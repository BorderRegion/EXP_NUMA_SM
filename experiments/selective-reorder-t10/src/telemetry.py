"""One NVML process, one sample/second; no per-load logging or controls."""
import ctypes as c, csv, glob, signal, time, sys
from common import UUID
lib=c.CDLL('libnvidia-ml.so.1');lib.nvmlInit_v2()
dev=c.c_void_p();lib.nvmlDeviceGetHandleByUUID(UUID.encode(),c.byref(dev))
stop=False
def end(*_):
 global stop;stop=True
signal.signal(signal.SIGTERM,end);signal.signal(signal.SIGINT,end)
class Util(c.Structure): _fields_=[('gpu',c.c_uint),('memory',c.c_uint)]
def u(name,*args):
 v=c.c_uint();rc=getattr(lib,name)(dev,*args,c.byref(v));return v.value if rc==0 else 'NA:'+str(rc)
with open(sys.argv[1],'w') as f:
 w=csv.writer(f);w.writerow(['wall_ns','monotonic_ns','temperature_c','power_mw','requested_limit_mw','enforced_limit_mw','sm_mhz','mem_mhz','gpu_util_pct','memory_util_pct','throttle_reasons','fan_rpm'])
 while not stop:
  util=Util();lib.nvmlDeviceGetUtilizationRates(dev,c.byref(util));th=c.c_ulonglong();rc=lib.nvmlDeviceGetCurrentClocksThrottleReasons(dev,c.byref(th));fans=[]
  for path in glob.glob('/sys/class/hwmon/hwmon*/fan1_input'):
   try: fans.append(path+':'+open(path).read().strip())
   except OSError: pass
  w.writerow([time.time_ns(),time.monotonic_ns(),u('nvmlDeviceGetTemperature',0),u('nvmlDeviceGetPowerUsage'),u('nvmlDeviceGetPowerManagementLimit'),u('nvmlDeviceGetEnforcedPowerLimit'),u('nvmlDeviceGetClockInfo',1),u('nvmlDeviceGetClockInfo',2),util.gpu,util.memory,th.value if rc==0 else 'NA:'+str(rc),'|'.join(fans)]);f.flush();time.sleep(1)
lib.nvmlShutdown()
