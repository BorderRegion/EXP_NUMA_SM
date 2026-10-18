"""Reuse locked, unchanged CUDA bodies; compile only the supplemental host adapters."""
from runlib import ROOT,sha,utc
import pathlib,subprocess,json,sys,shutil,datetime
sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab');from lgjudge import cudabuild as cb
name=sys.argv[1];old=ROOT/'build'/({'renderer':'renderer_20261014T140212Z','sparse':'sparse_20261014T140520Z'}[name]);out=ROOT/'build'/('supplement_'+name+'_'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'));out.mkdir()
recipe=json.loads((old/'build.json').read_text())['recipes'];commands=[]
for item in recipe:
 cmd=item['command'] if isinstance(item,dict) else item
 if name=='renderer' and str(ROOT/'src/renderer_runner.cpp') not in cmd and '-c' in cmd:continue
 if name=='sparse' and '--cubin' in cmd:continue
 cmd=[x.replace(str(old),str(out)).replace(str(ROOT/f'src/{name}_runner.cpp'),str(ROOT/f'src/supplement/{name}_runner.cpp')) for x in cmd]
 if name=='sparse':cmd.insert(1,f'-I{ROOT}/src')
 commands.append(cmd)
if name=='renderer':
 for f in old.glob('*.o'):
  if f.name!='renderer_runner.o':shutil.copy2(f,out/f.name)
else:shutil.copy2(old/'sparse.cubin',out/'sparse.cubin')
for i,cmd in enumerate(commands):
 result=subprocess.run(cmd,env=cb._subprocess_env(),capture_output=True,text=True);(out/f'compile_{i}.log').write_text(result.stdout+result.stderr)
 print(name,i,result.returncode,result.stderr[-2000:],flush=True)
 if result.returncode:raise SystemExit('Build failed; preserved '+str(out))
ss=out/'source_snapshot';ss.mkdir()
for f in [ROOT/f'src/supplement/{name}_runner.cpp',ROOT/'src/driver_backend.hpp',ROOT/'src/render_dispatch.h']:
 shutil.copy2(f,ss/f.name)
(out/'build.json').write_text(json.dumps({'created_at':utc(),'build_id':out.name,'parent_build':str(old.relative_to(ROOT)),'commands':commands,'source_sha256':{str(f.relative_to(ROOT)):sha(f) for f in ss.iterdir()},'binary_sha256':{f.name:sha(f) for f in out.iterdir() if f.is_file() and f.suffix not in ['.json','.log']},'reuse':'CUDA numerical bodies and cubins/objects unchanged'},indent=2))
link=ROOT/'build'/('supplement_'+name+'_current');link.unlink(missing_ok=True);link.symlink_to(out.name)
print(out)
