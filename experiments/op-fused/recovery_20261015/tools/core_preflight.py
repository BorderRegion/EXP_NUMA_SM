#!/usr/bin/env python3
"""Offline, CPU-only source gate. Header compilation is not GPU qualification."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
REQUIRED=[
 'include/cutlass/cutlass.h',
 'include/cutlass/gemm/device/gemm_grouped.h',
 'include/cutlass/gemm/kernel/default_gemm_grouped.h',
 'include/cutlass/gemm/kernel/grouped_problem_visitor.h',
 'include/cutlass/gemm/threadblock/default_mma_core_sm75.h',
 'examples/24_gemm_grouped/gemm_grouped.cu',
 'tools/util/include/cutlass/util/host_tensor.h',
 'LICENSE.txt',
 'SOURCE_ID.json',
]
NVCC=Path('/home/ubuntu/projects/leetgpu-lab/cuda/bin/nvcc')

def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--root',type=Path,default=ROOT.parent/'vendor/cutlass')
 p.add_argument('--out',type=Path,required=True)
 p.add_argument('--compile-headers',action='store_true')
 a=p.parse_args();a.root=a.root.resolve();a.out.mkdir(parents=True,exist_ok=False)
 missing=[s for s in REQUIRED if not (a.root/s).is_file()]
 report=dict(time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),root=str(a.root),
     missing=missing,source_complete=False,header_compile_status='NOT_RUN',
     gpu_qualified=False,candidate_implemented=False,network_used=False)
 def save(): (a.out/'preflight.json').write_text(json.dumps(report,indent=2)+'\n')
 if missing:
  report['status']='MUTABLE_CORE_SOURCE_MISSING';save();print(json.dumps(report,indent=2));return 2
 identity=json.loads((a.root/'SOURCE_ID.json').read_text())
 commit=identity.get('commit','')
 if len(commit)!=40 or any(c not in '0123456789abcdef' for c in commit):
  report['status']='SOURCE_ID_REQUIRES_FULL_COMMIT';save();return 2
 report['supplied_identity']=identity
 files=[]
 for path in sorted(a.root.rglob('*')):
  if not path.is_file() or '.git' in path.relative_to(a.root).parts: continue
  files.append(dict(path=str(path.relative_to(a.root)),bytes=path.stat().st_size,
                    sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
 (a.out/'source_manifest.json').write_text(json.dumps(files,indent=2)+'\n')
 # Required paths are necessary, not proof every transitive dependency is present.
 report['required_files_present']=True
 report['status']='FILES_PRESENT_PENDING_BUILD_AND_GPU_QUALIFICATION'
 if a.compile_headers:
  probe=a.out/'headers.cu'
  probe.write_text('\n'.join('#include "'+s.removeprefix('include/')+'"'
      for s in REQUIRED if s.startswith('include/'))+'\nint main(){return 0;}\n')
  sys.path.insert(0,'/home/ubuntu/projects/leetgpu-lab')
  from lgjudge import cudabuild as cb
  report['local_build_helper_sha256']=hashlib.sha256(Path(cb.__file__).read_bytes()).hexdigest()
  command=[str(NVCC),'-ccbin',str(cb.find_host_compiler()),'-std=c++17','-arch=sm_75',
     *['-I'+str(d) for d in cb.include_dirs()],
     '-I'+str(a.root/'include'),'-I'+str(a.root/'tools/util/include'),
     '-c',str(probe),'-o',str(a.out/'headers.o')]
  report['header_command']=command
  run=subprocess.run(command,capture_output=True,text=True,env=cb._subprocess_env())
  (a.out/'build_stdout.txt').write_text(run.stdout);(a.out/'build_stderr.txt').write_text(run.stderr)
  report['header_compile_returncode']=run.returncode
  report['header_compile_status']='PASS_HEADERS_ONLY' if run.returncode==0 else 'FAILED'
  report['probe_dependencies_complete']=run.returncode==0
  report['source_complete']=None
  report['source_complete_scope']='UNKNOWN; probe checks only its transitive headers, not every example or instantiation'
  if run.returncode: report['status']='BUILD_DEPENDENCY_OR_COMPATIBILITY_GAP'
 save();print(json.dumps(report,indent=2))
 return 0 if report['header_compile_status']=='PASS_HEADERS_ONLY' else 2

if __name__=='__main__':sys.exit(main())
