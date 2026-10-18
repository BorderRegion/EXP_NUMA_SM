"""Final address-conditioned iteration; no additional adaptive stage after this."""
from common import *
from worker import run
from v3_lib import *
import random,subprocess,sys,shutil,itertools,time
stage=ROOT/'build_v3';stage.mkdir(exist_ok=False)
s=(ROOT/'src/kernels.cu').read_text().replace('unsigned*base=flags+offsets[p.slot%3]/4;','unsigned*base=flags+p.slot*1024;').replace('if(p.kind==3)base=flags+blockIdx.x*1024;','if(p.kind==3)base=flags+(p.slot+blockIdx.x)*1024;').replace('base=flags+map[sm*2]*1024;','base=flags+(p.slot+map[sm*2])*1024;')
(stage/'kernels_v3.cu').write_text(s);shutil.copy2(ROOT/'src/types.hpp',stage/'types.hpp');shutil.copy2(ROOT/'build/runner',stage/'runner')
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab');from lgjudge import cudabuild as cb
cmd=[str(cb.find_nvcc()),'-O3','-std=c++17','-arch=sm_75',f'-ccbin={cb.find_host_compiler()}',*[f'-I{x}' for x in cb.include_dirs()],'--ptxas-options=-v','--cubin',str(stage/'kernels_v3.cu'),'-o',str(stage/'probe.cubin')]
p=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(stage/'compile.log').write_text(p.stdout+p.stderr)
if p.returncode:raise RuntimeError('Compile failure')
p=subprocess.run(['/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/cuobjdump','--dump-sass',str(stage/'probe.cubin')],capture_output=True,text=True);(stage/'probe.sass.txt').write_text(p.stdout+p.stderr)
write(stage/'build.json',dict(command=cmd,change='Only mailbox position selection: slot is now a4KiB page offset, same address for isolated calibration and concurrent producer-owned mailbox',files={p.name:sha(p) for p in stage.iterdir() if p.is_file()}))
ids=json.loads((RUN/'raw/roster/environment.json').read_text())['roster'];old=json.loads((ROOT/'freeze/PROTOCOL_V2.json').read_text())
protocol=dict(frozen_at=utc(),status='FINAL_STAGE_FROZEN_BEFORE_NEW_DATA',motivation='Stable same-address cycle shape but training slots0/1 versus held-out slot2 payload residual correlation only0.078. Static pair-only cost is incomplete.',matrix_processes=['tensor_dev_0','tensor_dev_1','tensor_confirm_0','tensor_confirm_1'],calibration='For each fixed producer i, use exact deployed mailbox base + (slot_page+i)*4096, test every one of28 consumer SMs. Two randomized repeats. All128 measured +16warm handshakes,64B payload.',slot_pages=[0,17,257],fit='Only tensor_dev_0/1 cycles; per-slot bottleneck assignment with sum tie break, and per-slot min-sum control',policies=['ADDRESS_MAX','ADDRESS_SUM','GLOBAL_CYCLE_MAX','IDENTITY','RANDOM'],new_deployment_processes=6,repeats=12,steps=[128,512],unscored_warm_launches=3,primary_comparisons=['ADDRESS_MAX/GLOBAL_CYCLE_MAX','ADDRESS_MAX/RANDOM'],secondary_comparisons=['ADDRESS_MAX/IDENTITY','ADDRESS_MAX/ADDRESS_SUM'],scope='Same synthetic28-pair communication kernel, not real application. CPU mapping and mapping upload excluded. Every slot and sign retained. Process-level equal weighting.',stop='Final bounded implementation stage; do not choose another method from confirmation outcomes',remaining_cap_seconds=900-sum(json.loads(x)['worker_seconds'] for x in (RUN/'ledger.jsonl').read_text().splitlines()))
write(ROOT/'freeze/PROTOCOL_V3.json',protocol)
for b,key in enumerate(protocol['matrix_processes']):
 rows=[];rng=random.Random(2026101800+b)
 for rnd in range(2):
  sub=[[1,rnd,1,page+i,ids[2*i],ids[2*j+1],128,0,0] for page in [0,17,257] for i in range(28) for j in range(28)];rng.shuffle(sub);rows+=sub
 (ROOT/'plans'/f'{key}.txt').write_text('\n'.join(' '.join(map(str,x)) for x in rows)+'\n')
