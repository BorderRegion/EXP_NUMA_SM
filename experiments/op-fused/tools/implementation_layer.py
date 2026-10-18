"""Full post-route layer: same math and useful pack for fusion/schedule four cells."""
import argparse,gc,hashlib,inspect,json,math,pathlib,time
import torch
from native_bench import ROOT,layer,utc
from cutlass_grouped import CutlassGrouped,pack_rows
from grouped_library import Grouped,capture_readable
from request_layer_bench import measure
from reference import balanced_orders
from implementation_bench import SEEDS,packet_stats

def make(case,block,freeze,development):
 ordinary,validate,ledger,storage=layer(case,block)
 v=inspect.getclosurevars(ordinary).nonlocals
 aa=[];bb=[];cc=[];dd=[];ee=[];ff=[]
 for j in range(v['e']):
  lo,hi=v['offset'][j:j+2]
  aa.append(v['pack'][lo:hi]);bb.append(v['wgu'][j]);cc.append(v['gu'][lo:hi])
  dd.append(v['act'][lo:hi]);ee.append(v['wd'][j]);ff.append(v['down'][lo:hi])
 totals=[];objects=[];calls={};metadata={}
 def finish(up,down,pack):
  def call():
   pack();up()
   torch.ops.aten.silu.out(v['gu'][:,:v['i']],out=v['silu'])
   torch.mul(v['silu'],v['gu'][:,v['i']:],out=v['act'])
   down();torch.index_select(v['down'],0,v['inv'],out=v['unpack'])
   torch.mul(v['unpack'].view(v['t'],v['top'],v['h']),v['gates'][:,:,None],out=v['weighted'])
   torch.sum(v['weighted'],dim=1,out=v['output'])
   return v['output']
  return call
 for fused in [0,1]:
  for schedule in [0,1]:
   name=f'F{fused}S{schedule}'
   mode=2 if schedule else (1 if freeze['simple']=='CACHE' else 0)
   q=freeze['full_q'] if schedule else (freeze['cache_q'] if mode==1 else 1)
   waves=freeze['full_waves'] if schedule else 1
   total=torch.full((2,),-1,device='cuda',dtype=torch.int32);totals.append(total)
   up=CutlassGrouped(aa,bb,cc,freeze['recipe'],mode,q,waves,sideband=total[:1] if fused else None)
   down=CutlassGrouped(dd,ee,ff,freeze['recipe'],mode,q,waves,sideband=total[1:] if fused else None)
   def pack(up=up,down=down,total=total,fused=fused):
    pack_rows(v['x'],v['token'],v['pack'],up,down,total,fused)
   calls[name]=finish(up,down,pack);objects.extend([up,down])
   metadata[name]=dict(up=up.metadata(),down=down.metadata(),up_packets=packet_stats(up),
       down_packets=packet_stats(down),sideband_in_existing_pack=bool(fused),
       new_scheduler_kernel_nodes=0,metadata_d2h_bytes=0,host_waits_inside=0)
 libs=['PER_EXPERT_GRAPH','NATIVE_GROUPED_GRAPH'] if development else [freeze['layer_library']]
 if 'PER_EXPERT_GRAPH' in libs:calls['PER_EXPERT_GRAPH']=ordinary
 if 'NATIVE_GROUPED_GRAPH' in libs:
  up=Grouped(aa,bb,cc);down=Grouped(dd,ee,ff)
  calls['NATIVE_GROUPED_GRAPH']=finish(up,down,lambda:torch.index_select(v['x'],0,v['token'],out=v['pack']))
 # Same-body exact reference from original visitor, independent of frozen S0.
 up=CutlassGrouped(aa,bb,cc,freeze['recipe'],0);down=CutlassGrouped(dd,ee,ff,freeze['recipe'],0)
 refcall=finish(up,down,lambda:torch.index_select(v['x'],0,v['token'],out=v['pack']))
 refcall();torch.cuda.synchronize();exact=v['output'].clone();up.close();down.close()
 assert all(c['pass'] for c in validate())
 return calls,validate,ledger,storage,exact,objects,metadata,totals

