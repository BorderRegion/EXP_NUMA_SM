"""One bounded memcheck qualification; charged to original E0 worker budget."""
import argparse,pathlib,subprocess,sys,json
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=pathlib.Path);a=p.parse_args()
command=['/home/ubuntu/文档/ChatGPT/numa_gpu/op-fused/vendor/cuda-sanitizer-12.8/usr/local/cuda-12.8/compute-sanitizer/compute-sanitizer','--tool','memcheck',
 '--target-processes','all',
 '--leak-check','no','--error-exitcode','99',sys.executable,str(pathlib.Path(__file__).with_name('qualify_cutlass.py')),
 '--out',str(a.out),'--small']
result=subprocess.run(command)
(a.out/'sanitizer_result.json').write_text(json.dumps(dict(command=command,returncode=result.returncode),indent=2)+'\n')
sys.exit(result.returncode)
