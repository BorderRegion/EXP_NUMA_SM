#!/usr/bin/env python3
"""CPU-only diagnostics for normalized new request records. No GPU inference.
Usage: python tools/analyze_focus.py requests.csv result.json
Required: episode_id,process_block,case_id,phase,window,label,input_slot,
          cpu_ready_us. Optional: gpu_span_us and integer monotonic timestamps.
Missing GPU values remain missing; no outlier removal or clock correction.
"""
from __future__ import annotations
import argparse,csv,json,math,statistics
from collections import defaultdict
from pathlib import Path
from typing import Iterable

def geomean(values: Iterable[float])->float:
    v=list(values)
    if not v or any(not math.isfinite(x) or x<=0 for x in v):
        raise ValueError('finite positive timings required')
    return math.exp(statistics.fmean(math.log(x) for x in v))

def quartet(labels: str, times: Iterable[float])->dict:
    t=list(times)
    if len(t)!=4 or len(labels)!=4 or labels.count('A')!=2 or labels.count('B')!=2:
        raise ValueError('expected exactly two A and two B windows')
    # Validate every input, including values not in a selected numerator.
    geomean(t)
    ga=geomean(t[i] for i in range(4) if labels[i]=='A')
    gb=geomean(t[i] for i in range(4) if labels[i]=='B')
    return {'B_over_A':gb/ga,
            'middle_over_outer':geomean(t[1:3])/geomean([t[0],t[3]]),
            'absolute_B_minus_A_us':statistics.fmean(t[i] for i in range(4) if labels[i]=='B')-statistics.fmean(t[i] for i in range(4) if labels[i]=='A'),
            'window_means_us':t,'labels':labels}

def decomposition(begin:int,context:int,launch:int,ready:int,end:int)->dict:
    stamps=[begin,context,launch,ready,end]
    if stamps!=sorted(stamps):raise ValueError('nonmonotonic request timestamps')
    return dict(context_us=(context-begin)/1000,launch_us=(launch-context)/1000,
                wait_us=(ready-launch)/1000,event_read_us=(end-ready)/1000,
                ready_us=(ready-begin)/1000,instrumented_us=(end-begin)/1000)

def trace_account(total_us:float, records:list[dict])->dict:
    if not math.isfinite(total_us) or total_us<0:raise ValueError('invalid total')
    out=defaultdict(lambda:dict(requests=0,cpu_ready_us=0.,gpu_span_us=0.,gpu_observed=0))
    seen=set()
    for x in records:
        rid=int(x['request'])
        if rid in seen:raise ValueError('duplicate request ordinal')
        seen.add(rid)
        v=float(x['cpu_ready_us'])
        if not math.isfinite(v) or v<0:raise ValueError('invalid ready timing')
        row=out[str(x['case_id'])];row['requests']+=1;row['cpu_ready_us']+=v
        g=x.get('gpu_span_us',x.get('gpu_us'))
        if g is not None and g!='':
            g=float(g)
            if not math.isfinite(g) or g<0:raise ValueError('invalid GPU timing')
            row['gpu_span_us']+=g;row['gpu_observed']+=1
    ready_sum=sum(v['cpu_ready_us'] for v in out.values())
    return {'by_signature':dict(out),'requests':len(records),'total_completion_us':total_us,
            'sum_ready_us':ready_sum,'other_host_intervals_us':total_us-ready_sum,
            'note':'Residual is not automatically selector cost. GPU sums are not trace wall time.'}

def analyze(path:Path)->dict:
    groups=defaultdict(list)
    with path.open(newline='',encoding='utf-8') as f:
        for row in csv.DictReader(f):groups[row['episode_id']].append(row)
    result=[]
    for eid,rows in groups.items():
        windows=defaultdict(list)
        for r in rows:
            if r['phase']=='measure':windows[int(r['window'])].append(r)
        ids=sorted(windows);effects=[]
        for off in range(0,len(ids),4):
            chunk=ids[off:off+4]
            if len(chunk)!=4:continue
            label=[];cpu=[];gpu=[]
            for wi in chunk:
                wr=windows[wi];ls={r['label'] for r in wr}
                if len(ls)!=1:raise ValueError('mixed window labels')
                label.append(next(iter(ls)));cpu.append(statistics.fmean(float(r['cpu_ready_us']) for r in wr))
                gv=[float(r['gpu_span_us']) for r in wr if r.get('gpu_span_us','')!='']
                gpu.append(statistics.fmean(gv) if len(gv)==len(wr) else None)
            e={'window_ids':chunk,'cpu':quartet(''.join(label),cpu)}
            e['gpu']=quartet(''.join(label),gpu) if all(x is not None for x in gpu) else None
            effects.append(e)
        first=rows[0]
        result.append({'episode_id':eid,'case_id':first['case_id'],'block':first['process_block'],
                       'rows':len(rows),'warmup_rows':sum(r['phase']=='warmup' for r in rows),
                       'measured_windows':len(windows),'quartets':effects})
    return {'source':str(path),'scope':'CPU diagnostics; no independent hardware samples created','episodes':result}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('csv',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    o=analyze(a.csv);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
if __name__=='__main__':main()
