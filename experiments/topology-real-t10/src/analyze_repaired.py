"""Serialization-only repair; frozen analysis math and raw data unchanged.

The prefix horizon's primary flag can be numpy.bool_, which stdlib JSON
rejects. Normalize NumPy scalar types at the serialization boundary.
"""
import numpy as np
import common
import analyze as frozen
def native(x):
    if isinstance(x,np.generic):return x.item()
    if isinstance(x,dict):return {k:native(v) for k,v in x.items()}
    if isinstance(x,(list,tuple)):return [native(v) for v in x]
    return x
def write(path,value):common.write(path,native(value))
frozen.write=write
development=frozen.development
short=frozen.short
net=frozen.net
calibration=frozen.calibration
if __name__=='__main__':short();net();calibration()
