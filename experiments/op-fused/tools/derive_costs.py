"""Algebraic useful work and tensor payload; never measured DRAM traffic."""
import csv,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1];D=ROOT/'derived/native_v1'
rows=[]
for x in json.loads((D/'case_results.json').read_text()):
 c=x['case'];suite=c['suite'];resident=None;payload=None
 if suite=='grouped':ms=c['rows_per_expert'];ks=[c['k']]*len(ms);ns=[c['n']]*len(ms)
 elif suite=='dense_control':ms=[c['m']];ks=[c['k']];ns=[c['n']]
 elif suite=='heterogeneous_k':ks=c['k_per_problem'];ms=[c['m']]*len(ks);ns=[c['n']]*len(ks)
 if suite in ['grouped','dense_control','heterogeneous_k']:
  flops=sum(2*m*k*n for m,k,n in zip(ms,ks,ns));payload=sum(2*(m*k+k*n+m*n) for m,k,n in zip(ms,ks,ns) if m>0)
  resident=sum(2*k*n for k,n in zip(ks,ns));domain='USEFUL_GEMM_FLOPS_AND_ONE_COPY_OF_ACTIVE_A_B_C; inactive weights remain resident but excluded from active payload'
 elif suite=='moe_layer':
  flops=6*c['tokens']*c['top_k']*c['hidden']*c['intermediate'];resident=6*c['experts']*c['hidden']*c['intermediate'];domain='GEMM_FLOPS_ONLY; total pipeline logical bytes not separately derived'
 elif suite in ['attention_decode','prefill_control']:
  total=sum(c['lengths']) if 'lengths' in c else c['batch']*c['kv_length'];flops=4*c['q_heads']*c['query_length']*total*c['head_dim']
  payload=4*total*c['kv_heads']*c['head_dim']+4*c['batch']*c['q_heads']*c['query_length']*c['head_dim'];domain='QK_AND_AV_CONTRACTION_FLOPS; one logical FP16 Q/K/V/output payload; no softmax/layout/metadata FLOPs'
 else:continue
 for name,v in x['variants'].items():
  ms=v['mean_ms'];rows.append(dict(case_id=c['case_id'],suite=suite,split=c['split'],variant=name,process_blocks=x['baseline_blocks'],mean_amortized_interval_ms=ms,useful_contraction_flops=flops,active_tensor_payload_bytes=payload,resident_weights_bytes=resident,effective_contraction_TFLOPs_per_s=flops/ms/1e9,one_payload_GB_per_s=payload/ms/1e6 if payload else None,domain=domain,actual_DRAM_bytes=None,actual_GPU_busy_time=None,resource_peak_margin_review=x.get('resource_qualification','NO_RECORDED_RESERVED_PEAK_THRESHOLD_FLAG')))
with (D/'logical_work_and_payload.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print('derived cost rows',len(rows))
