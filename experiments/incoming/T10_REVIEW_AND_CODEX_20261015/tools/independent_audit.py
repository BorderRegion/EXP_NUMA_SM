#!/usr/bin/env python3
"""Read-only review of the supplied T10 light archive. No GPU, subprocess or network.
Recalculates from SESSION MEANS, not unavailable frame-level data or native outputs.
"""
from __future__ import annotations
import argparse, csv, collections, datetime as dt, hashlib, json, math, random, statistics
from pathlib import Path

def load_csv(p: Path):
    with p.open(encoding='utf-8', newline='') as f:
        return list(csv.DictReader(f))

def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def boot(groups, draws=20000, seed=2026101403):
    vals=list(groups.values())
    rng=random.Random(seed)
    samples=[]
    for _ in range(draws):
        level=[]
        for g in vals:
            level.append(sum(g[rng.randrange(len(g))] for _ in range(len(g)))/len(g))
        samples.append(math.exp(sum(level)/len(level)))
    samples.sort()
    def q(frac):
        x=(len(samples)-1)*frac; lo=int(x); hi=min(lo+1,len(samples)-1)
        return samples[lo]+(samples[hi]-samples[lo])*(x-lo)
    return {'ratio':math.exp(sum(sum(g)/len(g) for g in vals)/len(vals)),
            'ci95':[q(.025),q(.975)], 'ci97_5':[q(.0125),q(.9875)],
            'draws':draws, 'seed':seed}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--root',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args();root=args.root.resolve();out=args.out.resolve()
    if out.exists():raise SystemExit(f'Refusing to overwrite {out}')
    manifest=json.loads((root/'LIGHT_MANIFEST.json').read_text())
    errors=[]
    for e in manifest['files']:
        p=(root/e['path']).resolve()
        if not p.is_relative_to(root) or not p.is_file():errors.append(['missing/unsafe',e['path']]);continue
        if p.stat().st_size!=e['bytes'] or sha(p)!=e['sha256']:errors.append(['mismatch',e['path']])
    ledger=[json.loads(x) for x in (root/'run_index.jsonl').read_text().splitlines() if x.strip()]
    if len({x['run_id'] for x in ledger})!=len(ledger):errors.append(['duplicate run ids'])
    idx={x['run_id']:x for x in ledger}
    sessions=load_csv(root/'derived/t10/session_summaries.csv')
    blocks={}
    for r in sessions:
        key=(r['workload'],r['input'],int(r['sequence']),int(r['block_id']))
        b=blocks.setdefault(key,{})
        if r['policy'] in b:errors.append(['duplicate cell',key,r['policy']])
        b[r['policy']]=r
    for key,b in blocks.items():
        if set(b)!={'N','R','M'}:errors.append(['incomplete cell',key])
        if len({x['run_id'] for x in b.values()})!=1:errors.append(['not shared process',key])
    expected=json.loads((root/'derived/t10/application_statistics.json').read_text())
    summaries={}
    for ref in ['N','R']:
        paired=json.loads((root/f'derived/t10/paired_M_{ref}.json').read_text())
        computed={('/'.join(map(str,k[:3])),k[3]):(float(v['M']['mean_ms']),float(v[ref]['mean_ms'])) for k,v in blocks.items()}
        for rec in paired:
            target=computed[(rec['condition'],int(rec['block_id']))]
            if target!=(rec['candidate_ms'],rec['reference_ms']):errors.append(['paired mean mismatch',rec])
        for w in ['W1','W2']:
            groups=collections.OrderedDict()
            for k,v in sorted(blocks.items()):
                if k[0]==w:
                    groups.setdefault('/'.join(map(str,k[:3])),[]).append(math.log(float(v['M']['mean_ms'])/float(v[ref]['mean_ms'])))
            result=boot(groups)
            original=expected[w+'_M/'+ref]
            diffs=[abs(result['ratio']-original['ratio'])]+[abs(a-b) for a,b in zip(result['ci95'],original['ratio_ci95'])]+[abs(a-b) for a,b in zip(result['ci97_5'],original['ratio_ci97_5'])]
            result['max_abs_delta_vs_report']=max(diffs)
            result['matches_report_within_1e_12']=max(diffs)<1e-12
            if not result['matches_report_within_1e_12']:errors.append(['summary mismatch',w,ref,result])
            summaries[w+'_M/'+ref]=result
    per_condition=[]
    for cond in sorted(set(k[:3] for k in blocks)):
        subset=sorted((k,v) for k,v in blocks.items() if k[:3]==cond)
        ns=[float(v['N']['mean_ms']) for _,v in subset]
        per_condition.append({'condition':'/'.join(map(str,cond)), 'n_blocks':len(ns),
            'N_first_ms':ns[0], 'N_last_ms':ns[-1], 'N_min_ms':min(ns), 'N_max_ms':max(ns),
            'N_max_over_min':max(ns)/min(ns),
            'block_ratios_M_N':[float(v['M']['mean_ms'])/float(v['N']['mean_ms']) for _,v in subset],
            'block_ratios_M_R':[float(v['M']['mean_ms'])/float(v['R']['mean_ms']) for _,v in subset]})
    # Ledger start precedes flock acquisition; overlaps of queued intervals do NOT
    # prove overlapping GPU execution. Reconstructed end-minus-worker is descriptive.
    formal=sorted((x for x in ledger if x['stage'] in ['E4_W1','E4_W2']),key=lambda x:x['start_utc'])
    def parse(x):return dt.datetime.fromisoformat(x)
    queued_overlap=[];worker_est_overlap=[]
    for i,a in enumerate(formal):
        for b in formal[i+1:]:
            ends=[parse(a['end_utc']),parse(b['end_utc'])]
            starts=[parse(a['start_utc']),parse(b['start_utc'])]
            q=(min(ends)-max(starts)).total_seconds()
            if q>0:queued_overlap.append({'a':a['run_id'],'b':b['run_id'],'seconds':q})
            est=[ends[0]-dt.timedelta(seconds=a['worker_seconds']),ends[1]-dt.timedelta(seconds=b['worker_seconds'])]
            t=(min(ends)-max(est)).total_seconds()
            if t>.001:worker_est_overlap.append({'a':a['run_id'],'b':b['run_id'],'seconds':t})
    order=[idx[next(iter(b.values()))['run_id']]['config']['policies'] for b in blocks.values()]
    rates={}
    for p in (root/'preregistration').glob('*/*/plan_card.json'):
        d=json.loads(p.read_text());rr=d['rates']
        rates[str(p.parent.relative_to(root))]={'relative_group1_group0_by_class':[y/x for x,y in zip(rr[0],rr[1])],
            'single_rate_ratio':d['single_rate'][1]/d['single_rate'][0], 'plan_overlap_M_R':d['plan_overlap_M_R']}
    # For the exact E2 K2 source recipe: 8 indices per lane, 128 lanes,
    # j repeats those indices; cache_n caps the total union.
    k2=[]
    for size,nt,units in [(0,256,16),(1,1024,64),(2,4096,128)]:
        cache_n=min(nt*1024,1<<(18+size))
        # tasks cover consecutive 1024-word blocks before modulo;
        # all lane x j%8 values give every offset in each block.
        touched=min(nt*1024,cache_n)
        k2.append({'size':size,'tasks':nt,'units':units,'unique_input_bytes':touched*4,
            'unique_input_MiB':touched*4/2**20,'per_task_unique_bytes':min(1024,cache_n)*4,
            'same_address_repeats_per_task':units//8,
            'L2_ratio':touched*4/4194304,
            'address_depends_on_previous_load_value':False})
    top=json.loads((root/'derived/t10/topology.json').read_text())
    perproc=collections.defaultdict(dict)
    for a in top:perproc[a['process_block']][a['layout']]=a['sm_sets']
    topology={'G1_G3_same_actual_sets_each_process':all(x[1]==x[3] for x in perproc.values()),
        'number_E1_records':len(top)}
    result={
      'scope':'CPU independent archive and session-mean review only; no GPU, no frame raw, no full images/tasks/assets/binaries.',
      'manifest_checked':len(manifest['files']),'archive_member_files':sum(p.is_file() for p in root.rglob('*')),
      'errors':errors,'run_index_count':len(ledger),
      'run_stages':dict(collections.Counter((x['stage']+' '+x['status']) for x in ledger)),
      'reported_worker_seconds_sum':sum(x['worker_seconds'] for x in ledger),
      'formal_blocks':len(blocks),'formal_sessions':len(sessions),'reported_frames_sum':sum(int(r['frames']) for r in sessions),
      'all_formal_N_first':all(x.startswith('N') for x in order),'formal_orders':dict(collections.Counter(order)),
      'recomputed_primary_comparisons':summaries,'per_condition_drift_descriptive':per_condition,
      'queue_timestamps':{'queued_interval_overlap_pairs':len(queued_overlap),
        'end_minus_worker_estimated_overlap_pairs_over_1ms':len(worker_est_overlap),
        'interpretation':'runlib.py uses flock; start_utc is before lock wait. Do not interpret queued overlap as concurrent GPU work. Actual start is not separately recorded.',
        'examples':queued_overlap[:2]},
      'K2_exact_source_access_sets':k2,'rates':rates,'topology':topology}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['manifest_checked','archive_member_files','errors','run_index_count','reported_worker_seconds_sum','formal_blocks','formal_sessions','reported_frames_sum','recomputed_primary_comparisons','queue_timestamps','K2_exact_source_access_sets','topology']},ensure_ascii=False,indent=2))
    if errors:raise SystemExit(2)
if __name__=='__main__':main()
