"""Matched-q full post-route layers, pointwise fusion, and activation ring."""
import argparse,gc,hashlib,inspect,json,math,pathlib,time
import torch
from native_bench import ROOT,layer,mm_reference,check
from same_q_v2_backend import CutlassGrouped,pack_rows
from same_q_v2_activation import activation,qualify_activation
from grouped_library import Grouped,capture_readable
from same_q_v2_common import setup,write,seed,request_phase,phase_order,memory

def make(case,block,freeze,with_fusion=False):
    ordinary,validate,ledger,storage=layer(case,block)
    v=inspect.getclosurevars(ordinary).nonlocals
    aa=[];bb=[];cc=[];dd=[];ee=[];ff=[]
    for j in range(v['e']):
        lo,hi=v['offset'][j:j+2]
        aa.append(v['pack'][lo:hi]);bb.append(v['wgu'][j]);cc.append(v['gu'][lo:hi])
        dd.append(v['act'][lo:hi]);ee.append(v['wd'][j]);ff.append(v['down'][lo:hi])
    objects=[];calls={};metadata={}
    def finish(up,down,pack,fused=False):
        def call():
            pack();up()
            if fused:activation(v['gu'],v['act'])
            else:
                torch.ops.aten.silu.out(v['gu'][:,:v['i']],out=v['silu'])
                torch.mul(v['silu'],v['gu'][:,v['i']:],out=v['act'])
            down();torch.index_select(v['down'],0,v['inv'],out=v['unpack'])
            torch.mul(v['unpack'].view(v['t'],v['top'],v['h']),v['gates'][:,:,None],out=v['weighted'])
            torch.sum(v['weighted'],dim=1,out=v['output'])
        return call
    for name,mode in [('CACHE_Q1_LEGACY',1),('FULL_Q1_LEGACY',2),('Q1_MINIMAL',3),('CORE_REFERENCE',0)]:
        up=CutlassGrouped(aa,bb,cc,freeze['recipe'],mode,1,2 if mode==2 else 1)
        down=CutlassGrouped(dd,ee,ff,freeze['recipe'],mode,1,2 if mode==2 else 1)
        objects.extend([up,down])
        def pack(up=up,down=down):pack_rows(v['x'],v['token'],v['pack'],up,down,None,False)
        calls[name]=finish(up,down,pack)
        metadata[name]=dict(up=up.metadata(),down=down.metadata(),sideband_generated=False,
          scheduler_kernel_nodes=0,metadata_d2h_bytes=0,host_waits_inside=0)
        if with_fusion and name in ['CACHE_Q1_LEGACY','Q1_MINIMAL']:
            calls[name+'_FUSED']=finish(up,down,pack,True)
            metadata[name+'_FUSED']=dict(metadata[name],activation_fused=True)
    def eager_up():
        for a,b,c in zip(aa,bb,cc):
            if a.shape[0]:torch.mm(a,b,out=c)
    def eager_down():
        for a,b,c in zip(dd,ee,ff):
            if a.shape[0]:torch.mm(a,b,out=c)
    if freeze['layer_library']=='PER_EXPERT_GRAPH':libup,libdown=eager_up,eager_down
    else:
        libup,libdown=Grouped(aa,bb,cc),Grouped(dd,ee,ff);objects.extend([libup,libdown])
    libpack=lambda:torch.index_select(v['x'],0,v['token'],out=v['pack'])
    calls['LIB']=finish(libup,libdown,libpack)
    metadata['LIB']=dict(selected_path=freeze['layer_library'],scope='COMPOSED_LIBRARY_LAYER')
    if with_fusion:
        calls['LIB_FUSED']=finish(libup,libdown,libpack,True)
        metadata['LIB_FUSED']=dict(metadata['LIB'],activation_fused=True)
    calls['CORE_REFERENCE']();torch.cuda.synchronize();expected=v['output'].clone()
    assert all(x['pass'] for x in validate())
    return calls,validate,ledger,storage,expected,objects,metadata,v

