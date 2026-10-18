"""CPU-only analysis of immutable V2 worker outputs; no timings rewritten."""
import collections,datetime,hashlib,json,math,pathlib
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]
RUN=pathlib.Path((ROOT/'implementation_same_q_v2/CURRENT_RUN.txt').read_text().strip())
OUT=RUN/'derived'
def save(name,data):
    OUT.mkdir(exist_ok=True);(OUT/name).write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def effect(logs,confidence=.95):
    values=np.array(logs,dtype=float);rng=np.random.default_rng(2026101609)
    draw=np.exp(values[rng.integers(0,len(values),(20000,len(values)))].mean(1))
    alpha=(1-confidence)/2
    return dict(ratio=float(np.exp(values.mean())),interval=[float(x) for x in np.quantile(draw,[alpha,1-alpha])],
      confidence=confidence,blocks=len(values),draws=20000,seed=2026101609,unit='independent process block')
def flat(nodes):
    for n in nodes:
        yield n
        yield from flat(n.get('children',[]))
def rows():
    registry=[json.loads(s) for s in (ROOT/'registry/runs.jsonl').read_text().splitlines()]
    records=[];failures=[]
    for m in registry:
        if not m['key'].startswith('sameq_v2_'):continue
        if m['status']!='COMPLETED':failures.append(m)
        for p in (ROOT/m['path']).glob('*.json'):
            d=json.loads(p.read_text())
            if isinstance(d,dict) and 'case' in d:
                if d.get('status')=='PASS':records.append((m,p,d))
                else:failures.append(dict(worker=m['key'],path=str(p.relative_to(ROOT)),result=d))
    return registry,records,failures
def metric_map(d,metric,mode='STATIC'):
    vals={p['variant']:p[metric] for p in d['phases'] if p['phase_role']=='primary' and p.get('input_mode','STATIC')==mode}
    for alias,original in d.get('aliases',{}).items():vals[alias]=vals[original]
    return vals
def pair_results(records,pairs,metric='device_interval_ms',mode='STATIC'):
    cases=collections.defaultdict(dict);aliases={}
    for _,_,d in records:
        cases[d['case']['case_id']][d['block']]=metric_map(d,metric,mode)
        aliases[d['case']['case_id']]=d.get('aliases',{})
    aggregate={};bycase=[]
    for a,b in pairs:
        valid={c:{block:math.log(v[a]/v[b]) for block,v in bs.items() if a in v and b in v} for c,bs in cases.items()}
        valid={c:vs for c,vs in valid.items() if vs}
        if not valid:continue
        blocks=sorted(set.intersection(*(set(v) for v in valid.values())))
        if not blocks:continue
        logs=[sum(v[x] for v in valid.values())/len(valid) for x in blocks]
        key=a+'/'+b;result=effect(logs)
        result.update(cases=len(valid),case_ids=sorted(valid),paired_block_ids=blocks,
          interpretation='EXPLORATORY_95_PERCENT; not multiplicity-controlled',metric=metric,input_mode=mode)
        if (a,b) in [('FULL_Q1_LEGACY','CACHE_Q1_LEGACY'),('Q1_MINIMAL','CACHE_Q1_LEGACY')]:
            result['same_q_two_pair_bonferroni_marginal_97p5']=effect(logs,.975)
        aggregate[key]=result
        for c,vs in valid.items():
            original=lambda x:aliases[c].get(x,x)
            alias=original(a)==original(b)
            bycase.append(dict(case_id=c,comparison=key,metric=metric,input_mode=mode,
              structural_alias=alias,**effect([vs[x] for x in sorted(vs)])))
    return dict(aggregate=aggregate,cases=bycase)
