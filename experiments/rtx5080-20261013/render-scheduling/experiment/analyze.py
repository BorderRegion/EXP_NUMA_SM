"""Rebuild statistics and figures from immutable measured CSV files."""
from common import ROOT, RAW, save
import csv, math, random, statistics
from collections import defaultdict

OUT=ROOT/'results/derived'/RAW.name
OUT.mkdir(exist_ok=True)
NAMES={0:'B0 Native',1:'B1 Blind queue',2:'B2 Morton',3:'B3 Load',4:'B4 Resource',5:'B5 Group + balance',6:'M Joint',7:'C1 Shuffled',8:'C2 No cap'}
def rows(path):
    with path.open() as f:return list(csv.DictReader(f))
def quantile(x,q):
    x=sorted(x);p=(len(x)-1)*q;lo=int(p);return x[lo]+(x[min(lo+1,len(x)-1)]-x[lo])*(p-lo)
def csvwrite(path,data):
    if not data:return
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)

sessions=[]
for path in sorted(RAW.glob('*/frames.csv')):
    rs=rows(path)
    if not rs:continue
    groups=defaultdict(list)
    for r in rs:groups[(int(r['policy']),int(r['q']),int(r['k']),float(r['alpha']))].append(r)
    label=path.parent.name
    run=__import__('json').loads((path.parent/'run.json').read_text())
    argv=run['argv'];scene=argv[1].split('/')[-1];track=argv[4]
    for (p,q,k,a),rr in groups.items():
        v=[float(r['cpu_result_ready_ms']) for r in rr]
        rec={'run':label,'phase':run['phase'],'scene':scene,'track':track,'policy':p,'name':NAMES[p],'q':q,'k':k,'alpha':a,'frames':len(rr),'mean_cpu_ms':statistics.fmean(v),'p50_cpu_ms':quantile(v,.5),'p95_cpu_ms':quantile(v,.95),'p99_cpu_ms':quantile(v,.99)}
        for col in ['gpu_span_ms','preprocess_ms','scan_ms','sort_ms','build_ms','render_ms','cpu_plan_ms','bundles','cap_hits','instances']:
            rec['mean_'+col]=statistics.fmean(float(r[col]) for r in rr)
        rec['max_render_ms']=max(float(r['render_ms']) for r in rr)
        rec['max_preprocess_ms']=max(float(r['preprocess_ms']) for r in rr)
        sessions.append(rec)
csvwrite(OUT/'sessions.csv',sessions)
j=__import__('json').loads((ROOT/'experiment/POLICY_FREEZE.json').read_text())
formal=[s for s in sessions if s['phase']=='formal']
comparisons=[];aggregate=[]
for base in [0,j['B_star']]:
    strata=defaultdict(list)
    for run in sorted({s['run'] for s in formal}):
        ss={s['policy']:s for s in formal if s['run']==run}
        m,b=ss[6],ss[base];ratio=m['mean_cpu_ms']/b['mean_cpu_ms']
        strata[(m['scene'],m['track'])].append(math.log(ratio))
        comparisons.append({'run':run,'scene':m['scene'],'track':m['track'],'baseline':NAMES[base],'M_ms':m['mean_cpu_ms'],'baseline_ms':b['mean_cpu_ms'],'M_over_baseline':ratio,'time_reduction_percent':100*(1-ratio),'throughput_gain_percent':100*(1/ratio-1)})
    rng=random.Random(50802026+base);boot=[]
    for _ in range(20000):
        means=[statistics.fmean(rng.choice(v) for _ in v) for v in strata.values()]
        boot.append(math.exp(statistics.fmean(means)))
    ratio=math.exp(statistics.fmean(statistics.fmean(v) for v in strata.values()))
    aggregate.append({'baseline_id':base,'baseline':NAMES[base],'M_over_baseline':ratio,'ratio_ci95':[quantile(boot,.025),quantile(boot,.975)],'time_reduction_percent':100*(1-ratio),'time_reduction_ci95':[100*(1-quantile(boot,.975)),100*(1-quantile(boot,.025))],'throughput_gain_percent':100*(1/ratio-1),'strata':len(strata),'process_blocks':sum(len(v) for v in strata.values()),'bootstrap_draws':20000,'unit':'Complete paired process block; within scene/track strata. Frames are not independent replicates.'})
csvwrite(OUT/'paired_comparisons.csv',comparisons)
quality=[]
for p in sorted(RAW.glob('qualification_*/quality.csv')):
    rr=rows(p);quality.append({'run':p.parent.name,'rows':len(rr),'raw_mismatches':sum(int(r['raw_mismatches']) for r in rr),'nonfinite':sum(int(r['nonfinite']) for r in rr),'reference_frames':len(set(r['frame'] for r in rr))})
