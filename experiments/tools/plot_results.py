import json,csv,collections,statistics,math,pathlib,textwrap
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=pathlib.Path(__file__).resolve().parents[1];D=ROOT/'derived/t10';P=ROOT/'reports/figures';P.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.dpi':150,'savefig.bbox':'tight'})
colors=['#22577A','#38A3A5','#D97732','#674EA7','#829399','#CC6677','#4477AA']
def save(fig,name):
 fig.savefig(P/(name+'.png'));fig.savefig(P/(name+'.svg'));plt.close(fig)
def table(name,title,headers,rows,width=11):
 rows=[[textwrap.fill(str(s),34)for s in row]for row in rows]
 heights=[.48]+[.24*max(s.count('\n')+1 for s in row)+.22 for row in rows]
 fig,ax=plt.subplots(figsize=(width,sum(heights)+1.0));ax.axis('off');ax.set_title(title,loc='left',weight='bold',pad=20);t=ax.table(cellText=rows,colLabels=headers,loc='center',cellLoc='left');t.auto_set_font_size(False);t.set_fontsize(9.5)
 for (r,c),cell in t.get_celld().items():cell.set_height(heights[r]/sum(heights))
 for (r,c),cell in t.get_celld().items():cell.set_edgecolor('white');cell.set_facecolor('#EAF1F5'if r%2 else'#F6F8FA');
 for c in range(len(headers)):t[(0,c)].set_facecolor('#22577A');t[(0,c)].set_text_props(color='white',weight='bold')
 save(fig,name)
