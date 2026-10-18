from measure import *
import sys,random
out=Path(sys.argv[1]);block=int(sys.argv[2]);e=Engine(mode=-2);write(out/'environment.json',dict(membership=e.membership,quad=e.quad,halves=e.halves,init_ms=e.init_ms,roster_ms=e.roster_ms));conditioning(e,out)
cases=[x for x in json.loads((INPUT/'plans/gemm_cases.json').read_text()) if x['split']=='development']
for case in cases:
 cid=case['case_id'];d=Data(case['M'],case['N'],case['K'],seed=20000+100*block+int(cid[1:]),ring=2)
 probe=Job(e,d,kind=3);probe.batch(16);lib_us=probe.batch(16)[0]/16;probe.close();replays=max(16,min(1024,round(100000/lib_us)))
 # Independent baseline anchors and all fixed recipes get the same measurement scope.
 phase(out,e,d,dict(phase_id=f'{block}_{cid}_LIB_begin',stage='E1',block=block,case=cid,policy='LIB',role='begin'),dict(kind=3),requests=16,replays=replays)
 opts=[(r,s) for r in range(4) for s in [1,2,4,8,16] if d.k//s>=32];random.Random(143+block).shuffle(opts)
 for r,s in opts:
  row=phase(out,e,d,dict(phase_id=f'{block}_{cid}_r{r}s{s}',stage='E1',block=block,case=cid,policy='S1' if s==1 else 'CORE',role='development'),dict(recipe=r,s=s,kind=4 if s==1 else 0),requests=16,replays=replays)
  # Separate event instrumentation; never substitute these times for formal chain timings.
  if s>1:
   j=Job(e,d,recipe=r,s=s,kind=0,stages=1);[j.run() for _ in range(4)];a=[j.run() for _ in range(16)];j.close();append(out/'stages.jsonl',dict(phase_id=row['phase_id'],P_us=float(np.mean([x[2] for x in a])),R_us=float(np.mean([x[3] for x in a])),chain_us=float(np.mean([x[0] for x in a])),scope='INSTRUMENTED_NATURAL_P_R'))
 phase(out,e,d,dict(phase_id=f'{block}_{cid}_LIB_end',stage='E1',block=block,case=cid,policy='LIB',role='end'),dict(kind=3),requests=16,replays=replays)
 print('DEVELOP_DONE',block,cid,flush=True);d.close()
e.close();write(out/'complete.json',dict(status='PASS',cases=len(cases)))
