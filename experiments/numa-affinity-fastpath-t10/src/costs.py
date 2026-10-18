from common import *
import numpy as np,collections,math
def main():
 page=read(ROOT/'freeze/MAILBOX_CHOICE.json')['page'];cells=read(ROOT/'derived/const_confirm.json')['cells'];setup=collections.defaultdict(list)
 for p in RUN.glob('api_*/api.json'):
  for x in read(p):setup[x['V'],x['policy']].append(x['setup_ms'])
 offline=sum(read(RUN/f'soft_tensor_{i}/manifest.json')['worker_seconds'] for i in [0,1])+read(ROOT/'freeze/SOFTMAX_MAPS.json')['fit_ms']/1000;rows=[]
 for V in [32768,65536,131072,262144]:
  case='VOCAB_'+str(V);z=collections.defaultdict(dict)
  for x in cells:
   if x['case']==case and x['scope']=='ready' and x['offset']==page:z[x['process'],x['block']][x['label']]=x['gpu']
  for baseline in ['NATIVE','IDENTITY']:
   saving=float(np.mean([v[baseline]-v['MINIMAX'] for v in z.values()]));base_ms=float(np.median(setup[V,baseline]));method_ms=float(np.median(setup[V,'MINIMAX']));delta=method_ms-base_ms
   rows.append(dict(V=V,page=page,baseline=baseline,paired_mean_saving_us=saving,baseline_plan_ms=base_ms,method_plan_ms=method_ms,observed_setup_difference_ms=delta,offline_model_reused_break_even_requests=math.ceil(max(delta,0)*1000/saving) if saving>0 else None,recalibrate_this_device_break_even_requests=math.ceil((offline*1e6+max(delta,0)*1000)/saving) if saving>0 else None))
 write(ROOT/'derived/COSTS.json',dict(offline_training_and_fit_seconds=offline,logical_mailbox_arena_bytes=2<<20,allocated_alignment_storage_bytes=4<<20,method_other_tensor_scratch_bytes=896,native_tensor_scratch_bytes=897,output_bytes_per_vocab_entry=4,rows=rows,limitations='Descriptive point estimates across3 setup processes and6 timing processes, not a cold-start confidence guarantee. Negative measured setup differences are retained but clamped to0 only in break-even arithmetic. Calibration cost is this research implementation including host/I/O, not an optimized production lower bound. Gains conditional on measured allocation/stream contract.'))
 print('COSTS_WRITTEN')
if __name__=='__main__':main()