def main():
 topology=json.load(open(D/'topology.json'));fig,ax=plt.subplots(figsize=(11,3.5));labels=[];arr=[]
 for x in topology[:5]:
  row=np.full(56,-1);labels.append('Native'if x['mode']=='native'else'G'+str(x['layout']))
  for g,ss in x['sm_sets'].items():row[ss]=int(g)
  arr.append(row)
 ax.imshow(arr,aspect='auto',cmap=matplotlib.colors.ListedColormap(colors[:2]),vmin=0,vmax=1,interpolation='nearest');ax.set_yticks(range(5),labels);ax.set_xlabel('Observed logical SM ID (not a physical GPC label)');ax.set_title('1. Public resource sets: 56 SMs retained in every layout',loc='left',weight='bold');ax.set_xticks(range(0,56,4));save(fig,'01_resource_map')
 table('02_capabilities','2. Measured capability and unavailable branches',['Item','T10 result','Evidence / limit'],[['Compute capability','7.5; 56 SM; 4 MiB L2','CUDA device query'],['Hardware block cluster','UNSUPPORTED','cluster_launch = 0; no simulation'],['Green full / split','56 / 28+28 / 18+38','All assigned SMs observed'],['G3 alternate split flag','Same observed sets as G1','Not an independent placement choice'],['SM-to-GPC map / NUMA','UNKNOWN / NOT STUDIED','No inference from SM ID ordering']])
 cap=list(csv.DictReader(open(D/'capacity.csv')));fig,axs=plt.subplots(1,3,figsize=(12,4),sharey=True)
 for size,ax in enumerate(axs):
  for j,mode in enumerate(['isolated','concurrent']):
   vals=[];err=[]
   for fam in range(4):
    ratios=[]
    for block in range(3):
     rr=[r for r in cap if int(r['size'])==size and int(r['family'])==fam and r['mode']==mode and int(r['process_block'])==block];rr.sort(key=lambda r:int(r['group']));ratios.append((float(rr[1]['tasks_per_ms'])/int(rr[1]['sms']))/(float(rr[0]['tasks_per_ms'])/int(rr[0]['sms'])))
    vals.append(statistics.mean(ratios));err.append(statistics.stdev(ratios))
   ax.bar(np.arange(4)+(j-.5)*.32,vals,.3,yerr=err,label=mode,color=colors[j],capsize=3)
  ax.axhline(1,color='#555',linestyle='--',linewidth=1);ax.set_xticks(range(4),['K0','K1','K2','K3']);ax.set_title(['small / G1 28+28','nominal / G2 18+38','large / G3 28+28'][size]);ax.set_ylim(0,1.5)
 axs[0].set_ylabel('Group 1 / group 0 capacity per SM');axs[-1].legend();fig.suptitle('3. Type and concurrency effects (three process runs; bars show SD)',weight='bold');fig.tight_layout();save(fig,'03_capacity')
 mech=list(csv.DictReader(open(D/'mechanism_sessions.csv')));lookup={(r['distribution'],r['load'],r['block_id'],r['policy']):float(r['mean_ms'])for r in mech};pol=['I','S','L','R','M','P'];fig,axs=plt.subplots(2,3,figsize=(12,7),sharey=True)
 for dist in range(3):
  for load in range(2):
   ax=axs[load,dist];vals=[]
   for p in pol:vals.append(math.exp(statistics.mean(math.log(lookup[str(dist),str(load),str(b),p]/lookup[str(dist),str(load),str(b),'N'])for b in range(6))))
   ax.bar(pol,vals,color=colors[:6]);ax.axhline(1,color='#555',linestyle='--');ax.set_title(f'distribution {dist}, load {load}');ax.set_ylim(0,max(1.5,max(vals)*1.1));ax.set_ylabel('Time / Native (lower is better)')
 fig.suptitle('4. All seven mechanism policies; Native remains the deployment reference',weight='bold');fig.tight_layout();save(fig,'04_mechanism_baselines')
 model=list(csv.DictReader(open(D/'prediction_error.csv')));fig,axs=plt.subplots(1,3,figsize=(14,4.4))
 for i,policy in enumerate(['R','M']):
  rr=[r for r in model if r['policy']==policy];x=[float(r['predicted_ms'])for r in rr];y=[float(r['actual_ms'])for r in rr];axs[0].scatter(x,y,s=14,alpha=.6,label=policy,color=colors[i]);axs[1].hist([100*float(r['relative_error'])for r in rr],bins=18,alpha=.55,label=policy,color=colors[i])
 lim=max(max(float(r['actual_ms']),float(r['predicted_ms']))for r in model);axs[0].plot([0,lim],[0,lim],'--',color='#555');axs[0].set(xlabel='Calibrated model prediction (ms)',ylabel='Measured group event interval (ms)');axs[1].set(xlabel='Prediction error / measured time (%)',ylabel='Group records');axs[0].legend();axs[1].legend()
 ratios=[]
 for fam in range(4):
  group=[]
  for size in range(3):
   for g in range(2):
    iso=statistics.mean(float(r['tasks_per_ms'])for r in cap if int(r['family'])==fam and int(r['size'])==size and int(r['group'])==g and r['mode']=='isolated')
    con=statistics.mean(float(r['tasks_per_ms'])for r in cap if int(r['family'])==fam and int(r['size'])==size and int(r['group'])==g and r['mode']=='concurrent');group.append(con/iso)
  ratios.append(group)
 axs[2].boxplot(ratios,tick_labels=['K0','K1','K2','K3']);axs[2].axhline(1,color='#555',linestyle='--');axs[2].set(xlabel='Six size/group conditions per family',ylabel='Concurrent / isolated capacity')
 fig.suptitle('5. Model transfer and concurrency effects',weight='bold');fig.tight_layout();save(fig,'05_model_error')
 stats=json.load(open(D/'application_statistics.json'));fig,axs=plt.subplots(1,2,figsize=(11,4.5),sharey=True);names=['W1/bonsai','W1/train','W2/ca-GrQc','W2/web-Google']
 for j,ref in enumerate(['N','R']):
  points=[stats[n+'_M/'+ref]['ratio']for n in names];ci=[stats[n+'_M/'+ref]['ratio_ci95']for n in names];axs[j].errorbar(points,range(4),xerr=np.array([[p-c[0]for p,c in zip(points,ci)],[c[1]-p for p,c in zip(points,ci)]]),fmt='o',color=colors[j],capsize=4);axs[j].axvline(1,color='#555',linestyle='--');axs[j].set_yticks(range(4),names);axs[j].invert_yaxis();axs[j].set_title('M / '+('Native (W2 = cuSPARSE)'if ref=='N'else'single-rate R'));axs[j].set_xlabel('Time ratio; 95% descriptive block-bootstrap CI')
 fig.suptitle('6. Full application/operator costs: six blocks per input-sequence cell',weight='bold');fig.tight_layout();save(fig,'06_application_results')
 table('07_cost_contract','7. Online planning is zero; execution costs remain',['Cost / action','Steady state','Accounting'],[['CPU planner / plan transfers','0 calls / 0 bytes','All 73,728 measured frame rows'],['Table indexing / group launches','Nonzero','Included in CPU-ready time'],['Context switching / join','Nonzero','Included in CPU-ready time'],['Output screen / diagnostics','Common, outside primary timer','2 KiB GPU digest; selected full readbacks'],['Initial calibration / build / map','One-time; available records retained','First map wall time not instrumented'],['Amortization against Native','No demonstrated deployable payback','Do not invent a precise break-even N']])
 table('08_platform_scope','8. Independent platform scope; no cross-device pooling',['Evidence','T10 (this run)','RTX 5070 Ti'],[['Actual resource query','Measured, one device','NOT RUN HERE'],['Native / Green / four kernel types','Executed','Await independent result package'],['Cluster / DSM','NA: unsupported','Requires actual capability qualification'],['Full rendering / CSR operator','720p + two real graph inputs','NOT RUN HERE'],['Comparison normalization','Within-device M/N and M/R','Never infer floorsweeping from raw cross-GPU ms']])
 table('09_claim_evidence','9. Claim-to-evidence map',['Claim','Evidence available','Boundary'],[['Public partition control','Observed complete 56-SM union','No arbitrary SM subset control'],['Type-sensitive effective capacity','Four families, isolated and concurrent','Short kernels include submission effects'],['Static mapping actually deployed','Full task maps; exactly-once qualification','No physical GPC causality claim'],['Independent M advantage over R','Paired E3 and E4 contrasts','No general benefit demonstrated'],['Real deployment advantage','Native visible, full CPU-ready costs','Do not promote mechanism-only gains'],['Cross-architecture / SKU inference','One T10 instance','Second platform and more devices missing']])
 print('Nine PNG/SVG figures saved',P)
if __name__=='__main__':main()
