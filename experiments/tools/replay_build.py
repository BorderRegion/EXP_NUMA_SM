#!/usr/bin/env python3
"""Replay a recorded successful T10 build into a new directory. Dry-run default."""
import argparse,pathlib,json,subprocess,os,shlex
ROOT=pathlib.Path(__file__).resolve().parents[1]
def main():
 a=argparse.ArgumentParser();a.add_argument('--build-id',required=True);a.add_argument('--toolchain-root',required=True);a.add_argument('--execute',action='store_true');args=a.parse_args()
 build=ROOT/'build'/args.build_id;record=json.loads((build/'build.json').read_text());dest=ROOT/'rebuild'/args.build_id;tc=pathlib.Path(args.toolchain_root).resolve()
 # Exported records use these placeholders; source workspace records use cwd.
 def resolve(s):
  s=s.replace('${PACKAGE_ROOT}',str(ROOT)).replace('${TOOLCHAIN_ROOT}',str(tc));s=s.replace(str(build),str(dest))
  for old in [str(ROOT/'src'),str(ROOT/'build/renderer_source')]:
   if s.startswith(old+'/') and pathlib.Path(s).suffix in ['.cpp','.cu']:
    snap=build/'source_snapshot'/pathlib.Path(s).name
    if snap.exists():s=str(snap)
  return s
 commands=[[resolve(str(s))for s in (r['command']if isinstance(r,dict)else r)]for r in record['recipes']]
 if not args.execute:
  for cmd in commands:print(shlex.join(cmd))
  return
 if dest.exists():raise SystemExit('Refuse to overwrite an existing rebuild directory')
 dest.mkdir(parents=True);env=dict(os.environ)
 prefixes=[tc/'cuda',tc/'cuda/usr',tc/'toolchain/usr'];bins=[tc/'toolchain/usr/bin'];libs=[tc/'toolchain/usr/lib/x86_64-linux-gnu']
 for p in prefixes:
  bins += [p/'lib/nvidia-cuda-toolkit/bin',p/'nvvm/bin',p/'bin'];libs += [p/'lib64',p/'lib',p/'usr/lib/x86_64-linux-gnu',p/'usr/lib']
 for p in tc.glob('.venv/lib/python*/site-packages/nvidia/*/lib'):libs.append(p)
 env['PATH']=os.pathsep.join([str(p)for p in bins if p.is_dir()]+[env.get('PATH','')]);env['LD_LIBRARY_PATH']=os.pathsep.join([str(p)for p in libs if p.is_dir()]+[env.get('LD_LIBRARY_PATH','')])
 results=[]
 for i,cmd in enumerate(commands):
  # The original micro host command used inherited env, unlike CUDA jobs and
  # renderer/sparse commands, which used the rootless CUDA toolchain env.
  command_env=dict(os.environ)if args.build_id=='20261014T134450Z'and cmd[0]=='g++'else env
  p=subprocess.run(cmd,cwd=ROOT,env=command_env,capture_output=True,text=True);(dest/f'compile_{i}.txt').write_text(p.stdout+p.stderr);results.append(dict(command=cmd,returncode=p.returncode));print(i,p.returncode)
  if p.returncode:raise SystemExit('Build failed; retained logs at '+str(dest))
 (dest/'replay.json').write_text(json.dumps(results,indent=2));print('Build complete; no GPU experiment was run:',dest)
if __name__=='__main__':main()
