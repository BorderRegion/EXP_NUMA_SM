"""CPU-only verification; restores original derived bytes and mtimes."""
from common import *
import os,io,math
import pandas as pd
def equal(a,b,path=''):
    if isinstance(a,dict):
        assert a.keys()==b.keys(),path
        for k in a:equal(a[k],b[k],path+'/'+str(k))
    elif isinstance(a,list):
        assert len(a)==len(b),path
        for i,(x,y) in enumerate(zip(a,b)):equal(x,y,path+'/'+str(i))
    elif isinstance(a,float):assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-9),(path,a,b)
    else:assert a==b,(path,a,b)
def run():
    manifest=ROOT/'FILE_MANIFEST.json'
    if manifest.exists():
        for n,h in read(manifest).items():assert sha(ROOT/n)==h,n
    originals={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in (ROOT/'derived').iterdir() if p.is_file()}
    frozen={p:sha(p) for p in (ROOT/'freeze').rglob('*') if p.is_file()}
    try:
        from analyze_repaired import development,short,net,calibration
        development(False);short();net();calibration()
        from audit import run as audit
        audit()
        from diagnostics import run as diagnostics
        diagnostics()
        for p,(before,_) in originals.items():
            after=p.read_bytes()
            if p.suffix=='.json':equal(json.loads(before),json.loads(after),p.name)
            elif p.suffix=='.csv':pd.testing.assert_frame_equal(pd.read_csv(io.BytesIO(before)),pd.read_csv(io.BytesIO(after)),check_exact=False,rtol=1e-10,atol=1e-9)
            else:assert before==after,p
        for p,h in frozen.items():assert sha(p)==h,p
        assert not any(n in __import__('sys').modules for n in ['torch','runtime','real_runtime'])
        print('CPU RECOMPUTATION PASS',len(originals),'derived files; raw data and frozen choices unchanged')
    finally:
        for p,(b,t) in originals.items():p.write_bytes(b);os.utime(p,ns=(t,t))
    if manifest.exists():
        for n,h in read(manifest).items():assert sha(ROOT/n)==h,('post-recompute',n)
        print('POST-RECOMPUTE ARCHIVE HASHES PASS')
if __name__=='__main__':run()
