"""Static research figures; ratios below one mean less time."""
import json,pathlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=pathlib.Path(__file__).resolve().parents[1]
RUN=pathlib.Path((ROOT/'implementation_same_q_v2/CURRENT_RUN.txt').read_text().strip())
def main():
    data=json.loads((RUN/'derived/analyses.json').read_text());out=RUN/'figures';out.mkdir(exist_ok=True)
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'figure.facecolor':'white'})
    def save(fig,name):
        fig.tight_layout();fig.savefig(out/(name+'.png'),dpi=180,bbox_inches='tight');fig.savefig(out/(name+'.pdf'),bbox_inches='tight');plt.close(fig)
    def dots(ax,entries,title):
        for i,(label,d) in enumerate(entries):
            v=d['ratio'];lo,hi=d['interval']
            ax.errorbar(v,i,xerr=[[v-lo],[hi-v]],fmt='o',capsize=3,color='#2563a6')
            ax.annotate(f'{v:.3f}',(hi,i),xytext=(6,0),textcoords='offset points',va='center',fontsize=8)
        labels=[x[0].replace('Q1_MINIMAL','MIN').replace('CACHE_Q1_LEGACY','CACHE q1').replace('FULL_Q1_LEGACY','FULL q1').replace('PER_EXPERT_GRAPH','LIB').replace('GROUPED_MINIMAL','group MIN').replace('GROUPED_CORE','group CORE').replace('_FUSED',' + fused') for x in entries]
        ax.set_yticks(range(len(entries)),labels);ax.invert_yaxis();ax.axvline(1,color='#555',ls='--',lw=1)
        ax.set_xlabel('Candidate / reference time (lower is faster)');ax.set_title(title);ax.grid(axis='x',alpha=.2)
    fig,axes=plt.subplots(1,2,figsize=(13,4.5))
    for ax,cohort in zip(axes,['known_regression','confirmation']):
        entries=list(data[cohort]['STATIC']['device_interval_ms']['aggregate'].items())
        entries=[(k.replace('Q1_MINIMAL','MIN').replace('CACHE_Q1_LEGACY','CACHE q1').replace('FULL_Q1_LEGACY','FULL q1').replace('CORE_ORIGINAL','CORE').replace('CACHE_FIXED_BEST','fixed best').replace('PER_EXPERT_GRAPH','LIB').replace('NATIVE_GROUPED_GRAPH','LIB'),v) for k,v in entries]
        dots(ax,entries,cohort.replace('_',' ')+' (6 process blocks)')
    fig.suptitle('T10 same-q controls: exploratory 95% block intervals',y=1.03);save(fig,'same_q_primary')
    fig,axes=plt.subplots(1,2,figsize=(13,7))
    entries=[]
    for cohort in ['known_regression','confirmation']:
        entries+=data[cohort]['STATIC']['device_interval_ms']['cases']
    for ax,ref in zip(axes,['CACHE_Q1_LEGACY',json.loads((RUN/'BODY_AND_BASELINE_FREEZE_V2.json').read_text())['library']]):
        subset=sorted([(x['case_id'],x) for x in entries if x['comparison']=='Q1_MINIMAL/'+ref],key=lambda x:x[0])
        dots(ax,subset,'MIN / '+('same-q CACHE' if ref=='CACHE_Q1_LEGACY' else 'frozen LIB'))
    fig.suptitle('Every formal operator case, including slow cases',y=1.02);save(fig,'operator_all_cases')
    diag=data['single_problem_diagnostic']['STATIC']['device_interval_ms']['aggregate']
    fig,axes=plt.subplots(1,2,figsize=(13,7))
    dots(axes[0],[(k,v) for k,v in diag.items() if k.endswith('/PER_EXPERT_GRAPH')],'Single-problem paths / LIB (3 blocks)')
    dots(axes[1],[(k,v) for k,v in diag.items() if '/SINGLE_' in k],'Grouped / same-tile ordinary GEMM')
    save(fig,'backbone_decomposition')
    fig,axes=plt.subplots(1,2,figsize=(13,4.5))
    dots(axes[0],list(data['layer_main']['STATIC']['operator_or_layer_ready_ms']['aggregate'].items()),'Full layer: output-ready ratio (6 blocks)')
    if 'layer_fusion' in data:
        dots(axes[1],list(data['layer_fusion']['STATIC']['operator_or_layer_ready_ms']['aggregate'].items()),'Matched activation fusion (3 blocks)')
    else:axes[1].text(.5,.5,'Fusion not qualified',ha='center',transform=axes[1].transAxes)
    save(fig,'layer_and_fusion')
    if 'layer_ring' in data:
        fig,axes=plt.subplots(1,2,figsize=(13,4.5))
        for ax,(mode,vals) in zip(axes,data['layer_ring'].items()):dots(ax,list(vals['operator_or_layer_ready_ms']['aggregate'].items()),('Hot slot 0 + copy' if mode=='HOT_SLOT0_COPY' else '8-slot activation ring')+' (3 blocks)')
        save(fig,'activation_ring')
    print('FIGURES',out)
if __name__=='__main__':main()
