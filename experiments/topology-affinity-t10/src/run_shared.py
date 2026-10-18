from common import *
from worker import run
import subprocess
if __name__=='__main__':
    assert read(ROOT/'reports/GPU_COMPLETE.json')['status']=='COMPLETE'
    write(ROOT/'freeze/SHARED_GRAPH_IMPLEMENTATION.json',dict(created_utc=utc(),
        hashes={str(p.relative_to(ROOT)):sha(p) for p in list((ROOT/'src').glob('*'))+[ROOT/'build/shared_graph.so'] if p.is_file()},
        protocol_sha256=sha(ROOT/'freeze/SHARED_GRAPH_PROTOCOL.json')))
    run('sg_qualification',[PYTHON,ROOT/'src/shared_experiment.py','{OUT}','qualify'],timeout=120)
    san=REPO/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer'
    run('sg_memcheck',[san,'--tool','memcheck','--error-exitcode','9',PYTHON,ROOT/'src/shared_experiment.py','{OUT}','qualify'],timeout=180)
    for i in range(6):run(f'shared_{i}',[PYTHON,ROOT/'src/shared_experiment.py','{OUT}',i],timeout=180)
    subprocess.run([PYTHON,ROOT/'src/analyze.py','shared'],check=True)
    write(ROOT/'reports/SHARED_GPU_COMPLETE.json',dict(created_utc=utc(),status='COMPLETE'))
    print('SHARED GPU COMPLETE',flush=True)
