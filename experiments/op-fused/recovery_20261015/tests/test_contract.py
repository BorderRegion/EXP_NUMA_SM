"""Cross-language finite mapping checks; no CUDA imports or GPU claims."""
import collections
import importlib.util
import json
import pathlib
import random
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('protocol_reference', ROOT.parent/'protocol/tools/reference.py')
ref = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = ref
spec.loader.exec_module(ref)

def run():
    (ROOT/'build').mkdir(exist_ok=True)
    executable = ROOT/'build/packet_cli'
    build = subprocess.run(['g++','-std=c++17','-O2','-Wall','-Wextra','-Werror',
        '-I'+str(ROOT/'include'), str(ROOT/'tests/packet_cli.cpp'), '-o',str(executable)],
        text=True,capture_output=True,check=True)
    rng = random.Random(2026101520)
    cases = []
    # Explicit empty/zero-N/short-tail/heterogeneous-K and q=1 cases.
    for shapes in [[],[(0,128,32)],[(65,0,32)],[(65,257,4096)],
                   [(513,129,32),(0,64,128),(65,257,4096)]]:
        for kind in range(3):
            cases.append((32,64,32,3,4,2,128,kind,shapes))
    for _ in range(500):
        cases.append((rng.choice([16,32,64]),rng.choice([32,64,128]),32,
            rng.choice([1,2,7,56,112]),rng.choice([1,2,4]),rng.choice([1,2]),
            rng.choice([16,64,128,256]),rng.randrange(3),
            [(rng.randrange(700),rng.choice([0,31,128,257]),rng.choice([16,32,64,2048,4096]))
             for _ in range(rng.randrange(10))]))
    lines=[str(len(cases))]
    expected=[]
    for bm,bn,bk,workers,q,waves,budget,kind,shapes in cases:
        lines.append(' '.join(map(str,[bm,bn,bk,workers,q,waves,budget,kind,len(shapes)])))
        lines.extend(' '.join(map(str,s)) for s in shapes)
        problems=[ref.Problem(*s) for s in shapes]
        if kind==0:
            packets=ref.make_packets(problems,bm,bn,bk,workers,q,waves,budget)
        else:
            # Independent explicit fixed-q / q1 baseline enumeration.
            packets=[]
            for e,p in enumerate(problems):
                mt,nt=ref.ceil_div(p.m,bm),ref.ceil_div(p.n,bn)
                if not mt or not nt: continue
                pq=1 if kind==2 else ref.floor_pow2(min(q,mt))
                packets.extend(ref.Packet(e,n,m,min(pq,mt-m))
                               for n in range(nt) for m in range(0,mt,pq))
        expected.append((problems,packets))
    output=subprocess.run([str(executable)],input='\n'.join(lines)+'\n',
        capture_output=True,text=True,check=True).stdout.splitlines()
    assert len(output)==len(cases)
    packet_count=tile_count=q_gt1=0
    for case,line,(problems,packets) in zip(cases,output,expected):
        bm,bn,bk,workers,*_=case
        actual=[tuple(map(int,p.split(','))) for p in line.split(';') if p]
        wanted=[(wid,p.problem,p.n_tile,p.m_first,p.length)
                for wid,seq in enumerate(ref.assign_static(packets,workers)) for p in seq]
        assert actual==wanted, (case,actual[:3],wanted[:3])
        seen=collections.Counter((e,m,n) for _,e,n,m0,length in actual for m in range(m0,m0+length))
        assert set(seen)==ref.expected_tiles(problems,bm,bn)
        assert all(v==1 for v in seen.values())
        packet_count+=len(actual);tile_count+=len(seen)
        q_gt1+=any(p[-1]>1 for p in actual)
    # q=1 still fixes n-major packet order; native order remains unknown.
    q1=ref.make_packets([ref.Problem(64,128,32)],32,64,32,1,1,1,128)
    assert [t for p in q1 for t in p.tiles()]==[(0,0,0),(0,1,0),(0,0,1),(0,1,1)]
    result=dict(status='CPU_CONTRACT_PASS_ONLY',cases=len(cases),packets=packet_count,
        tiles=tile_count,cases_with_multitile_packets=q_gt1,
        generation_mismatch_rejected=True,unique_coverage=True,gpu_qualified=False,
        source= 'Original protocol Python enumeration versus new C++ ordinal decoder',
        q1_native_identity='UNKNOWN_WITHOUT_NATIVE_VISITOR',compiler_stderr=build.stderr)
    (ROOT/'reports/cpu_contract_validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__': run()