def main():
    registry,records,failures=rows();freeze_path=RUN/'BODY_AND_BASELINE_FREEZE_V2.json'
    freeze=json.loads(freeze_path.read_text()) if freeze_path.exists() else None
    cohorts=collections.defaultdict(list)
    for m,p,d in records:
        if not d['phases']:continue
        if 'develop' in m['key']:name='development'
        elif 'diagnose' in m['key']:name='single_problem_diagnostic'
        elif 'formal' in m['key']:name=d['case']['split']
        elif 'fusion' in m['key']:name='layer_fusion'
        elif 'ring' in m['key']:name='layer_ring'
        elif 'layer_' in m['key']:name='layer_main'
        else:continue
        cohorts[name].append((m,p,d))
    pairs=[('FULL_Q1_LEGACY','CACHE_Q1_LEGACY'),('Q1_MINIMAL','CACHE_Q1_LEGACY'),
      ('Q1_MINIMAL','CORE_ORIGINAL'),('Q1_MINIMAL','CACHE_FIXED_BEST'),('Q1_MINIMAL',freeze['library'] if freeze else 'PER_EXPERT_GRAPH')]
    analyses={}
    for cohort,data in cohorts.items():
        current=pairs;modes=['STATIC']
        if cohort=='development':
            current=[(f'CORE_r{r}','CORE_r0') for r in [1,2,3]]+[(f'MINIMAL_r{r}',f'CACHE_r{r}_q1') for r in range(4)]+[(f'FULL_Q1_r{r}',f'CACHE_r{r}_q1') for r in range(4)]
        elif cohort=='single_problem_diagnostic':
            current=[(f'{kind}_r{r}','PER_EXPERT_GRAPH') for r in range(4) for kind in ['SINGLE','GROUPED_CORE','GROUPED_MINIMAL']]+[(f'{kind}_r{r}',f'SINGLE_r{r}') for r in range(4) for kind in ['GROUPED_CORE','GROUPED_MINIMAL']]
        elif cohort=='layer_main':current=pairs[:2]+[('Q1_MINIMAL','LIB'),('CACHE_Q1_LEGACY','LIB'),('FULL_Q1_LEGACY','LIB')]
        elif cohort=='layer_fusion':current=[('Q1_MINIMAL','CACHE_Q1_LEGACY'),('Q1_MINIMAL_FUSED','CACHE_Q1_LEGACY_FUSED'),('Q1_MINIMAL_FUSED','Q1_MINIMAL'),('CACHE_Q1_LEGACY_FUSED','CACHE_Q1_LEGACY')]
        elif cohort=='layer_ring':
            fused=any(p['variant'].endswith('_FUSED') for _,_,d in data for p in d['phases']);suffix='_FUSED' if fused else ''
            current=[('Q1_MINIMAL'+suffix,'CACHE_Q1_LEGACY'+suffix),('Q1_MINIMAL'+suffix,'LIB'+suffix),('CACHE_Q1_LEGACY'+suffix,'LIB'+suffix)]
            modes=['HOT_SLOT0_COPY','ACTIVATION_RING8_FIXED_DESCRIPTORS']
        analyses[cohort]={mode:{metric:pair_results(data,current,metric,mode) for metric in ['device_interval_ms','operator_or_layer_ready_ms']} for mode in modes}
    phases=[];launch=[];drift=[];resources={};binary=set();checks=0;bad=[];maxfro=0;warmbad=[];mem=[];cost=[];anchor_sensitivity=[];outside=0
    for m,p,d in records:
        ident=dict(worker=m['key'],case_id=d['case']['case_id'],block=d['block'])
        mem.append(dict(**ident,**d['memory'])) if 'memory' in d else None
        for row in d['phases']+d.get('qualification',[]):
            for c in row.get('correctness',row.get('checks',[])):
                checks+=1;maxfro=max(maxfro,c['relative_frobenius'])
                if not c['pass']:bad.append(dict(**ident,variant=row['variant'],check=c))
            if row.get('same_body_bitwise') is False:bad.append(dict(**ident,variant=row['variant'],bitwise=False))
        for row in d['phases']:
            if 'aggregate_device_ms' in row and not 50<=row['aggregate_device_ms']<=150:outside+=1
            phases.append(dict(**ident,variant=row['variant'],role=row['phase_role'],input_mode=row.get('input_mode','STATIC'),
              device_ms=row['device_interval_ms'],ready_ms=row['operator_or_layer_ready_ms'],start=row['start'],end=row['end'],repeats=row['measured_requests']))
            if row['warmup_repeats']<64 or row['warmup_device_ms']<150:warmbad.append(dict(**ident,variant=row['variant']))
            for col,mean in [('request_device_ms','device_interval_ms'),('request_ready_ms','operator_or_layer_ready_ms')]:
                if col in row:assert abs(sum(row[col])/len(row[col])-row[mean])<1e-12
        anchors={row['phase_role']:row for row in d['phases'] if row['phase_role'].startswith('anchor')}
        if len(anchors)==2:
            ratio=anchors['anchor_tail']['device_interval_ms']/anchors['anchor_head']['device_interval_ms']
            drift.append(dict(**ident,tail_over_head=ratio,over_five_percent=abs(ratio-1)>.05))
            primary={row['variant']:row for row in d['phases'] if row['phase_role']=='primary'}
            if 'Q1_MINIMAL' in primary:
                anchor_sensitivity.append(dict(**ident,candidate_ms=primary['Q1_MINIMAL']['device_interval_ms'],
                  lib_primary_ms=primary[anchors['anchor_head']['variant']]['device_interval_ms'],
                  lib_head_ms=anchors['anchor_head']['device_interval_ms'],lib_tail_ms=anchors['anchor_tail']['device_interval_ms']))
        for variant,meta in d['metadata'].items():
            for component,adapter in ([('operator',meta['adapter'])] if 'adapter' in meta else [(k,meta[k]) for k in ['up','down'] if k in meta]):
                binary.add(adapter['binary_sha256'])
                for mode,res in enumerate(adapter['resources']):resources[f"recipe{adapter['recipe']}_mode{mode}"]=res
            graph=meta.get('graph_structure',d.get('graph_structure',{}).get(variant))
            if graph:
                kinds=collections.Counter(n['type'] for n in flat(graph['nodes']))
                launch.append(dict(**ident,variant=variant,kernel_nodes=kinds[0],memcpy_nodes=kinds[1],memset_nodes=kinds[2],
                  scheduler_kernel_nodes=0,scheduler_field_scope='USER_ADDED_ONLY; closed library internal planning unclassified',scheduler_D2H_bytes=0,host_waits_inside_operator=0,
                  sideband_bytes=0,ring_D2D_bytes_per_request=(d.get('ring') or {}).get('D2D_bytes_per_request',0),
                  evidence='GRAPH_NODE_INTROSPECTION_AND_WRAPPER_SOURCE; ring copy outside graph included in timing'))
        wall=sum((datetime.datetime.fromisoformat(x['end'])-datetime.datetime.fromisoformat(x['start'])).total_seconds() for x in d['phases'])
        cost.append(dict(**ident,case_elapsed_s=d['elapsed_s'],phase_wall_s=wall,other_setup_reference_validation_graph_python_s=d['elapsed_s']-wall))
    new=registry[92:];prefix=(ROOT/'registry/runs.jsonl').read_bytes().startswith((RUN/'registry_prefix.jsonl').read_bytes())
    budget=dict(old_records=92,old_prefix_unchanged=prefix,new_records=len(new),new_seconds=sum(x['worker_occupied_s'] for x in new),
      total_seconds=sum(x['worker_occupied_s'] for x in registry),new_cap_seconds=14400,total_cap_seconds=57600)
    budget['worker_windows_overlap']=any(datetime.datetime.fromisoformat(a['released_at'])>datetime.datetime.fromisoformat(b['lock_acquired_at']) for a,b in zip(registry,registry[1:]))
    temperatures=[];limits=set();clocks=[]
    for m in new:
        import csv
        p=ROOT/m['path']/'telemetry.csv'
        with p.open() as f:
            for row in csv.DictReader(f,skipinitialspace=True):
                try:
                    temperatures.append(int(row['temperature.gpu']));clocks.append(int(row['clocks.current.sm [MHz]'].split()[0]))
                    limits.add((row['power.limit [W]'],row['enforced.power.limit [W]']))
                except (ValueError,KeyError):continue
    summary=dict(freeze=freeze,case_blocks={k:len(v) for k,v in cohorts.items()},phases=len(phases),checks=checks,
      correctness_failures=bad,max_relative_frobenius=maxfro,warmup_failures=warmbad,worker_failures=failures,
      operator_phases_outside_target_50_to_150_ms=outside,
      bitwise_scope='Operator phase legacy field is FP16 value equality, signed zero not distinguished. Separate raw-int16 samples; layer phases use int16 views.',
      budget=budget,math_binary_hashes=sorted(binary),drift_blocks=len(drift),drift_over_five_percent=sum(d['over_five_percent'] for d in drift),
      memory_failures=[x for x in mem if not x['conservative_margin_pass']],thermal=dict(samples=len(temperatures),
      temperature_range=[min(temperatures),max(temperatures)] if temperatures else None,clock_range=[min(clocks),max(clocks)] if clocks else None,
      power_limits=sorted(limits),interpretation='100W cap is not locked frequency; raw sample masks retained in telemetry'))
    for name,value in [('analyses.json',analyses),('summary.json',summary),('phase_means.json',phases),('launch_ledger.json',launch),('resources.json',resources),('drift.json',drift),('memory.json',mem),('cost_accounting.json',cost),('anchor_sensitivity.json',anchor_sensitivity)]:save(name,value)
    print(json.dumps(summary,indent=2,ensure_ascii=False))
if __name__=='__main__':main()