def reference_current(v):
    # Same FP64 reference and explicit half boundaries as native_bench.layer.
    packed=v['x'].index_select(0,v['token']);gu=torch.empty_like(v['gu'],dtype=torch.float64)
    down=torch.empty_like(v['down'],dtype=torch.float64)
    for j in range(v['e']):
        lo,hi=v['offset'][j:j+2]
        if lo<hi:gu[lo:hi]=mm_reference(packed[lo:hi],v['wgu'][j]).half().double()
    act=(torch.nn.functional.silu(gu[:,:v['i']]).half().double()*gu[:,v['i']:]).half()
    for j in range(v['e']):
        lo,hi=v['offset'][j:j+2]
        if lo<hi:down[lo:hi]=mm_reference(act[lo:hi],v['wd'][j]).half().double()
    return (down[v['inv']].view(v['t'],v['top'],v['h'])*v['gates'].double()[:,:,None]).half().double().sum(1).half().double()

def run_case(case,block,freeze,phase,fusion_enabled):
    start=time.perf_counter();torch.manual_seed(seed(case,block));torch.cuda.reset_peak_memory_stats()
    calls,validate,ledger,storage,expected,objects,metadata,v=make(case,block,freeze,fusion_enabled)
    if phase=='formal':names=['LIB','CACHE_Q1_LEGACY','FULL_Q1_LEGACY','Q1_MINIMAL']
    elif phase=='fusion':names=['CACHE_Q1_LEGACY','Q1_MINIMAL','CACHE_Q1_LEGACY_FUSED','Q1_MINIMAL_FUSED']
    elif phase=='ring':names=['LIB_FUSED','CACHE_Q1_LEGACY_FUSED','Q1_MINIMAL_FUSED'] if fusion_enabled else ['LIB','CACHE_Q1_LEGACY','Q1_MINIMAL']
    else:names=[n for n in calls if n!='CORE_REFERENCE']
    graphs={};nodes={};qualification=[]
    for n in names:
        calls[n]();torch.cuda.synchronize();checks=validate();assert all(x['pass'] for x in checks),(n,checks)
        exact=torch.equal(storage['output'].view(torch.int16),expected.view(torch.int16)) if not n.startswith('LIB') else None
        if exact is not None:assert exact,n
        g,nd=capture_readable(calls[n]);graphs[n]=g;nodes[n]=nd
        qualification.append(dict(variant=n,checks=checks,same_body_bitwise=exact))
    gc.collect();torch.cuda.empty_cache()
    rows=[];ring_info=None
    if phase=='ring':
        slots=[v['x'].clone()]+[torch.randn_like(v['x']) for _ in range(7)]
        refs=[];exacts=[]
        for x in slots:
            v['x'].copy_(x);refs.append(reference_current(v));calls['CORE_REFERENCE']();torch.cuda.synchronize();exacts.append(storage['output'].clone())
        for n in names:
            for i,x in enumerate(slots):
                v['x'].copy_(x);graphs[n].replay();torch.cuda.synchronize()
                ck=check(storage['output'],refs[i]);assert ck['pass']
                exact=torch.equal(storage['output'].view(torch.int16),exacts[i].view(torch.int16)) if not n.startswith('LIB') else None
                if exact is not None:assert exact,(n,i)
                qualification.append(dict(variant=n,slot=i,checks=[ck],same_body_bitwise=exact))
        # One common D2D copy per request in both modes. CPU selection and copy
        # are inside ready/event intervals; weights/descriptors never rebuilt.
        modes=['HOT_SLOT0_COPY','ACTIVATION_RING8_FIXED_DESCRIPTORS']
        entries=[(n,m) for n in names for m in modes]
        order=phase_order([n+'@'+m for n,m in entries],block,case['case_id']+'ring',names[0]+'@'+modes[0])[1:-1]
        for entry,role in order:
            n,mode=entry.split('@');cursor=[0,0]
            def request():
                idx=cursor[0]%8 if mode==modes[1] else 0
                cursor[0]+=1;cursor[1]=idx
                v['x'].copy_(slots[idx]);graphs[n].replay()
            measured=request_phase(request);idx=cursor[1]
            checks=[check(storage['output'],refs[idx])];assert all(x['pass'] for x in checks)
            exact=torch.equal(storage['output'].view(torch.int16),exacts[idx].view(torch.int16)) if not n.startswith('LIB') else None
            if exact is not None:assert exact
            rows.append(dict(variant=n,input_mode=mode,phase_role=role,correctness=checks,same_body_bitwise=exact,**measured))
        ring_info=dict(slots=8,scope='DYNAMIC_ACTIVATION_FIXED_DESCRIPTORS',route_changes=False,weights_shared=True,
          prebuilt_graphs_per_policy=1,D2D_bytes_per_request=v['x'].numel()*2,selection_and_copy_in_ready=True,
          input_sequence_id=hashlib.sha256(('ring8:'+str(seed(case,block))).encode()).hexdigest(),all_slots_full_output_qualified=True)
    elif phase!='qualify':
        order=phase_order(names,block,case['case_id'], 'LIB' if phase=='formal' else names[0])
        if phase=='fusion':order=order[1:-1]
        for n,role in order:
            measured=request_phase(graphs[n].replay);checks=validate();assert all(x['pass'] for x in checks)
            exact=torch.equal(storage['output'].view(torch.int16),expected.view(torch.int16)) if n!='LIB' else None
            if exact is not None:assert exact,n
            rows.append(dict(variant=n,phase_role=role,correctness=checks,same_body_bitwise=exact,**measured))
    result=dict(status='PASS',case=case,block=block,phase=phase,input_seed=seed(case,block),
      route_seed=2026101517+block%3+case['tokens'],route_scope='THREE_REUSED_ROUTE_FAMILIES_KNOWN_REGRESSION',
      phases=rows,qualification=qualification,metadata={n:metadata[n] for n in names},graph_structure=nodes,
      ledger=ledger,memory=memory(),ring=ring_info,elapsed_s=time.perf_counter()-start,
      scope='FULL_POST_ROUTE_PACK_UP_ACTIVATION_DOWN_UNPACK_GATE_REDUCE',sideband_generated=False)
    for obj in objects:
        if hasattr(obj,'close'):obj.close()
    return result

