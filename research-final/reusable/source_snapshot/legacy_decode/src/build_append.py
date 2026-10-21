from common import *
import sys,subprocess,time
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab')
from lgjudge import cudabuild as cb
out=ROOT/'build/append';out.mkdir(exist_ok=True);cmd=read(ROOT/'build/build.json')['command'];cmd=[str(ROOT/'src/append_attention.cu') if x==str(ROOT/'src/attention.cu') else str(out/'attention.so') if x==str(ROOT/'build/attention.so') else x for x in cmd];t=time.monotonic();p=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(out/'compile.log').write_text(p.stdout+p.stderr)
if p.returncode:print(p.stderr[-8000:]);raise SystemExit(p.returncode)
p=subprocess.run(['/home/ubuntu/projects/leetgpu-lab/cuda/usr/bin/cuobjdump','--dump-sass',str(out/'attention.so')],capture_output=True,text=True,check=True);(out/'attention.sass').write_text(p.stdout)
write(out/'build.json',dict(command=cmd,wall_seconds=time.monotonic()-t,source_sha256=sha(ROOT/'src/append_attention.cu'),binary_sha256=sha(out/'attention.so')));print('APPEND_BUILD_PASS')
