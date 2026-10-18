from measure import *
import sys,random
out=Path(sys.argv[1]);block=int(sys.argv[2]);sel=json.loads((ROOT/'freeze/selection.json').read_text());rule=json.loads((ROOT/'freeze/pc_rule.json').read_text());e=Engine(mode=rule['partition']);groups=e.halves[rule['partition']];assert [e.membership[g] for g in groups]==rule['actual_SM_sets'];write(out/'environment.json',dict(membership=e.membership,groups=groups,init_ms=e.init_ms,roster_ms=e.roster_ms,setup_costs=e.setup_costs));conditioning(e,out)
cases=json.loads((ROOT/'freeze/layer_plan.json').read_text())['gemm']
for c in cases:
 cid=c['case_id'];m,n,k=c['M'],c['N'],c['K'];b=sel['bins'][f'M{0 if m<=8 else 1 if m<=128 else 2}_N{int(n>4096)}'];r=b['mechanism']['recipe'];s=b['mechanism']['S'];d=Data(m,n,k,s=s,seed=60000+block*100+int(cid[1:]),ring=4,chain=True);bits=qualification(e,d,dict(recipe=r,s=s,kind=0),out,cid)
 common=dict(recipe=r,s=s);kw={'LIB':dict(**common,kind=3),'CORE':dict(**common,kind=0),'G':dict(**common,kind=1,slab=1,pg=groups,cg=groups),'M':dict(**common,kind=1,slab=1,pg=groups,cg=groups[::-1] if rule['pi'] else groups)}
 phase(out,e,d,dict(phase_id=f'{block}_{cid}_LIB_begin',stage='E5_GEMM_CHAIN',block=block,case=cid,policy='LIB',role='begin',source=c['source']),kw['LIB'],replays=256)
 order=list(kw);random.Random(112+block).shuffle(order);seen={}
 for label in order:
  key=json.dumps(kw[label],sort_keys=True)
  if key in seen:append(out/'aliases.jsonl',dict(case=cid,policy=label,alias=seen[key],role='main'));continue
  seen[key]=label
  phase(out,e,d,dict(phase_id=f'{block}_{cid}_{label}',stage='E5_GEMM_CHAIN',block=block,case=cid,policy=label,role='main',source=c['source']),kw[label],replays=256,check_bitwise=bits if label!='LIB' else None)
 phase(out,e,d,dict(phase_id=f'{block}_{cid}_LIB_end',stage='E5_GEMM_CHAIN',block=block,case=cid,policy='LIB',role='end',source=c['source']),kw['LIB'],replays=256)
 print('GEMM_CHAIN_COMPLETE',block,cid,flush=True);d.close()
e.close();write(out/'complete.json',dict(status='PASS',cases=len(cases)))