def main(a):
    setup();freeze=json.loads((a.run_root/'BODY_AND_BASELINE_FREEZE_V2.json').read_text())
    protocol=json.loads((a.run_root/'PROTOCOL_V2.json').read_text())
    enabled=True
    if a.phase=='qualify':
        qualification=qualify_activation();write(a.out/'activation_qualification.json',qualification)
        enabled=qualification['status']=='PASS'
        case=dict(case_id='v2-layer-qualification',suite='moe_layer',tokens=17,hidden=128,intermediate=256,experts=4,top_k=2)
        try:result=run_case(case,0,freeze,'qualify',enabled)
        except AssertionError as error:
            if not enabled:raise
            qualification.update(status='FAILED',layer_semantic_failure=str(error))
            write(a.out/'activation_qualification.json',qualification)
            gc.collect();torch.cuda.empty_cache()
            result=run_case(case,0,freeze,'qualify',False)
        write(a.out/'layer_qualification.json',result)
        print('LAYER_PASS FUSION_'+qualification['status'],flush=True);return
    # Qualification failure only disables optional fusion; matched-q main work survives.
    registry=[json.loads(s) for s in (ROOT/'registry/runs.jsonl').read_text().splitlines()] if (ROOT/'registry/runs.jsonl').exists() else []
    # Worker supplies this flag from the preceding immutable qualification.
    enabled=a.fusion_enabled
    if a.phase=='fusion' and not enabled:
        write(a.out/'skipped.json',dict(status='SKIPPED',reason='ACTIVATION_NOT_QUALIFIED'));return
    plans=[json.loads(s) for s in (ROOT/'preregistration/plan.jsonl').read_text().splitlines()]
    ids=protocol['ring_cases'] if a.phase=='ring' else freeze['layer_ids']
    for c in plans:
        if c['case_id'] not in ids:continue
        try:result=run_case(c,a.block,freeze,a.phase,enabled)
        except (MemoryError,torch.OutOfMemoryError) as e:result=dict(status='MEMORY_UNSUPPORTED',case=c,block=a.block,error=str(e))
        write(a.out/(c['case_id']+'.json'),result);print(c['case_id'],a.phase,result['status'],round(result.get('elapsed_s',0),2),flush=True)
        gc.collect();torch.cuda.empty_cache()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=pathlib.Path,required=True);p.add_argument('--run-root',type=pathlib.Path,required=True)
    p.add_argument('--phase',choices=['qualify','formal','fusion','ring'],required=True);p.add_argument('--block',type=int,default=0)
    p.add_argument('--fusion-enabled',action='store_true');main(p.parse_args())
