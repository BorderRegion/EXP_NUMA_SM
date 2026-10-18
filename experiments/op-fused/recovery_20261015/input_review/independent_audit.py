"""Read-only CPU review of the supplied OP-FUSED T10 archive.
Does not import submitted runners, invoke a compiler, execute GPU code, or access network.
"""
from pathlib import Path
import json,hashlib,csv,collections,math,re,datetime,ast,argparse
import numpy as np
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--input',type=Path,required=True,help='Unpacked original archive root')
ap.add_argument('--output',type=Path,required=True,help='New CPU-only review directory')
args=ap.parse_args()
ROOT=args.input.resolve();OUT=args.output.resolve(); OUT.mkdir(parents=True,exist_ok=True)
def load(p):return json.loads(p.read_text())
def dump(n,x):(OUT/n).write_text(json.dumps(x,ensure_ascii=False,indent=2))
def eff(values):
 a=np.asarray(values,dtype=float); ratio=float(np.exp(a.mean()));ci=None
 if len(a)>1:
  g=np.random.default_rng(2026101509)
  z=np.exp(a[g.integers(0,len(a),(20000,len(a)))].mean(1))
  ci=list(map(float,np.quantile(z,[.025,.975])))
 return {'ratio':ratio,'ci95':ci,'blocks':len(a),'block_log_ratios':a.tolist()}
def flatten(nodes):
 ans=[]
 for n in nodes:
  ans.append(n);ans+=flatten(n.get('children',[]))
 return ans
