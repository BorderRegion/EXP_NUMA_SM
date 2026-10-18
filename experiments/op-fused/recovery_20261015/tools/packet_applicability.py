"""Development-only applicability from actual backend resource evidence, or NA."""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('protocol_reference',ROOT.parent/'protocol/tools/reference.py')
ref=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ref;spec.loader.exec_module(ref)

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--backend-evidence',type=Path)
 p.add_argument('--out',type=Path,required=True)
 a=p.parse_args()
 plans=[json.loads(s) for s in (ROOT.parent/'preregistration/plan.jsonl').read_text().splitlines()]
 # The plan uses development, not test performance, to define the work proxy.
 development=[c for c in plans if c['suite']=='grouped' and c['split']=='calibration']
 if not development:
  raise ValueError('No development cases; inspect schema rather than silently using test cases')
 result=dict(status='ACTUAL_BODY_UNAVAILABLE',candidate_timed=False,
     actual_tile=None,actual_workers=None,work_budget_amended=False,
     q1_native_identity='UNKNOWN_WITHOUT_NATIVE_VISITOR',cases=[])
 if not a.backend_evidence:
  for c in development:
   result['cases'].append(dict(case_id=c['case_id'],k=c['k'],q=None,total_tiles=None,
       packets=None,tail_packets=None,status='NA_NO_QUALIFIED_BODY'))
 else:
  evidence=json.loads(a.backend_evidence.read_text())
  required=['tile_m','tile_n','tile_k','active_workers','backend_commit',
            'worker_evidence_path','mma_evidence_path','numerical_qualification_path']
  for key in required:
   if not evidence.get(key):raise ValueError('Missing actual backend field '+key)
  for key in required[-3:]:
   path=Path(evidence[key]);path=path if path.is_absolute() else a.backend_evidence.parent/path
   if not path.is_file():raise ValueError('Missing evidence file '+str(path))
  bm,bn,bk,W=[evidence[k] for k in required[:4]]
  if any(type(x)!=int or x<=0 for x in [bm,bn,bk,W]):raise ValueError('Positive actual tile/workers required')
  ks=sorted(ref.ceil_div(c['k'],bk) for c in development for m in c['rows_per_expert'] if m)
  # Nearest rank, upward rounded 75th percentile, exactly as original rule.
  budget=2*ks[(3*len(ks)+3)//4-1]
  result.update(status='CPU_APPLICABILITY_FROM_SUPPLIED_BACKEND_EVIDENCE',
      actual_tile=[bm,bn,bk],actual_workers=W,work_budget_k_tiles=budget,
      backend_evidence=evidence)
  for c in development:
   problems=[ref.Problem(m,c['n'],c['k']) for m in c['rows_per_expert']]
   for cap in [1,2,4]:
    for waves in [1,2]:
     packets=ref.make_packets(problems,bm,bn,bk,W,cap,waves,budget)
     total=sum(ref.ceil_div(p.m,bm)*ref.ceil_div(p.n,bn) for p in problems)
     q_by_expert={}
     for e,pr in enumerate(problems):
      mt,nt,kt=ref.ceil_div(pr.m,bm),ref.ceil_div(pr.n,bn),ref.ceil_div(pr.k,bk)
      q_by_expert[e]=0 if not mt or not nt else ref.floor_pow2(min(cap,max(1,total//(W*waves)),max(1,budget//kt),mt))
     result['cases'].append(dict(case_id=c['case_id'],q_cap=cap,target_waves=waves,
       total_tiles=total,q_by_expert=q_by_expert,packets=len(packets),
       tail_packets=sum(p.length<q_by_expert[p.problem] for p in packets),
       multitile_packets=sum(p.length>1 for p in packets)))
 a.out.parent.mkdir(parents=True,exist_ok=True)
 a.out.write_text(json.dumps(result,indent=2)+'\n')
 print(result['status'],len(result['cases']),'rows')

if __name__=='__main__':main()
