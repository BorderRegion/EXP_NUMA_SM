from measure import *
assert (ROOT/'freeze/production_implementation.json').exists(), 'Production qualification must precede bridge/formal measurements'
import sys,random
out=Path(sys.argv[1]);block=int(sys.argv[2]);mode=sys.argv[3] if len(sys.argv)>3 else 'reduced'
sel=json.loads((ROOT/'freeze/selection.json').read_text());rule=json.loads((ROOT/'freeze/pc_rule.json').read_text());e=Engine(mode=rule['partition']);groups=e.halves[rule['partition']];assert [e.membership[g] for g in groups]==rule['actual_SM_sets'];write(out/'environment.json',dict(membership=e.membership,groups=groups,init_ms=e.init_ms,roster_ms=e.roster_ms,setup_costs=e.setup_costs));conditioning(e,out)
reduced=json.loads((INPUT/'plans/reduced_confirmation.json').read_text())['gemm'];cases=[x for x in json.loads((INPUT/'plans/gemm_cases.json').read_text()) if x['split']=='test' and (mode=='full' or x['case_id'] in reduced)]
def binid(c):return f"M{0 if c['M']<=8 else 1 if c['M']<=128 else 2}_N{int(c['N']>4096)}"
base_order=[0,1,7,2,6,3,5,4];policies=['LIB','CORE','I','L','C','M','P','G'];order=[policies[(x+block)%8] for x in base_order]
for c in cases:
 cid=c['case_id'];b=sel['bins'][binid(c)];r=b['mechanism']['recipe'];s=b['mechanism']['S'];d=Data(c['M'],c['N'],c['K'],s=s,seed=50000+block*100+int(cid[1:]),ring=4);bits=qualification(e,d,dict(recipe=r,s=s,kind=0),out,cid)
 count_path=ROOT/'freeze/replays.json';counts=json.loads(count_path.read_text()) if count_path.exists() else {}
 if cid not in counts:
  assert block==0;j=Job(e,d,kind=3);j.batch(16);t=j.batch(32)[0]/32;j.close();counts[cid]=dict(replays=max(16,min(1024,round(100000/t))),baseline_probe_us=t,basis='LIB only, frozen in first formal process before candidates');write(count_path,counts)
 replays=counts[cid]['replays'];kw={
 'LIB':dict(recipe=r,s=s,kind=3),
 'CORE':dict(recipe=r,s=s,kind=0),
 'I':dict(recipe=r,s=s,kind=1,slab=0,pg=groups,cg=groups),
 'L':dict(recipe=r,s=s,kind=1,slab=1,pg=groups,cg=groups),
 'C':dict(recipe=r,s=s,kind=1,slab=0,pg=groups,cg=groups[::-1] if rule['pi'] else groups),
 'M':dict(recipe=r,s=s,kind=1,slab=1,pg=groups,cg=groups[::-1] if rule['pi'] else groups),
 'P':dict(recipe=r,s=s,kind=1,slab=1,pg=groups,cg=groups if rule['pi'] else groups[::-1]),
 'G':dict(recipe=r,s=s,kind=1,slab=1,pg=groups,cg=groups)}
 phase(out,e,d,dict(phase_id=f'{block}_{cid}_LIB_begin',stage='E3',block=block,case=cid,policy='LIB',role='begin',forced_split=b['forced_split']),kw['LIB'],replays=replays)
 use=set(policies) if mode=='full' else {'CORE','M','P','G'};seen={}
 for label in order:
  if label not in use:continue
  key=json.dumps(kw[label],sort_keys=True)
  if key in seen:append(out/'aliases.jsonl',dict(case=cid,policy=label,alias=seen[key],role='main',reason='Identical source parameters, resource sets, layout and DAG'));continue
  seen[key]=label
  phase(out,e,d,dict(phase_id=f'{block}_{cid}_{label}',stage='E3',block=block,case=cid,policy=label,role='main',forced_split=b['forced_split'],production_recipe=b['production']['recipe'],production_S=b['production']['S']),kw[label],replays=replays,check_bitwise=bits if label!='LIB' else None)
  if kw[label]['kind']==1:
   j=Job(e,d,**kw[label],diag=1,generation=61+block);append(out/'placement.jsonl',dict(case=cid,policy=label,check=j.placement()));j.close()
 phase(out,e,d,dict(phase_id=f'{block}_{cid}_LIB_end',stage='E3',block=block,case=cid,policy='LIB',role='end',forced_split=b['forced_split']),kw['LIB'],replays=replays)
 print('FORMAL_CASE_COMPLETE',block,cid,flush=True);d.close()
e.close();write(out/'complete.json',dict(status='PASS',mode=mode,cases=len(cases),block=block))
