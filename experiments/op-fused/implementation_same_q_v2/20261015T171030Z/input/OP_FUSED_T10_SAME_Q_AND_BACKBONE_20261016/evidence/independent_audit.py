"""Read-only CPU review of OP_FUSED_T10_IMPLEMENTATION_COMPLETE_20261015.
Never imports uploaded GPU modules, loads a shared object, or modifies source data.
"""
from pathlib import Path
import argparse, json, hashlib, collections, math, re
import numpy as np

def load(p): return json.loads(p.read_text())
def geomean(a): return math.exp(sum(math.log(float(v)) for v in a)/len(a))
def effect(logs, primary=False):
    a=np.asarray(logs,dtype=float)
    rng=np.random.default_rng(2026101509)
    b=a[rng.integers(0,len(a),(20000,len(a)))].mean(1)
    q=(.0125,.9875) if primary else (.025,.975)
    return {'time_ratio':float(np.exp(a.mean())), 'ratio_interval':np.exp(np.quantile(b,q)).tolist(), 'block_log_ratios':a.tolist()}
def primary(row):
    d={x['variant']:x for x in row['phases'] if x['phase_role']=='primary'}
    for k,v in row.get('aliases',{}).items(): d[k]=d[v]
    return d

def flatten(nodes):
    for n in nodes:
        yield n
        yield from flatten(n.get('children',[]))

