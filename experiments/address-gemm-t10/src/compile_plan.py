"""CPU-only compiler for a measured real-GEMM address cost matrix.
The emitted metadata binds the plan to the original allocation; reallocation
requires fresh calibration. This tool makes no deployment-speed guarantee.
"""
from common import *
import argparse,numpy as np,time
from schedule import all_maps

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--calibration',type=Path,required=True);ap.add_argument('--metadata',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--portable',action='store_true');a=ap.parse_args()
 if not a.portable:
  try:
   from fast_schedule import enable
   enable()
  except (OSError,ImportError):pass
 v=np.load(a.calibration)['values'];meta=read(a.metadata);assert v.shape[0]==3 and v.shape[1]==56 and v.shape[-2:]==(4,2);cost=np.median(v[:2,:,:,0,0].astype(float),axis=0)
 t=time.perf_counter();maps,_=all_maps(cost,meta['seed']);dt=(time.perf_counter()-t)*1000
 write(a.out,dict(kind='address-aware split-K reduction',allocation_workspace_va=meta['workspace_va'],allocation_output_va=meta['output_va'],allocation_frozen_ns=meta['frozen_ns'],validity='Original allocation lifetime only; equal VA after reallocation is insufficient. Recalibrate after allocation or workload changes.',chunk_floats=2048,sm_count=56,map=maps['ADDRESS'].tolist(),source_calibration_sha256=sha(a.calibration),compile_ms=dt,performance_status='Experimental; complete GEMM slower than original in current six-process campaign'))
 print('PLAN_COMPILED',a.out)
if __name__=='__main__':main()