# Exact-position qualification includes both notification ownership and28-pair concurrency.
qual=[[3,0,1,page,0,0,n,0,0] for page in [0,17,257] for n in [128,512]]
(ROOT/'plans/qualification_v3.txt').write_text('\n'.join(' '.join(map(str,x)) for x in qual)+'\n')
base=[stage/'runner','--cubin',stage/'probe.cubin'];san=REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer'
write(ROOT/'freeze/V3_EXECUTION.json',dict(at=utc(),files={str(p.relative_to(ROOT)):sha(p) for d in ['src','build_v3'] for p in (ROOT/d).iterdir() if p.is_file()}))
for tool in ['memcheck','synccheck']:
 run(f'{tool}_v3',[san,'--tool',tool,'--error-exitcode','97']+base+['--plan',ROOT/'plans/qualification_v3.txt','--maps',ROOT/'plans/qualification_maps.txt','--out','{OUT}'])
for key in protocol['matrix_processes'][:2]:run(key,base+['--plan',ROOT/'plans'/f'{key}.txt','--out','{OUT}'])
ts=[tensor(RUN/'raw'/key)[0]['cycles'] for key in protocol['matrix_processes'][:2]];cost=np.mean(ts,axis=(0,1));maps=[];metadata=[];fitstart=time.monotonic()
for g,page in enumerate([0,17,257]):
 for name in protocol['policies']:
  if name.startswith('ADDRESS'):
   a=bottleneck(cost[g]) if name=='ADDRESS_MAX' else hungarian(cost[g]);pairs=[[ids[2*i],ids[2*j+1]] for i,j in enumerate(a)]
  else:pairs=old['maps']['CYCLE_MAX' if name=='GLOBAL_CYCLE_MAX' else name]
  maps.append(pairs);metadata.append(dict(policy_id=len(maps)-1,name=name,slot_page=page,pairs=pairs,fit_mean=float(np.mean([cost[g,i,ids.index(d)//2] for i,(_,d) in enumerate(pairs)])),fit_max=float(np.max([cost[g,i,ids.index(d)//2] for i,(_,d) in enumerate(pairs)]))))
write(ROOT/'freeze/MAPPING_V3.json',dict(frozen_at=utc(),fit_seconds=time.monotonic()-fitstart,fit_sources=protocol['matrix_processes'][:2],confirmation_seen=False,maps=metadata))
(ROOT/'plans/frozen_maps_v3.txt').write_text(str(len(maps))+'\n'+'\n'.join(f'{a} {b}' for ps in maps for a,b in ps)+'\n')
for b in range(6):
 rows=[];rng=random.Random(2026101820+b);conditions=[(n,g) for n in [128,512] for g in range(3)];rng.shuffle(conditions)
 for n,g in conditions:
  policies=list(range(5));rng.shuffle(policies)
  for p in policies:
   for j in range(3):rows.append([3,-1,1,[0,17,257][g],0,0,n,0,g*5+p])
  for rnd in range(12):
   policies=list(range(5));rng.shuffle(policies)
   for p in policies:rows.append([3,rnd,1,[0,17,257][g],0,0,n,0,g*5+p])
 (ROOT/'plans'/f'deploy_v3_{b}.txt').write_text('\n'.join(' '.join(map(str,x)) for x in rows)+'\n')
write(ROOT/'freeze/V3_PLAN_HASHES.json',{p.name:sha(p) for p in (ROOT/'plans').iterdir() if 'v3' in p.name or p.name.startswith('tensor_')})
for key in protocol['matrix_processes'][2:]:run(key,base+['--plan',ROOT/'plans'/f'{key}.txt','--out','{OUT}'])
for b in range(6):run(f'deploy_v3_{b}',base+['--plan',ROOT/'plans'/f'deploy_v3_{b}.txt','--maps',ROOT/'plans/frozen_maps_v3.txt','--out','{OUT}'])
write(ROOT/'GPU_EXECUTION_COMPLETE_V3.json',dict(at=utc(),status='COMPLETE',worker_seconds=sum(json.loads(x)['worker_seconds'] for x in (RUN/'ledger.jsonl').read_text().splitlines())))
