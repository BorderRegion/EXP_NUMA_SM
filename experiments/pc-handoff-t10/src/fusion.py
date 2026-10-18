from measure import *
import sys,random
out=Path(sys.argv[1]);block=int(sys.argv[2]);sel=json.loads((ROOT/'freeze/selection.json').read_text());rule=json.loads((ROOT/'freeze/pc_rule.json').read_text());e=Engine(mode=rule['partition']);groups=e.halves[rule['partition']];assert [e.membership[g] for g in groups]==rule['actual_SM_sets'];conditioning(e,out)
for c in sel['representatives']:
 cid=c['case_id'];r=c['recipe'];s=c['S'];d=Data(c['M'],c['N'],c['K'],s=s,ring=2,seed=90000+100*block+int(cid[1:]));bits=qualification(e,d,dict(recipe=r,s=s,kind=0),out,cid)
 configs=[(f,label,pi) for f in [0,1] for label,pi in [('G',0),('M',rule['pi'])]];configs.sort(key=lambda x:x[0],reverse=bool(block%2));seen={}
 for f,label,pi in configs:
  if (f,pi) in seen:append(out/'aliases.jsonl',dict(case=cid,policy=f'F{f}_{label}',alias=seen[f,pi]));continue
  seen[f,pi]=f'F{f}_{label}'
  phase(out,e,d,dict(phase_id=f'{block}_{cid}_F{f}_{label}',stage='E5_DEPENDENCY_INTERACTION',block=block,case=cid,policy=f'F{f}_{label}',f1=f,pi=pi),dict(recipe=r,s=s,kind=1,slab=1,pg=groups,cg=groups[::-1] if pi else groups,f1=f),requests=64,replays=max(16,min(1024,round(100000/c['lib_us']))),check_bitwise=bits)
 # Layout x position four cells, all at the same global producer-ready boundary.
 seen={}
 for slab,label,pi in [(slab,label,pi) for slab in ([1,0] if block%2 else [0,1]) for label,pi in [('NEUTRAL',0),('LEARNED',rule['pi'])]]:
  if (slab,pi) in seen:append(out/'aliases.jsonl',dict(case=cid,policy=f'LAYOUT{slab}_{label}',alias=seen[slab,pi]));continue
  seen[slab,pi]=f'LAYOUT{slab}_{label}'
  phase(out,e,d,dict(phase_id=f'{block}_{cid}_LAYOUT{slab}_{label}',stage='E5_LAYOUT_INTERACTION',block=block,case=cid,policy=f'LAYOUT{slab}_{label}',slab=slab,pi=pi),dict(recipe=r,s=s,kind=1,slab=slab,pg=groups,cg=groups[::-1] if pi else groups),requests=64,replays=max(16,min(1024,round(100000/c['lib_us']))),check_bitwise=bits)
 print('ABLATION_DONE',block,cid,flush=True);d.close()
e.close();write(out/'complete.json',dict(status='PASS'))
