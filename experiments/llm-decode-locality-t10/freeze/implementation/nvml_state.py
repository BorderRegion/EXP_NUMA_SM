"""Read-only NVML. Unsupported fields keep status; time units explicit."""
import ctypes as C,time
from common import UUID
class Violation(C.Structure):_fields_=[('referenceTime',C.c_ulonglong),('violationTime',C.c_ulonglong)]
class Util(C.Structure):_fields_=[('gpu',C.c_uint),('memory',C.c_uint)]
class NVML:
 def __init__(self):
  self.lib=C.CDLL('libnvidia-ml.so.1');assert self.lib.nvmlInit_v2()==0;self.dev=C.c_void_p();assert self.lib.nvmlDeviceGetHandleByUUID(UUID.encode(),C.byref(self.dev))==0
 def query(self,name,args=(),typ=C.c_uint):
  a=time.monotonic_ns();v=typ();f=getattr(self.lib,name,None);rc=f(self.dev,*args,C.byref(v)) if f else -1
  return dict(value=v.value if rc==0 else None,rc=rc,begin_ns=a,end_ns=time.monotonic_ns())
 def fast(self):
  d=dict(begin_ns=time.monotonic_ns(),wall_ns=time.time_ns())
  d['sm_mhz']=self.query('nvmlDeviceGetClockInfo',(1,))
  d['throttle_bits']=self.query('nvmlDeviceGetCurrentClocksThrottleReasons',(),C.c_ulonglong)
  d['end_ns']=time.monotonic_ns();return d
 def snapshot(self):
  d=dict(begin_ns=time.monotonic_ns(),wall_ns=time.time_ns())
  for name,fn,args,typ in [('sm_mhz','nvmlDeviceGetClockInfo',(1,),C.c_uint),('mem_mhz','nvmlDeviceGetClockInfo',(2,),C.c_uint),('power_mw','nvmlDeviceGetPowerUsage',(),C.c_uint),('limit_mw','nvmlDeviceGetEnforcedPowerLimit',(),C.c_uint),('temperature_c','nvmlDeviceGetTemperature',(0,),C.c_uint),('pstate','nvmlDeviceGetPerformanceState',(),C.c_uint),('throttle_bits','nvmlDeviceGetCurrentClocksThrottleReasons',(),C.c_ulonglong)]:d[name]=self.query(fn,args,typ)
  for name,policy in [('power',0),('thermal',1)]:
   v=Violation();a=time.monotonic_ns();f=getattr(self.lib,'nvmlDeviceGetViolationStatus',None);rc=f(self.dev,policy,C.byref(v)) if f else -1;d[name+'_violation']=dict(rc=rc,reference_us=v.referenceTime if rc==0 else None,violation_ns=v.violationTime if rc==0 else None,begin_ns=a,end_ns=time.monotonic_ns())
  u=Util();a=time.monotonic_ns();rc=self.lib.nvmlDeviceGetUtilizationRates(self.dev,C.byref(u));d['util']=dict(rc=rc,gpu=u.gpu if rc==0 else None,memory=u.memory if rc==0 else None,begin_ns=a,end_ns=time.monotonic_ns())
  d['end_ns']=time.monotonic_ns();return d
 def close(self):self.lib.nvmlShutdown()
