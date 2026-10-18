from measure import *
import sys,random
out=Path(sys.argv[1]);block=int(sys.argv[2]);sel=json.loads((ROOT/'freeze/selection.json').read_text());rule=json.loads((ROOT/'freeze/pc_rule.json').read_text());e=Engine(mode=rule['partition']);groups=e.halves[rule['partition']];conditioning(e,out)
# One representative per baseline reducer-fraction tier; these are not selected by candidate effect.
for c in sel['representatives'][::2]:
 cid=c['case_id'];r=c['recipe'];d=Data(c['M'],c['N'],c['K'],s=8,ring=2,seed=95000+block*100+int(cid[1:]))
 bitsets={s:qualification(e,d,dict(recipe=r,s=s,kind=0),out,cid+f'_S{s}') for s in [2,8]}
 configs=[(s,pi) for s in [2,8] for pi in [rule['pi'],1-rule['pi']]];order=[[0,1,3,2],[1,2,0,3],[2,3,1,0],[3,0,2,1]][block%4]
 for idx in order:
  s,pi=configs[idx]
  phase(out,e,d,dict(phase_id=f'{block}_{cid}_S{s}_pi{pi}',stage='E5_SPLIT_WORKSPACE',block=block,case=cid,policy='M' if pi==rule['pi'] else 'P',interpretation='S2 vs S8 jointly changes split decomposition and workspace; only within-S M/P isolates consumer placement.'),dict(recipe=r,s=s,kind=1,slab=1,pg=groups,cg=groups[::-1] if pi else groups),replays=max(16,min(1024,round(100000/c['lib_us']))),check_bitwise=bitsets[s])

 d.close()
e.close();write(out/'complete.json',dict(status='PASS',cases=3))
