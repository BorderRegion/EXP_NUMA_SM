from measure import *
import sys
out=Path(sys.argv[1]);sel=json.loads((ROOT/'freeze/selection.json').read_text());e=Engine(mode=-2);conditioning(e,out)
for c in sel['cards'][:12]:
 cid=c['case_id'];d=Data(c['M'],c['N'],c['K'],s=c['S'],ring=1,seed=81000+int(cid[1:]));r=c['recipe'];s=c['S'];chain=Job(e,d,recipe=r,s=s,kind=0,stages=1);chain.run();d.numerical(0);partial=d.w[:c['M']*c['N']*s].cpu();answer=d.d.cpu();chain.close()
 for name,kind in [('P_ONLY',6),('P_TO_R',0),('R_ONLY_REUSE',7)]:
  j=Job(e,d,recipe=r,s=s,kind=kind,stages=0);j.batch(32);a=[j.run() for _ in range(32)];bat=j.batch(32)
  if kind==6:assert np.array_equal(partial.numpy().view('uint32'),d.w[:partial.numel()].cpu().numpy().view('uint32'))
  else:d.numerical(0)
  append(out/'scopes.jsonl',dict(case=cid,scope=name,recipe=r,S=s,chain_us=float(np.mean([x[0] for x in a])),batch_per_replay_us=bat[0]/32,complete_partial_or_output_check='PASS',interpretation='Independent scope changes cache; do not subtract spans to infer pure interconnect latency'));j.close()
 print('SCOPE_DONE',cid,flush=True);d.close()
e.close();write(out/'complete.json',dict(status='PASS',development_cases=12,scopes=36))
