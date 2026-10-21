from pathlib import Path
import subprocess,json,hashlib,time
root=Path(__file__).resolve().parents[1];raw=root/'results/raw'/json.loads((root/'recovery/run.json').read_text())['run_id'];records=[]
for scene,w,h in [('bonsai',320,180),('train',640,360),('bonsai',1920,1080),('train',1920,1080)]:
 prefix=f'{scene}_{w}x{h}';reference=None
 for label,policy,executor in [('native',None,None),('instrumented',0,0),('identity_I',1,0),('identity_Q',1,1),('joint_I',6,0),('joint_Q',6,1)]:
  out=raw/'executor_checks_r2'/f'{prefix}_{label}';cmd=[str(root/'build/native'/('native_renderer' if policy is None else 'scheduled_renderer')),str(root/'offline_inbox/assets'/scene),str(w),str(h),'0','3',str(out),'8']
  if policy is not None:cmd += [str(policy),str(executor)]
  started=time.monotonic();p=subprocess.run(cmd,capture_output=True,text=True,timeout=120);out.mkdir(parents=True,exist_ok=True);(out/'stdout.txt').write_text(p.stdout);(out/'stderr.txt').write_text(p.stderr)
  r={'scene':scene,'width':w,'height':h,'label':label,'returncode':p.returncode,'wall_seconds':time.monotonic()-started,'argv':cmd};records.append(r)
  if p.returncode:raise RuntimeError(p.stderr)
  hashes={f:hashlib.sha256((out/f).read_bytes()).hexdigest() for f in ['color.raw','final_T.raw','n_contrib.raw']};r['sha256']=hashes
  if reference is None:reference=hashes
  r['raw_bitwise_equal']=hashes==reference
  print(prefix,label,'equal',r['raw_bitwise_equal'],flush=True)
  if not r['raw_bitwise_equal']:raise RuntimeError('Executor qualification mismatch; stop')
  (root/'recovery/EXECUTOR_CHECKS_R2.json').write_text(json.dumps(records,indent=2)+'\n')
