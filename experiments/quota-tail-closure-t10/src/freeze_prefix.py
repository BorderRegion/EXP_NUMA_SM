from common import *
import math
result={}
for cid in ['LONG','RAGGED']:
 cells={}
 for block in [0,1]:
  matches=[f for f in (RUN/'raw').glob(f'S1_block_{block}*') if (f/'COMPLETE.json').exists() and read(f/'manifest.json')['status']=='COMPLETED'];assert len(matches)==1;folder=matches[0];assert read(folder/'COMPLETE.json')['status']=='PASS';ph=read(folder/'PHASES.json');aliases=read(folder/'ALIASES.json')
  for task in ['FG','BG']:
   alias=next(x['aliases'] for x in aliases if x['case']==cid and x['task']==task)
   for label,source in alias.items():cells[block,task,label]=next(x for x in ph if x['case']==cid and x['task']==task and x['role']=='PRIMARY' and x['label']==source)
 result[cid]={}
 for q in [10,20,28,36,46]:
  for fam in ['NEUTRAL','PACK','SPREAD']:
   label=f'{fam}_Q{q}';fg=[cells[b,'FG',label]['job_gpu_us'] for b in [0,1]];bg=[cells[b,'BG',label]['job_gpu_us'] for b in [0,1]]
   ft=math.sqrt(fg[0]*fg[1]);bt=math.sqrt(bg[0]*bg[1]);k=max(1,min(31,math.floor(32*bt/ft+.5)))
   result[cid][label]=dict(k=k,foreground32_gpu_us=ft,background_total_gpu_us=bt,development_fg_values=fg,development_bg_values=bg,metric='Complete isolated GPU service intervals; host output-ready retained separately',formula='clamp(floor(32*Tbg/Tfg32+0.5),1,31)')
assert not (RUN/'freeze/PREFIX.json').exists();write(RUN/'freeze/PREFIX.json',result);print(json.dumps(result,indent=2))