hashes=[__import__('json').loads(p.read_text()) for p in RAW.glob('formal_*/HASH_COMPARISON.json')]
commands=[__import__('json').loads(s) for s in (RAW/'commands.jsonl').read_text().splitlines()]
summary={'aggregate':aggregate,'formal_sessions':len(formal),'formal_frames':sum(s['frames'] for s in formal),'formal_process_blocks':len(set(s['run'] for s in formal)),'formal_hash_rows':sum(r['rows_checked'] for r in hashes),'formal_hash_mismatches':sum(r['mismatches'] for r in hashes),'qualification':quality,'new_xid_events':[e for c in commands for e in c.get('new_xid_events',[])],'process_worker_seconds':sum(c['worker_seconds'] for c in commands),'max_measured_render_ms':max(s['max_render_ms'] for s in sessions),'max_measured_preprocess_ms':max(s['max_preprocess_ms'] for s in sessions),'finite_contract':'Every formal frame checked; qualification additionally compares every raw output word. Native repeat checks executed twice after each reference.','limitations':['Three blocks per stratum in negative branch yield exploratory intervals.','Bootstrap measures process-repeat variation on this captured-camera sample, not generalization to other renderers or GPUs.','No hardware L2/DRAM counters or validated footprint model.']}
save(OUT/'SUMMARY.json',summary)

# Scientific plots use Matplotlib. Run with the workspace plotting environment.
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams.update({'figure.dpi':140,'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,ax=plt.subplots(figsize=(9,4.5))
groups=sorted({(s['scene'],s['track']) for s in formal});policies=sorted({s['policy'] for s in formal})
colors={0:'#4C6278',j['B_star']:'#27918E',6:'#D87935'}
for offset,p in enumerate(policies):
    vv=[[s['mean_cpu_ms'] for s in formal if (s['scene'],s['track'])==g and s['policy']==p] for g in groups]
    x=[i+(offset-(len(policies)-1)/2)*.24 for i in range(len(groups))]
    ax.bar(x,[statistics.fmean(v) for v in vv],width=.23,label=NAMES[p],color=colors.get(p),alpha=.8)
    for at,v in zip(x,vv):ax.scatter([at]*len(v),v,color='#24323B',s=14,zorder=4)
ax.set_xticks(range(len(groups)),[f'{a}\n{b}' for a,b in groups]);ax.set_ylabel('CPU result-ready time (ms)');ax.set_title('1080p confirmation: full pipeline, including CPU planning');ax.legend(frameon=False);ax.grid(axis='y',alpha=.15);fig.tight_layout();fig.savefig(OUT/'formal_cpu.png');fig.savefig(OUT/'formal_cpu.svg');plt.close(fig)
fig,ax=plt.subplots(figsize=(9,4.5))
cal=[s for s in sessions if s['phase']=='calibration' and [s['policy'],s['q'],s['k'],s['alpha']]==j['settings'][str(s['policy'])]]
pp=sorted({s['policy'] for s in cal});bottom=[0.]*len(pp)
for field,label,color in [('mean_preprocess_ms','Preprocess','#8494A4'),('mean_scan_ms','Scan / host wait','#ADB8C3'),('mean_sort_ms','Binning / sort','#4C6278'),('mean_build_ms','Feature / CPU plan / upload','#D87935'),('mean_render_ms','Render','#27918E')]:
    values=[statistics.fmean(s[field] for s in cal if s['policy']==p) for p in pp];ax.bar(range(len(pp)),values,bottom=bottom,label=label,color=color);bottom=[a+b for a,b in zip(bottom,values)]
ax.set_xticks(range(len(pp)),[NAMES[p].replace(' ','\n',1) for p in pp]);ax.set_ylabel('Mean CUDA event interval (ms)');ax.set_title('Selected configurations on calibration cameras');ax.legend(frameon=False,fontsize=8);fig.tight_layout();fig.savefig(OUT/'calibration_stages.png');fig.savefig(OUT/'calibration_stages.svg');plt.close(fig)
micro=[]
for p in RAW.glob('micro_*/gather.csv'):micro.extend(rows(p))
fig,axes=plt.subplots(1,2,figsize=(9,3.5),sharey=True)
for skew,ax in enumerate(axes):
    for policy,label in enumerate(['Identity','Reverse','Load order','Shuffled']):
        xs=sorted(set(int(r['working_set_bytes']) for r in micro));ys=[statistics.fmean(float(r['gpu_ms']) for r in micro if int(r['skew'])==skew and int(r['schedule'])==policy and int(r['working_set_bytes'])==x) for x in xs];ax.plot([x/67108864 for x in xs],ys,'o-',label=label)
    ax.set_title('Skewed work' if skew else 'Uniform work');ax.set_xlabel('Allocated working set / L2');ax.grid(alpha=.15)
axes[0].set_ylabel('Gather kernel milliseconds');axes[1].legend(frameon=False,fontsize=8);fig.suptitle('Synthetic gather: average over reuse levels and repeats');fig.tight_layout();fig.savefig(OUT/'micro_gather.png');fig.savefig(OUT/'micro_gather.svg');plt.close(fig)
print(__import__('json').dumps(summary,indent=2))
