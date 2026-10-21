"""CPU-only analysis; complete processes are the statistical units."""
from common import *
import numpy as np,collections,sys
if len(sys.argv)>1:RUN=Path(sys.argv[1]).resolve()
measured=[];expanded=[];sources=[];anchors=[]
for f in sorted((RUN/'raw').glob('*/PHASES.json')):
 folder=f.parent
 if not (folder/'COMPLETE.json').exists() or read(folder/'manifest.json')['status']!='COMPLETED':continue
 ph=read(f);measured.extend(ph);sources.append(dict(worker=folder.name,sha256=sha(f)))
 for a in read(folder/'ALIASES.json'):
  for label,source in a['aliases'].items():
   r=next(x for x in ph if x['case']==a['case'] and x['task']==a['task'] and x['role']=='PRIMARY' and x['label']==source)
   expanded.append(dict(r,label=label,measured_label=source,is_alias=label!=source,requested_action=a['requested_actions'][label],raw_source=str(f.relative_to(RUN))))
sel=read(RUN/'freeze/SELECTION.json') if (RUN/'freeze/SELECTION.json').exists() else {}
out=RUN/'derived';out.mkdir(exist_ok=True)
write(out/'MEASURED_PHASES.json',measured);write(out/'EXPANDED_LABELS.json',expanded);write(out/'SOURCES.json',sources)
indices={n:np.random.default_rng(194500000+n).integers(0,n,size=(5000,n)) for n in [4,6]}
def stat(ratios,level=.95,alias=False):
 r=np.array(ratios,float);assert np.isfinite(r).all() and (r>0).all();logs=np.log(r);mean=float(np.exp(logs.mean()));q=(1-level)/2;ci=np.exp(np.quantile(logs[indices[len(r)]].mean(axis=1),[q,1-q]))
 return dict(time_ratio=mean,time_change_percent=100*(mean-1),ci_level=level,ci_time_ratio=ci.tolist(),ci_change_percent=(100*(ci-1)).tolist(),block_ratios=r.tolist(),faster_blocks=int((r<1).sum()),blocks=len(r),structural_alias_all_blocks=alias,statistical_unit='whole process block; same one device',bootstrap_draws=5000)
def rows(stage,cid,label):return sorted([x for x in expanded if x['stage']==stage and x['case']==cid and x['label']==label],key=lambda x:x['block'])
comparisons=[]
def compare(stage,cid,label,reference,level=.95,tag=''):
 a,b=rows(stage,cid,label),rows(stage,cid,reference);expected=4 if stage=='HOLDOUT' else 6
 if len(a)!=expected or len(b)!=expected:return
 assert [x['block'] for x in a]==[x['block'] for x in b]
 for metric in ['job_output_ready_us','job_gpu_us','foreground_completion_us','background_completion_us']:
  same=all(x['measured_label']==y['measured_label'] for x,y in zip(a,b))
  comparisons.append(dict(stage=stage,case=cid,label=label,reference=reference,metric=metric,tag=tag,candidate_block_us=[x[metric] for x in a],reference_block_us=[x[metric] for x in b],**stat([x[metric]/y[metric] for x,y in zip(a,b)],level,same)))
for stage in ['S3','HOLDOUT']:
 for cid in ['LONG','RAGGED']:
  if cid not in sel:continue
  for label in ['SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','SHARED56','Q_ONLY','SIMPLE_SPREAD','JOINT_POOL']:
   for ref in ['SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','SHARED56']:compare(stage,cid,label,ref)
  bestnat=sel[cid]['BEST_NATIVE']['label'];best=sel[cid]['BEST_SIMPLE']['action']
  if best['family']=='NATIVE':bestsimple=best['mode']
  else:bestsimple=next(x for x in ['Q_ONLY','SIMPLE_SPREAD'] if sel[cid][x]['action']==best)
  compare(stage,cid,'JOINT_POOL',bestnat,.975 if stage=='S3' else .95,'FROZEN_BEST_NATIVE')
  compare(stage,cid,'JOINT_POOL',bestsimple,.975 if stage=='S3' else .95,'FROZEN_BEST_SIMPLE')
  if stage=='S3':
   for label in ['ABLATE_PACK','ABLATE_SPREAD']:compare(stage,cid,label,'ABLATE_NEUTRAL',.95,'SAME_QUOTA_MODE_K')
   for label in ['ABLATE_NEUTRAL','ABLATE_PACK','ABLATE_SPREAD']:
    for ref in ['SERIAL_GQA_FIRST','SERIAL_GEMM_FIRST','SHARED56']:compare(stage,cid,label,ref,.95,'DESCRIPTIVE_ABLATION_VS_NATIVE_NOT_SELECTED')
   pc=sel[cid]['PC_STAR']['action'];chosen='ABLATE_'+pc['family'];release,fixed=(chosen,'ABLATE_OTHER_MODE') if pc['mode']=='RELEASE' else ('ABLATE_OTHER_MODE',chosen)
   compare(stage,cid,release,fixed,.95,'RELEASE_VS_FIXED')
for stage in ['S3','HOLDOUT']:
 for cid in ['LONG','RAGGED']:
  metric='job_output_ready_us';rr=[x for x in measured if x['stage']==stage and x['case']==cid and x['role']!='PRIMARY'];by={}
  for x in rr:by.setdefault(x['block'],{})[x['role']]=x
  if len(by)!=(6 if stage=='S3' else 4):continue
  for a,b in [('AA_HEAD','ANCHOR_HEAD'),('ANCHOR_TAIL','ANCHOR_HEAD'),('AA_TAIL','ANCHOR_TAIL')]:anchors.append(dict(stage=stage,case=cid,contrast=a+'/'+b,metric=metric,**stat([v[a][metric]/v[b][metric] for k,v in sorted(by.items())])))
write(out/'COMPARISONS.json',comparisons);write(out/'ANCHORS.json',anchors)
counts=collections.Counter((x['stage'],x['task']) for x in expanded);actual=collections.Counter(x['stage'] for x in measured if x['role']=='PRIMARY')
write(out/'COUNTS.json',dict(expanded_labels={str(k):v for k,v in counts.items()},actually_measured_primary=dict(actual),completed_workers=[x['worker'] for x in sources]))
print(json.dumps(dict(measured_phases=len(measured),expanded_primary_labels=len(expanded),comparisons=len(comparisons),actually_measured_primary=dict(actual))))