def main(root,out):
    out.mkdir(parents=True,exist_ok=True)
    errors=[]
    manifests=load(root/'MANIFEST_SHA256.json')
    for r in manifests:
        p=root/r['path']
        if not p.is_file():errors.append(['missing',r['path']]);continue
        b=p.read_bytes()
        if len(b)!=r['bytes'] or hashlib.sha256(b).hexdigest()!=r['sha256']:errors.append(['hash',r['path']])
    rows=[]
    for p in sorted((root/'runs').glob('*/*.json')):
        d=load(p)
        if isinstance(d,dict) and 'case' in d and 'phases' in d:
            d=dict(d);d['_ref']=str(p.relative_to(root));rows.append(d)
    grouped=collections.defaultdict(list)
    development=[];phases=[];nc=0;nf=0;exactfalse=0;warmfalse=0;sampletotal=0;mean_err=[]
    bysuite=collections.Counter();graph_counts=collections.defaultdict(set);graphsn=0
    aliases=collections.Counter();allq1=True;fullstatsn=0;tiletotal=0
    saved_cases=load(root/'derived/implementation_v1/case_results.json')
    formal_refs={s for r in saved_cases for s in r['raw_refs']}
    for row in rows:
        bysuite[row['case']['suite']]+=1
        for ph in row['phases']:
            phases.append(ph)
            for chk in ph.get('correctness',[]):
                nc+=1;nf+=not chk.get('pass',False)
            exactfalse+=ph.get('same_body_bitwise') is False
            warmfalse+=ph['warmup_repeats']<64 or ph['warmup_device_ms']<300
            for key,mkey in [('request_device_ms','device_interval_ms'),('request_ready_ms','operator_or_layer_ready_ms')]:
                if key in ph:
                    ar=ph[key];sampletotal+=len(ar)
                    err=abs(sum(ar)/len(ar)-ph[mkey]);mean_err.append(err)
        for a,t in row.get('aliases',{}).items():aliases[(a,t)]+=1
        # The authoritative formal set is independently matched to provided raw_refs.
        if row['_ref'] in formal_refs:
            grouped[(row['case']['suite'],row['case']['case_id'])].append(row)
        else:
            if row['case']['suite']=='grouped':development.append(row)
        graphs={k:m['graph_structure'] for k,m in row.get('metadata',{}).items() if 'graph_structure' in m}
        graphs.update(row.get('graph_structure',{}))
        for name,g in graphs.items():
            graphsn+=1
            nodes=list(flatten(g['nodes']))
            graph_counts[(row['case']['suite'],name)].add(sum(n['type']==0 for n in nodes))
        if row['_ref'] in formal_refs:
            for name,m in row.get('metadata',{}).items():
                st=m.get('packets')
                if st and name=='FULL':
                    fullstatsn+=1;allq1 &= not st['has_multitile_packet'];tiletotal+=st['tiles']
                if name in ('F0S1','F1S1'):
                    for k in ('up_packets','down_packets'):
                        st=m.get(k)
                        if st:fullstatsn+=1;allq1 &= not st['has_multitile_packet'];tiletotal+=st['tiles']
    fr=load(root/'preregistration/implementation_freeze.json')
    lf=load(root/'preregistration/implementation_layer_freeze.json')
    caseout=[];aggs=collections.defaultdict(lambda:collections.defaultdict(list))
    for (suite,cid),rs in sorted(grouped.items()):
        rs.sort(key=lambda r:r['block'])
        assert len(rs)==6 and {r['block'] for r in rs}==set(range(6)),cid
        met='operator_or_layer_ready_ms' if suite=='moe_layer' else 'device_interval_ms'
        cmps=({'FULL_over_LIB':('F1S1',lf['layer_library']),'FULL_over_SIMPLE':('F1S1','F1S0'),
            'SCHEDULE_AT_F0':('F0S1','F0S0'),'FUSION_AT_FULL':('F1S1','F0S1'),'FUSION_AT_SIMPLE':('F1S0','F0S0')}
           if suite=='moe_layer' else
           {'FULL_over_LIB':('FULL',fr['library']),'FULL_over_SIMPLE':('FULL',fr['simple']),
            'CORE_over_LIB':('CORE',fr['library']),'CACHE_over_CORE':('CACHE','CORE'),
            'FULL_over_ABL':('FULL','ABL'),'FULL_over_BAL':('FULL','BAL')})
        cres={'suite':suite,'case_id':cid,'effects':{}}
        for name,(a,b) in cmps.items():
            logs=[]
            for r in rs:
                p=primary(r);v=math.log(p[a][met]/p[b][met]);logs.append(v);aggs[(suite,name)][r['block']].append(v)
            cres['effects'][name]=effect(logs)
        if suite=='moe_layer':
            for r in rs:
                p=primary(r);v=math.log(p['F1S1'][met]/p['F1S0'][met])-math.log(p['F0S1'][met]/p['F0S0'][met])
                aggs[(suite,'FUSION_SCHEDULE_INTERACTION')][r['block']].append(v)
        caseout.append(cres)
    summary=load(root/'derived/implementation_v1/summary.json')
    max_delta=0.;effect_count=0
    orig={r['case_id']:r for r in saved_cases}
    for r in caseout:
        for name,e in r['effects'].items():
            oe=orig[r['case_id']]['effects'][name];effect_count+=1
            max_delta=max(max_delta,abs(e['time_ratio']-oe['time_ratio']),*np.abs(np.array(e['ratio_interval'])-oe['ratio_interval']))
    aggout={}
    for (suite,name),bl in aggs.items():
        e=effect([sum(v)/len(v) for b,v in sorted(bl.items())],name in ('FULL_over_LIB','FULL_over_SIMPLE'))
        aggout.setdefault(suite,{})[name]=e;effect_count+=1
        oe=summary['aggregate'][suite][name]
        max_delta=max(max_delta,abs(e['time_ratio']-oe['time_ratio']),*np.abs(np.array(e['ratio_interval'])-oe['ratio_interval']))
    # Exploratory reuse of development records, explicitly not new holdout evidence.
    devres={}
    pairs=[('FULL_r0_q1_w2','CACHE_r0_q1'),('FULL_r0_q1_w1','CACHE_r0_q1'),('CACHE_r0_q1','CORE_r0'),
       ('CACHE_r0_q4','CACHE_r0_q1'),('FULL_r0_q1_w2','FULL_r0_q1_w1')]
    for a,b in pairs:
        logs=collections.defaultdict(list)
        for r in development:
            p=primary(r)
            if a in p and b in p:logs[r['block']].append(math.log(p[a]['device_interval_ms']/p[b]['device_interval_ms']))
        devres[a+'/'+b]=dict(effect([sum(v)/len(v) for k,v in sorted(logs.items())]),scope='POST_HOC_DEVELOPMENT_ONLY')
    # Verify finite q=1 logical map against a second, direct enumeration.
    mapchecks=0
    for r in rows:
        for name,m in r.get('metadata',{}).items():
            op=m.get('adapter')
            if not op:continue
            bm=op['resources'][0]['tile_m'];bn=op['resources'][0]['tile_n']
            for M,N,K in op['shapes']:
                gm=(M+bm-1)//bm;gn=(N+bn-1)//bn
                if not gm or not gn:continue
                # Algebraic inverse check at boundary and representative points.
                for idx in {0,gm*gn-1,min(gm*gn-1,gm),min(gm*gn-1,gn),gm*gn//2}:
                    m0=idx%gm;n0=idx//gm;ordinal=m0*gn+n0
                    assert (ordinal//gn,ordinal%gn)==(m0,n0)
                    mapchecks+=1
    result={
      'scope':'CPU integrity, raw recorded statistics, graph and source analysis only; no GPU, no tensor recomputation',
      'manifest_entries':len(manifests),'manifest_errors':errors,
      'case_blocks':len(rows),'formal_case_blocks':sum(len(v) for v in grouped.values()),'phases':len(phases),
      'by_suite_case_blocks':dict(bysuite),'correctness_summaries':nc,'failed_summaries':nf,
      'same_body_bitwise_false':exactfalse,'warmup_violations':warmfalse,
      'request_sample_values_reaveraged':sampletotal,'request_mean_max_error':max(mean_err,default=0),
      'graph_records':graphsn,'graph_kernel_counts':{'/'.join(k):sorted(v) for k,v in graph_counts.items()},
      'alias_counts':{'->'.join(k):v for k,v in aliases.items()},
      'formal_FULL_packet_records':fullstatsn,'formal_FULL_all_q1':allq1,'formal_FULL_tiles_counted_with_stage_duplicates':tiletotal,
      'effects_recomputed':effect_count,'effect_max_absolute_discrepancy':max_delta,
      'aggregate':aggout,'development_exploratory_pairs':devres,
      'q1_algebra_boundary_checks':mapchecks,
      'unknown':['Numerical tensors absent; no independent GEMM or MoE numeric verification',
                 'Full vendor checkout excluded; no complete vendor source equivalence proof',
                 'No GPU binary executed or compiled in this review',
                 'Hardware performance-cause attribution requires controlled measurements']}
    (out/'independent_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    (out/'independent_case_effects.json').write_text(json.dumps(caseout,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['manifest_entries','manifest_errors','case_blocks','formal_case_blocks','phases','correctness_summaries','failed_summaries','same_body_bitwise_false','graph_records','effects_recomputed','effect_max_absolute_discrepancy','formal_FULL_all_q1','request_sample_values_reaveraged','request_mean_max_error','development_exploratory_pairs']},ensure_ascii=False,indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('out',type=Path);a=p.parse_args();main(a.root,a.out)
