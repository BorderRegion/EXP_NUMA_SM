"""CPU-only evidence tables from immutable completed workers; no CUDA context."""
import collections,csv,datetime,hashlib,json,math,pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/'derived/implementation_v1'
def save(name,data):
 (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def table(name,rows):
 if not rows:return
 with (OUT/name).open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def flat(nodes):
 for n in nodes:
  yield n
  yield from flat(n.get('children',[]))
def packet(adapter):
 bm,bn,bk=[adapter['resources'][0][f'tile_{x}'] for x in ('m','n','k')]
 workers=adapter['workers'];total=adapter['total_tiles'];hist=collections.Counter();qs=[];tails=0;changed=False
 for m,n,k in adapter['shapes']:
  mt,nt,kt=math.ceil(m/bm),math.ceil(n/bn),math.ceil(k/bk)
  if not mt or not nt:continue
  cap=min(adapter['q_cap'],mt)
  if adapter['mode']==2:cap=min(cap,max(1,total//(workers*adapter['target_waves'])),max(1,adapter['work_budget_k_tiles']//kt))
  q=4 if cap>=4 else 2 if cap>=2 else 1;qs.append(q)
  for start in range(0,mt,q):
   length=min(q,mt-start);hist[length]+=nt;tails+=int(length<q)*nt
  # Original native ordinal is m-major then n; packet ordinal is n-major then m.
  changed|=mt>1 and nt>1
 assert sum(k*v for k,v in hist.items())==total
 return dict(tiles=total,workers=workers,packets=sum(hist.values()),q_per_nonempty_problem=qs,
    length_counts=dict(hist),tail_packets=tails,multitile_tiles=sum(k*v for k,v in hist.items() if k>1),
    has_q_gt1=any(q>1 for q in qs),q1_can_change_native_order=changed)

def main():
 OUT.mkdir(parents=True,exist_ok=True)
 manifests=[json.loads(s) for s in (ROOT/'registry/runs.jsonl').read_text().splitlines()]
 manifests=[m for m in manifests if m['key'].startswith(('implementation_','cutlass_'))]
 packets=[];launch=[];cost=[];hashes=collections.defaultdict(set);resources={};throughput=[]
 for manifest in manifests:
  if manifest['status']!='COMPLETED':continue
  folder=ROOT/manifest['path'];cohort=manifest['key'].rsplit('_block_',1)[0]
  for path in folder.glob('*.json'):
   row=json.loads(path.read_text())
   if not isinstance(row,dict) or row.get('status') not in ('IMPLEMENTED_OPERATOR_COMPARISON','IMPLEMENTED_LAYER_COMPARISON'):continue
   ident=row['case']['case_id'];suite=row['case']['suite'];block=row['block'];base=dict(cohort=cohort,case_id=ident,block=block)
   for variant,meta in row['metadata'].items():
    adapters={'operator':meta['adapter']} if 'adapter' in meta else {name:meta[name] for name in ('up','down') if name in meta}
    for component,adapter in adapters.items():
     hashes['binary'].add(adapter['binary_sha256'])
     for mode,res in enumerate(adapter['resources']):resources[f"recipe{adapter['recipe']}_mode{mode}"]=res
     if adapter['mode'] not in (1,2):continue
     stats=packet(adapter)
     recorded=meta.get('packets') if component=='operator' else meta.get(component+'_packets')
     if recorded is not None:
      assert recorded['tiles']==stats['tiles'] and recorded['packets']==stats['packets']
      assert {int(k):v for k,v in recorded['length_counts'].items()}==stats['length_counts']
     packets.append(dict(**base,variant=variant,component=component,recipe=adapter['recipe'],mode=adapter['mode'],q_cap=adapter['q_cap'],waves=adapter['target_waves'],**stats))
    graph=meta.get('graph_structure',row.get('graph_structure',{}).get(variant))
    if graph:
     nodes=list(flat(graph['nodes']));types=collections.Counter(n['type'] for n in nodes)
     is_candidate=bool(adapters);e=len(next(iter(adapters.values()))['shapes']) if adapters else None
     launch.append(dict(**base,variant=variant,scope=row['scope'],kernel_nodes=types[0],memcpy_nodes=types[1],memset_nodes=types[2],
      step_H2D_bytes=0,step_D2H_bytes=0,extra_plan_launches=0,host_waits_inside=0,
      result_boundary_waits_per_request=1 if suite=='moe_layer' else 'one per measurement batch',
      static_descriptor_bytes=60*e*len(adapters) if is_candidate else 'not independently counted',
      per_step_sideband_bytes=8 if variant.startswith('F1') else 0,
      evidence='read-only captured CUDA Graph node census + wrapper source transfer/wait audit; not hardware trace'))
   for name,sha in row.get('source_sha256',{}).items():hashes[name].add(sha)
   phase_wall=sum((datetime.datetime.fromisoformat(p['end'])-datetime.datetime.fromisoformat(p['start'])).total_seconds() for p in row['phases'])
   cost.append(dict(**base,elapsed_s=row['elapsed_s'],all_phases_including_warmup_wall_s=phase_wall,
      other_setup_validation_pilot_graph_and_python_s=row['elapsed_s']-phase_wall,
      disaggregation='Residual is NOT deployment initialization or JIT cost; individual prep stages were not separately timed'))
   for phase in row['phases']:
    if phase['phase_role']!='primary':continue
    flops=row['ledger'].get('effective_flops');logical=row['ledger'].get('logical_tensor_bytes')
    throughput.append(dict(**base,variant=phase['variant'],device_ms=phase['device_interval_ms'],ready_ms=phase['operator_or_layer_ready_ms'],
      effective_flops=flops,logical_tensor_bytes=logical,effective_tflops=flops/(phase['device_interval_ms']*1e9) if flops else None,
      logical_gb_s=logical/(phase['device_interval_ms']*1e6) if logical else None,
      scope='Resident logical tensor bytes include zero-row experts weights, NOT accessed bytes or actual DRAM traffic; FLOPs count GEMM arithmetic only'))
 save('packet_applicability.json',packets);save('source_stability.json',{k:sorted(v) for k,v in hashes.items()});save('actual_resources.json',resources)
 table('LAUNCH_AND_TRANSFER_LEDGER.csv',launch);table('COST_ACCOUNTING.csv',cost);table('THROUGHPUT_AND_LOGICAL_BYTES.csv',throughput)
 print(json.dumps(dict(packet_records=len(packets),launch_records=len(launch),source_versions={k:len(v) for k,v in hashes.items()}),indent=2))

if __name__=='__main__':main()
