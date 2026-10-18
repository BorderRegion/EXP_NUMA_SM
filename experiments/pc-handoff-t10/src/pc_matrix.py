import os,json
from pathlib import Path
_matrix_root=Path(__file__).resolve().parents[1]
os.environ['PC_BUILD']=json.loads((_matrix_root/'freeze/matrix_build.json').read_text())['build']
from measure import *
import sys,random
out=Path(sys.argv[1]);block=int(sys.argv[2]);selection=json.loads((ROOT/'freeze/selection.json').read_text());e=Engine();write(out/'environment.json',dict(membership=e.membership,quad=e.quad,halves=e.halves,init_ms=e.init_ms,roster_ms=e.roster_ms));assert [e.membership[g] for g in e.quad]==json.loads((ROOT/'freeze/quad_resources.json').read_text())['actual_SM_sets']
conditioning(e,out)
for c in selection['representatives']:
 cid=c['case_id'];d=Data(c['M'],c['N'],c['K'],s=c['S'],seed=30000+block*100+int(cid[1:]),ring=1);r=c['recipe'];s=c['S'];bits=qualification(e,d,dict(recipe=r,s=s,kind=0),out,cid)
 order=[(slot,round_,p,q) for slot in range(2) for round_ in range(4) for p in range(4) for q in range(4)];random.Random(613+block+int(cid[1:])).shuffle(order)
 for slot,round_,p,q in order:
  row=phase(out,e,d,dict(phase_id=f'{block}_{cid}_w{slot}_r{round_}_p{p}c{q}',stage='E2_MATRIX',block=block,case=cid,policy='CELL',P_group=p,C_group=q,workspace_slot=slot,round=round_,role='development' if block<2 else 'confirmation'),dict(recipe=r,s=s,kind=2,pg=[e.quad[p],e.quad[p]],cg=[e.quad[q],e.quad[q]],wslot=slot),requests=16,replays=48,warm_ms=0,check_bitwise=bits)
 # Exact placement siblings run outside all formal timers, for every physical group.
 for p in range(4):
  j=Job(e,d,recipe=r,s=s,kind=2,pg=[e.quad[p],e.quad[p]],cg=[e.quad[(p+1)%4],e.quad[(p+1)%4]],diag=1,generation=41+block);check=j.placement();append(out/'placement.jsonl',dict(case=cid,P_group=p,C_group=(p+1)%4,check=check));j.close()
 print('MATRIX_CASE_COMPLETE',block,cid,flush=True);d.close()
e.close();write(out/'complete.json',dict(status='PASS',episodes=768))
