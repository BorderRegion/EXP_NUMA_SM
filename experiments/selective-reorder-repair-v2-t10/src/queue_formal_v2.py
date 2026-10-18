from worker import *
# Scope is frozen using elapsed implementation cost only, before V/G timings.
rows=lines(runroot()/'ledger.jsonl');cal=[x for x in rows if x['key'].startswith('S2_pairs_')];assert len(cal)==3
cases=read(INPUT/'plans/cases.json');full=[c['id'] for c in cases if c['split'] in ['new_confirmation','regression']]
observed=[r for x in cal for r in lines(Path(x['out'])/'pairs.jsonl')];mean_quartet_s=sum(sum(w['warm_cpu_us']+w['window_host_us'] for w in r['windows'])/1e6 for r in observed)/len(observed)
projection=sum(x['worker_s'] for x in cal)*2+144*mean_quartet_s;remaining=read(ROOT/'BEGIN_EXECUTION.json')['effective_new_gpu_cap_s']-sum(x['worker_s'] for x in rows)
reduced=projection>70*60 or projection+55*60>remaining or elapsed()+projection>355*60
keep=['V01','V03','V05','V07','V09','V11','V13','V15','R_G002','R_G008','R_G017','R_G039'] if reduced else full
assert all(x in full for x in keep)
write(ROOT/'freeze/formal_scope.json',dict(case_ids=keep,reduced=reduced,projected_full_worker_s=projection,projection_method='Twice the three observed development worker costs plus 144 direct quartets at development mean; conservative 5min stage margin. No candidate win/loss used.',remaining_gpu_s=remaining,elapsed_wall_s=elapsed(),direct_cases=['V01','V06','V11','V16'],untimed_action_tables=[x for x in full if x not in keep],main_pairs_expected=len(keep)*8*2*6,direct_quartets_expected=144,AA_expected=len(set(keep+['V01','V06','V11','V16']))*2*6,created_at=utc()))
for b in range(6):run(f'S4_pairs_{b}',[PYTHON,ROOT/'src/pair_suite.py','{OUT}','EVALUATION',str(b)])
