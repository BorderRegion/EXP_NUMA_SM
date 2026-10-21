from pathlib import Path
import subprocess,json,datetime,time,sys
root=Path(__file__).resolve().parents[1];meta=json.loads((root/'recovery/run.json').read_text());raw=root/'results/raw'/meta['run_id'];name,kind,*cmd=sys.argv[1:]
if kind.startswith('GPU') and (root/'recovery/GPU_STOP.json').exists():
    raise SystemExit('GPU testing is stopped; incident decision required before resumption.')
start=time.monotonic();ts=datetime.datetime.now(datetime.timezone.utc).isoformat()
p=subprocess.run(cmd,capture_output=True,text=True,timeout=1200)
for stream,data in [('stdout',p.stdout),('stderr',p.stderr)]:
    with (raw/(name+'.'+stream+'.txt')).open('x') as f:f.write(data)
record={'name':name,'kind':kind,'argv':cmd,'started_at_utc':ts,'wall_seconds':time.monotonic()-start,'returncode':p.returncode}
with (root/'recovery/commands.jsonl').open('a') as f:f.write(json.dumps(record)+'\n')
print(json.dumps(record));print(p.stdout);print(p.stderr,file=sys.stderr);sys.exit(p.returncode)