def run_case(case,block,freeze,development,qualify=False):
 torch.manual_seed(SEEDS[block]+int(case['case_id'].split('-')[-1]))
 torch.cuda.reset_peak_memory_stats();start=time.perf_counter()
 calls,validate,ledger,storage,expected,objects,metadata,totals=make(case,block,freeze,development)
 validation_peak=torch.cuda.max_memory_reserved()
 gc.collect();torch.cuda.empty_cache();torch.cuda.reset_peak_memory_stats()
 graphs={};nodes={}
 for name,call in calls.items():
  call();torch.cuda.synchronize();checks=validate();assert all(x['pass'] for x in checks),(name,checks)
  if name.startswith('F'):assert torch.equal(storage['output'],expected),name
  graph,graph_nodes=capture_readable(call);graphs[name]=graph;nodes[name]=graph_nodes
  graph.replay();torch.cuda.synchronize();assert all(x['pass'] for x in validate())
  if name.startswith('F'):assert torch.equal(storage['output'],expected),name
 for name,total in zip(['F0S0','F0S1','F1S0','F1S1'],totals):
  if name.startswith('F1'):
   assert total.cpu().tolist()==[metadata[name]['up']['total_tiles'],metadata[name]['down']['total_tiles']]
 rows=[]
 if not qualify:
  anchor='PER_EXPERT_GRAPH' if development else freeze['layer_library']
  order=balanced_orders(list(graphs),6,2026101531)[block]
  for name,role in [(anchor,'anchor_head')]+[(n,'primary') for n in order]+[(anchor,'anchor_tail')]:
   measured=measure(graphs[name].replay);checks=validate();assert all(x['pass'] for x in checks)
   exact=torch.equal(storage['output'],expected) if name.startswith('F') else None
   if exact is not None:assert exact
   rows.append(dict(variant=name,phase_role=role,correctness=checks,same_body_bitwise=exact,**measured))
 free,total=torch.cuda.mem_get_info();reserved=torch.cuda.max_memory_reserved()
 result=dict(status='LAYER_QUALIFICATION_PASS' if qualify else 'IMPLEMENTED_LAYER_COMPARISON',case=case,
   block=block,input_seed=SEEDS[block]+int(case['case_id'].split('-')[-1]),route_seed=2026101517+block%3+case['tokens'],
   phases=rows,metadata=metadata,graph_structure=nodes,ledger=ledger,elapsed_s=time.perf_counter()-start,
   memory=dict(validation_peak_reserved_bytes=validation_peak,production_peak_reserved_bytes=reserved,
      free_after=free,total=total,production_margin_pass=reserved<=total-max(2*2**30,math.ceil(.15*total))),
   scope='SYNTHETIC_FIXED_POST_ROUTE; THREE_ROUTE_FAMILIES_SIX_INPUT_SEEDS; TRUE_REQUEST_READY',
   fusion='F0 and F1 same custom useful pack; F1 adds total-tile sideband used instead of visitor warp reduction',
   metadata_lifecycle='GPU problem shapes are ready inputs; pack CTA0 reads them, next kernel consumes totals; no CTA reads another CTA output')
 for op in objects:op.close()
 return result

def main(args):
 torch.set_num_threads(2);torch.backends.cuda.preferred_blas_library('cublas')
 torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction=False
 if args.phase=='qualify':
  case=dict(case_id='qualification-001',suite='moe_layer',tokens=17,hidden=128,intermediate=256,experts=4,top_k=2)
  data=[]
  for recipe in [0,1]:
   freeze=dict(recipe=recipe,simple='CACHE',cache_q=2,full_q=4,full_waves=1)
   data.append(run_case(case,0,freeze,True,True));gc.collect();torch.cuda.empty_cache()
  (args.out/'layer_qualification.json').write_text(json.dumps(data,indent=2)+'\n')
  print('LAYER_FOUR_CELL_QUALIFICATION_PASS',flush=True);return
 freeze=json.loads((ROOT/'preregistration/implementation_freeze.json').read_text())
 development=args.phase=='develop'
 if not development:freeze.update(json.loads((ROOT/'preregistration/implementation_layer_freeze.json').read_text()))
 plans=[json.loads(s) for s in (ROOT/'preregistration/plan.jsonl').read_text().splitlines()]
 if development:cases=[c for c in plans if c['suite']=='moe_layer' and c['split']=='calibration']
 else:cases=[c for c in plans if c['case_id'] in freeze['layer_test_case_ids']]
 for case in cases:
  try:result=run_case(case,args.block,freeze,development)
  except (MemoryError,torch.OutOfMemoryError) as e:result=dict(status='MEMORY_UNSUPPORTED',case=case,block=args.block,error=str(e))
  (args.out/(case['case_id']+'.json')).write_text(json.dumps(result,indent=2)+'\n')
  print(case['case_id'],result['status'],round(result.get('elapsed_s',0),2),flush=True)
  gc.collect();torch.cuda.empty_cache()

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=pathlib.Path)
 p.add_argument('--phase',choices=['qualify','develop','test'],required=True);p.add_argument('--block',type=int,default=0)
 main(p.parse_args())
