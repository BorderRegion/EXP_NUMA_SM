"""CPU-only semantic recomputation; restores original bytes and mtimes afterward."""
from common import *
import os,io,gzip,math
import numpy as np
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
        for name,h in read(manifest).items():assert sha(ROOT/name)==h,name
    times=ROOT/'FILE_TIMES.json'
    if times.exists():
        for name,t in read(times).items():
            p=ROOT/name
            if p.exists():os.utime(p,ns=(t,t))
    originals={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in (ROOT/'derived').iterdir() if p.is_file()}
    # Analysis is read-only with respect to raw runs and every frozen choice.
    frozen={p:sha(p) for p in (ROOT/'freeze').iterdir() if p.is_file()}
    try:
        from analyze import operator,micro
        for phase in ['dev','confirm','shared']:operator(phase,False);micro(phase)
        from analyze_full import run as full
        full()
        from analyze_fast import run as fast
        fast()
        from final_audit import run as audit
        audit()
        # Regenerate the two flat tables without touching report prose.
        from report import run as report
        report_files=[ROOT/'reports'/n for n in ['REPORT.md','REVIEW_QUESTIONS.md','DECISION.json']]
        saved={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in report_files if p.exists()}
        try:report()
        finally:
            for p,(b,t) in saved.items():p.write_bytes(b);os.utime(p,ns=(t,t))
        for p,(before,_) in originals.items():
            after=p.read_bytes()
            if p.suffix=='.json':equal(json.loads(before),json.loads(after),p.name)
            elif p.suffix=='.npz':
                a=np.load(io.BytesIO(before));b=np.load(io.BytesIO(after));assert a.files==b.files
                for k in a.files:np.testing.assert_allclose(a[k],b[k],rtol=1e-10,atol=1e-9,equal_nan=True)
            elif p.suffix in ['.csv','.gz']:
                def csvbytes(raw):return pd.read_csv(io.BytesIO(gzip.decompress(raw) if p.suffix=='.gz' else raw))
                pd.testing.assert_frame_equal(csvbytes(before),csvbytes(after),check_exact=False,rtol=1e-10,atol=1e-9)
            else:assert before==after,p
        for p,h in frozen.items():assert sha(p)==h,p
        print('CPU RECOMPUTATION PASS',len(originals),'derived files; raw data and frozen choices unchanged')
    finally:
        for p,(b,t) in originals.items():p.write_bytes(b);os.utime(p,ns=(t,t))
    if manifest.exists():
        for name,h in read(manifest).items():assert sha(ROOT/name)==h,('post-recompute changed',name)
        print('POST-RECOMPUTE ARCHIVE HASHES PASS')
if __name__=='__main__':run()