issues=[]
manifest=load(ROOT/'FILES_SHA256.json');manifest_ok=0
for e in manifest:
 p=ROOT/e['path']
 if not p.is_file() or p.stat().st_size!=e['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=e['sha256']:issues.append(['manifest',e['path']])
 else:manifest_ok+=1
actual={str(p.relative_to(ROOT)) for p in ROOT.rglob('*') if p.is_file()};indexed={e['path'] for e in manifest}
reg=[json.loads(s) for s in (ROOT/'registry/runs.jsonl').read_text().splitlines()]
run_windows=sorted([(datetime.datetime.fromisoformat(m['process_started_at']),datetime.datetime.fromisoformat(m['process_ended_at']),m['run_id']) for m in reg])
overlap=[]
for a,b in zip(run_windows,run_windows[1:]):
 if a[1]>b[0]:overlap.append([a[2],b[2]])
source_checks=[]
for m in reg:
 p=ROOT/m['path'];s=p/'source_snapshot.py'
 if s.exists():
  ok=hashlib.sha256(s.read_bytes()).hexdigest()==m['source_sha256'];source_checks.append(ok)
  if not ok:issues.append(['snapshot_hash',str(s.relative_to(ROOT))])
 rt=p/'runtime.json'
 if rt.exists():
  v=load(rt)
  for name,h in v.get('shared_sources',{}).items():
   dep=p/('dependency_'+name)
   if not dep.exists() or hashlib.sha256(dep.read_bytes()).hexdigest()!=h:issues.append(['dependency',str(dep.relative_to(ROOT))])
cohorts={'native':[], 'strong':[], 'request':[]}; failures=[]
for m in reg:
 if re.fullmatch(r'E[1345]_native_block_[0-5]',m['key']):c='native'
 elif re.fullmatch(r'E[134]_strong_block_[0-5]',m['key']):c='strong'
 elif re.fullmatch(r'E4_request_block_[0-5]',m['key']):c='request'
 else:continue
 for p in sorted((ROOT/m['path']).glob('*.json')):
  x=load(p)
  if not isinstance(x,dict) or 'case' not in x:continue
  x['_stage']=m['stage'];x['_ref']=str(p.relative_to(ROOT));x['_cohort']=c
  if not x.get('phases'):failures.append({'cohort':c,'case':x['case']['case_id'],'block':x.get('block'),'status':x['status'],'error':x.get('error'),'ref':x['_ref']});continue
  cohorts[c].append(x)
stats={};checks_total=0;req_counts=0;req_mean_checks=0
for c,rows in cohorts.items():
 phases=[p for x in rows for p in x['phases']];checks=[y for p in phases for y in p.get('correctness',[])]
 stats[c]={'case_blocks':len(rows),'cases':len({x['case']['case_id'] for x in rows}),'phases':len(phases),'output_check_summaries':len(checks),'all_reported_check_pass':all(x['pass'] for x in checks),'max_reported_relative_frobenius':max((x['relative_frobenius'] for x in checks),default=None)}
 checks_total+=len(checks)
 for x in rows:
  for p in x['phases']:
   n=p['measured_requests'];d=p['device_interval_ms'];r=p['operator_or_layer_ready_ms']
   if not(n>0 and math.isfinite(d) and math.isfinite(r) and d>0 and r>0):issues.append(['duration',x['_ref']])
   if 'aggregate_device_ms' in p and not math.isclose(d*n,p['aggregate_device_ms'],rel_tol=1e-10,abs_tol=1e-7):issues.append(['aggregate_time',x['_ref']])
   if 'request_ready_ms' in p:
    req_counts+=len(p['request_ready_ms']); req_mean_checks+=2
    if len(p['request_ready_ms'])!=n or len(p['request_device_ms'])!=n:issues.append(['request_length',x['_ref']])
    if not math.isclose(float(np.mean(p['request_ready_ms'])),r,rel_tol=1e-10,abs_tol=1e-8):issues.append(['request_ready_mean',x['_ref']])
    if not math.isclose(float(np.mean(p['request_device_ms'])),d,rel_tol=1e-10,abs_tol=1e-8):issues.append(['request_device_mean',x['_ref']])
# Independent per-case paired effects versus submitted derived outputs.
paired=[];max_err=0;comparison_count=0
native_by=collections.defaultdict(list)
for x in cohorts['native']:native_by[x['case']['case_id']].append(x)
for reported in load(ROOT/'derived/native_v1/case_results.json'):
 ident=reported['case']['case_id'];data=native_by.get(ident,[])
 if len(data)!=reported['baseline_blocks']:issues.append(['native_blocks',ident])
 for label,v in reported.get('effects',{}).items():
  a,b=label.split('/');logs=[]
  for x in sorted(data,key=lambda x:x['block']):
   pp={p['variant']:p for p in x['phases'] if p['phase_role']=='primary'}
   logs.append(math.log(pp[a]['device_interval_ms']/pp[b]['device_interval_ms']))
  e=eff(logs);err=max(abs(e['ratio']-v['ratio']),max((abs(u-w) for u,w in zip(e['ci95'] or [],v['ci95'] or [])),default=0));max_err=max(max_err,err);comparison_count+=1
  paired.append({'cohort':'native','case':ident,'comparison':label,'metric':'device',**e})
strong_by=collections.defaultdict(list)
for x in cohorts['strong']:strong_by[x['_stage'],x['case']['case_id']].append(x)
for v in load(ROOT/'derived/native_v1/strong_library_results.json'):
 data=strong_by[v['stage'],v['case_id']]
 for ep,key in [('device','device_interval_ms'),('ready','operator_or_layer_ready_ms')]:
  logs=[]
  for x in sorted(data,key=lambda x:x['block']):
   pp={p['variant']:p for p in x['phases'] if p['phase_role']=='primary'}
   logs.append(math.log(pp['NATIVE_GROUPED_GRAPH'][key]/pp['PER_EXPERT_GRAPH'][key]))
  e=eff(logs);z=v['native_over_per_expert'][ep];max_err=max(max_err,abs(e['ratio']-z['ratio']),max(abs(u-w) for u,w in zip(e['ci95'],z['ci95'])));comparison_count+=1
  paired.append({'cohort':'strong','stage':v['stage'],'case':v['case_id'],'comparison':'native_grouped/per_expert','metric':ep,**e})
request_by=collections.defaultdict(list)
for x in cohorts['request']:request_by[x['case']['case_id']].append(x)
for v in load(ROOT/'derived/native_v1/layer_request_results.json'):
 data=request_by[v['case_id']];logs=[]
 for x in sorted(data,key=lambda x:x['block']):
  pp={p['variant']:p for p in x['phases'] if p['phase_role']=='primary'}
  logs.append(math.log(pp['CUBLAS_GRAPH_REQUEST']['operator_or_layer_ready_ms']/pp['CUBLAS_EAGER_REQUEST']['operator_or_layer_ready_ms']))
 e=eff(logs);z=v['graph_over_eager_ready'];max_err=max(max_err,abs(e['ratio']-z['ratio']),max(abs(u-w) for u,w in zip(e['ci95'],z['ci95'])));comparison_count+=1
 paired.append({'cohort':'request','case':v['case_id'],'comparison':'graph/eager','metric':'ready',**e})
if max_err>1e-9:issues.append(['paired_discrepancy',max_err])
# Graph structure inspection for all actually stored graph node records.
graph_rows=[];summary_rows=[]
for (stage,ident),xs in sorted(strong_by.items()):
 a_nodes=[];b_nodes=[];namesA=collections.Counter();namesB=collections.Counter()
 ratios=[]
 for x in sorted(xs,key=lambda x:x['block']):
  pp={p['variant']:p for p in x['phases'] if p['phase_role']=='primary'}
  ratios.append(math.log(pp['NATIVE_GROUPED_GRAPH']['operator_or_layer_ready_ms']/pp['PER_EXPERT_GRAPH']['operator_or_layer_ready_ms']))
  counts={}
  for name,g in x['graph_structure'].items():
   nodes=flatten(g['nodes']);ks=[n for n in nodes if n['type']==0];counts[name]=len(ks)
   for n in ks:(namesA if name=='NATIVE_GROUPED_GRAPH' else namesB)[n.get('name','UNKNOWN')]+=1
   graph_rows.append({'stage':stage,'case_id':ident,'block':x['block'],'variant':name,'kernel_nodes':len(ks),'raw_ref':x['_ref']})
  a_nodes.append(counts['NATIVE_GROUPED_GRAPH']);b_nodes.append(counts['PER_EXPERT_GRAPH'])
 e=eff(ratios)
 summary_rows.append({'stage':stage,'case_id':ident,'case':xs[0]['case'],'blocks':len(xs),'native_kernel_nodes':sorted(set(a_nodes)),'per_expert_kernel_nodes':sorted(set(b_nodes)),'native_kernel_names':dict(namesA),'per_expert_kernel_names':dict(namesB),'ready_ratio':e})
oldcensus=load(ROOT/'derived/native_v1/strong_library_graph_census.json');index={(x['stage'],x['case_id'],x['block'],x['variant']):x for x in oldcensus}
for row in graph_rows:
 k=tuple(row[y] for y in ['stage','case_id','block','variant'])
 if row['kernel_nodes']!=index[k]['kernel_nodes']:issues.append(['graph_count',k])
# Selection criterion: equal-case, available block averages. Not alternative block weighting.
freeze=load(ROOT/'preregistration/strong_library_freeze.json')
v=[]
for (stage,c),xs in strong_by.items():
 if stage!='E1':continue
 logs=[]
 for x in xs:
  pp={p['variant']:p for p in x['phases'] if p['phase_role']=='primary'}
  logs.append(math.log(pp['NATIVE_GROUPED_GRAPH']['device_interval_ms']/pp['PER_EXPERT_GRAPH']['device_interval_ms']))
 v.append(float(np.mean(logs)))
sel=math.exp(float(np.mean(v)))
# Independent timed output prefix checks: those summaries are not tensors.
ptx=[]
for p in ROOT.glob('runs/**/*.ptx'):
 s=p.read_text();ptx.append({'path':str(p.relative_to(ROOT)),'has_mma_instruction':bool(re.search(r'\b(?:mma\.sync|wmma\.mma|wgmma\.mma)',s)),'fma_rn_f32_count':len(re.findall('fma.rn.f32',s)),'target':re.findall(r'\.target\s+([^\n]+)',s)})
# q degeneracy from formula, no importing project generator.
plan=[json.loads(s) for s in (ROOT/'preregistration/plan.jsonl').read_text().splitlines()]
qrows=[]
for bm in [32,64]:
 for workers in [56,112]:
  devke=sorted([math.ceil(c['k']/32) for c in plan if c['suite']=='grouped' and c['split']=='calibration' for m in c['rows_per_expert'] if m])
  work=2*math.ceil(float(np.quantile(devke,.75)))
  counts=collections.Counter();k4096=collections.Counter()
  for c in plan:
   if c['suite']!='grouped':continue
   rows=c['rows_per_expert'];mts=[math.ceil(m/bm) for m in rows];nt=math.ceil(c['n']/128);ke=math.ceil(c['k']/32);tt=sum(mts)*nt
   qs=[]
   for mt in mts:
    if not mt:qs.append(0);continue
    z=min(4,max(1,tt//workers),max(1,work//ke),mt);qs.append(1<<(z.bit_length()-1))
   deg=max(qs,default=0)<=1;counts[str((c['split'],deg))]+=1
   if c['k']==4096:k4096[str(deg)]+=1
  qrows.append({'bm':bm,'workers':workers,'work_budget_k_tiles':work,'counts':dict(counts),'k4096':dict(k4096)})
# Aggregate independent stage effects with complete E3/E4 cohorts.
aggregate={}
for stage in ['E3','E4']:
 aggregate[stage]={}
 for ep,key in [('device','device_interval_ms'),('ready','operator_or_layer_ready_ms')]:
  perblock=collections.defaultdict(list)
  for x in cohorts['strong']:
   if x['_stage']!=stage:continue
   pp={p['variant']:p for p in x['phases'] if p['phase_role']=='primary'}
   perblock[x['block']].append(math.log(pp['NATIVE_GROUPED_GRAPH'][key]/pp['PER_EXPERT_GRAPH'][key]))
  aggregate[stage][ep]=eff([float(np.mean(z)) for _,z in sorted(perblock.items())])
# Saved power records / journal classifications, descriptive not causal.
events=load(ROOT/'reports/thermal_controller_events.json')
def pc(phase):
 st=datetime.datetime.fromisoformat(phase['start']).timestamp();en=datetime.datetime.fromisoformat(phase['end']).timestamp();state=125
 for ev in events:
  if ev['epoch_s']<=st:state=ev['power_limit_w']
 ss={state}|{ev['power_limit_w'] for ev in events if st<ev['epoch_s']<=en}
 return str(next(iter(ss)))+'W' if len(ss)==1 else 'TRANSITION'
powerstats={c:dict(collections.Counter(pc(p) for x in xs for p in x['phases'])) for c,xs in cohorts.items()}
strongpow={st:dict(collections.Counter(pc(p) for x in cohorts['strong'] if x['_stage']==st for p in x['phases'])) for st in ['E1','E3','E4']}
checks_output={'scope':'Only archive data and source; no GPU, no tensors recomputed, no binary/SASS independently generated','manifest_entries':len(manifest),'manifest_verified':manifest_ok,'unlisted_files':sorted(actual-indexed),'missing_indexed':sorted(indexed-actual),'registry_runs':len(reg),'source_snapshots_checked':len(source_checks),'source_snapshots_ok':sum(source_checks),'worker_seconds_sum':sum(m['worker_occupied_s'] for m in reg),'overlapping_process_windows':overlap,'cohorts':stats,'formal_phase_total':sum(z['phases'] for z in stats.values()),'formal_failures':failures,'output_summary_checks_total':checks_total,'per_request_ready_samples_recomputed':req_counts,'per_request_device_samples_recomputed':req_counts,'per_request_mean_comparisons':req_mean_checks,'paired_comparisons_recomputed':comparison_count,'paired_max_abs_error':max_err,'graph_record_comparisons':len(graph_rows),'selection_equal_case_ratio':sel,'reported_selection_ratio':freeze['native_over_per_expert'],'strong_stage_aggregates':aggregate,'power_conditions':powerstats,'strong_power_by_stage':strongpow,'ptx_evidence':ptx,'q_degeneracy':qrows,'issues':issues}
# Inspect the already disclosed request-time/lock-time provenance distinction.
hs=collections.defaultdict(set)
for m in reg:
 if '_native_block_' not in m['key']:continue
 tree=ast.parse((ROOT/m['path']/'source_snapshot.py').read_text())
 for n in tree.body:
  if not isinstance(n,ast.FunctionDef):continue
  active=n.name in ['phase','capture'] or n.name=='grouped' and m['stage'] in ['E1','E3'] or n.name=='layer' and m['stage']=='E4' or n.name=='attention' and m['stage']=='E5'
  if active:hs[n.name].add(hashlib.sha256(ast.dump(n,include_attributes=False).encode()).hexdigest())
checks_output['active_native_function_ast_hash_counts']={k:len(v) for k,v in hs.items()}
known=load(ROOT/'reports/SOURCE_PROVENANCE_AUDIT.json')['source_hash_mismatches']
checks_output['source_snapshot_mismatches_disclosed_in_package']=len(known)==sum(x[0]=='snapshot_hash' for x in issues)
checks_output['source_provenance_boundary']='Five request-time versus lock-time source hash differences already disclosed. Active function ASTs checked only for the stages that use them; not a full runtime dependency or GPU binary equivalence proof.'
checks_output['unexpected_integrity_or_statistics_errors']=[x for x in issues if x[0]!='snapshot_hash']
checks_output['worker_budget_note']='Registry monotonic occupied-time sum used here; report budget uses timestamp-derived accounting and differs by less than one second. Neither is pure GPU busy time.'
dump('independent_audit.json',checks_output);dump('paired_recalculations.json',paired);dump('graph_and_cost_by_case.json',summary_rows)
with (OUT/'graph_node_counts.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(graph_rows[0]));w.writeheader();w.writerows(graph_rows)
print(json.dumps({k:checks_output[k] for k in ['manifest_entries','manifest_verified','unlisted_files','registry_runs','cohorts','formal_phase_total','output_summary_checks_total','per_request_ready_samples_recomputed','paired_comparisons_recomputed','paired_max_abs_error','graph_record_comparisons','selection_equal_case_ratio','strong_power_by_stage','issues']},ensure_ascii=False,indent=2))
