"""V2 timing and bookkeeping. No dispatch based on confirmation timings."""
import datetime, hashlib, json, math, time
from pathlib import Path
import torch
from native_bench import utc
from reference import balanced_orders

SEEDS=[2026101637,2026101651,2026101663,2026101679,2026101693,2026101709]
def write(p,obj):
    Path(p).write_text(json.dumps(obj,indent=2)+'\n')
def seed(case,block):
    return SEEDS[block]+int(hashlib.sha256(case['case_id'].encode()).hexdigest()[:6],16)
def batch_phase(fn,repeats,warm_ms=150):
    a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True)
    def batch(n):
        torch.cuda.synchronize();t=time.perf_counter();a.record()
        for _ in range(n):fn()
        b.record();b.synchronize()
        return a.elapsed_time(b),(time.perf_counter()-t)*1000
    start=utc();warm=0;warmtime=0
    while warm<64 or warmtime<warm_ms:
        d,_=batch(64);warm+=64;warmtime+=d
    d,c=batch(repeats)
    return dict(start=start,end=utc(),warmup_repeats=warm,warmup_device_ms=warmtime,
      measured_requests=repeats,device_interval_ms=d/repeats,operator_or_layer_ready_ms=c/repeats,
      aggregate_device_ms=d,endpoint='BATCH_END_WAIT',timing_label='CUDA_EVENT_SPAN_INCLUDES_SUBMISSION_GAPS; AMORTIZED_NOT_REQUEST_P99')
def request_phase(fn,repeats=64):
    a=torch.cuda.Event(enable_timing=True);b=torch.cuda.Event(enable_timing=True)
    def once():
        t=time.perf_counter();a.record();fn();b.record();b.synchronize()
        return a.elapsed_time(b),(time.perf_counter()-t)*1000
    start=utc();warm=0;warmtime=0
    while warm<64 or warmtime<150:
        d,_=once();warm+=1;warmtime+=d
    samples=[once() for _ in range(repeats)]
    return dict(start=start,end=utc(),warmup_repeats=warm,warmup_device_ms=warmtime,
      measured_requests=repeats,device_interval_ms=sum(x[0] for x in samples)/repeats,
      operator_or_layer_ready_ms=sum(x[1] for x in samples)/repeats,
      request_device_ms=[x[0] for x in samples],request_ready_ms=[x[1] for x in samples],
      endpoint='ONE_OUTPUT_READY_WAIT_PER_REQUEST',p99_claim=None)
def phase_order(names,block,caseid,anchor):
    order=balanced_orders(names,6,2026101600+int(hashlib.sha256(caseid.encode()).hexdigest()[:6],16))[block]
    return [(anchor,'anchor_head')]+[(n,'primary') for n in order]+[(anchor,'anchor_tail')]
def memory():
    free,total=torch.cuda.mem_get_info();peak=torch.cuda.max_memory_reserved()
    return dict(peak_reserved_bytes=peak,free_after=free,total=total,
      conservative_margin_pass=peak<=total-max(2*2**30,math.ceil(.15*total)))
def setup():
    torch.set_num_threads(2);torch.backends.cuda.preferred_blas_library('cublas')
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cuda.matmul.allow_fp16_reduced_precision_reduction=False
