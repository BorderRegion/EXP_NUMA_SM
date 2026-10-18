"""Optional CPU-only solver accelerator, validated against every executed mapping.
The GPU campaign used the frozen pure Python implementation. This does not change
any GPU kernel, timing, historical schedule, calibration, or performance result.
"""
from pathlib import Path
import ctypes as C
import numpy as np
import schedule
ROOT=Path(__file__).resolve().parents[1]
lib=C.CDLL(str(ROOT/'build/fast_assignment.so'))
lib.ag_hungarian.argtypes=[C.POINTER(C.c_double),C.c_int,C.c_int,C.POINTER(C.c_int)]
def hungarian(cost):
 a=np.ascontiguousarray(cost,dtype=np.float64);n,m=a.shape;out=np.empty(n,np.int32);rc=lib.ag_hungarian(a.ctypes.data_as(C.POINTER(C.c_double)),n,m,out.ctypes.data_as(C.POINTER(C.c_int)));assert rc==0;return out

def enable():schedule.hungarian=hungarian
