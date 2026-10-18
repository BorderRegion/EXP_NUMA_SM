"""One lightweight NVML process at1Hz. Every field has separate query brackets."""
import ctypes as c,csv,glob,signal,time,sys,json
from common import UUID
lib=c.CDLL('libnvidia-ml.so.1');rc=lib.nvmlInit_v2();assert rc==0
dev=c.c_void_p();assert lib.nvmlDeviceGetHandleByUUID(UUID.encode(),c.byref(dev))==0
period=float(sys.argv[2]) if len(sys.argv)>2 else 1.0
stop=False
def end(*_):
 global stop;stop=True
signal.signal(signal.SIGTERM,end);signal.signal(signal.SIGINT,end)
class Util(c.Structure):_fields_=[('gpu',c.c_uint),('memory',c.c_uint)]
queries=[('temperature_c','nvmlDeviceGetTemperature',[0]),('power_mw','nvmlDeviceGetPowerUsage',[]),('requested_limit_mw','nvmlDeviceGetPowerManagementLimit',[]),('enforced_limit_mw','nvmlDeviceGetEnforcedPowerLimit',[]),('sm_mhz','nvmlDeviceGetClockInfo',[1]),('mem_mhz','nvmlDeviceGetClockInfo',[2])]
with open(sys.argv[1],'w') as f:
 fields=['wall_ns','monotonic_ns']+[x[0] for x in queries]+['gpu_util_pct','memory_util_pct','throttle_reasons','fan_rpm','field_query_bounds_json']
 w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
 while not stop:
  start=time.monotonic();row=dict(wall_ns=time.time_ns(),monotonic_ns=time.monotonic_ns());bounds={}
  for name,fn,args in queries:
   v=c.c_uint();a=time.monotonic_ns();rc=getattr(lib,fn)(dev,*args,c.byref(v));b=time.monotonic_ns();bounds[name]=[a,b,rc];row[name]=v.value if rc==0 else 'NA:'+str(rc)
  v=Util();a=time.monotonic_ns();rc=lib.nvmlDeviceGetUtilizationRates(dev,c.byref(v));bounds['utilization']=[a,time.monotonic_ns(),rc];row.update(gpu_util_pct=v.gpu if rc==0 else 'NA',memory_util_pct=v.memory if rc==0 else 'NA')
  v=c.c_ulonglong();a=time.monotonic_ns();rc=lib.nvmlDeviceGetCurrentClocksThrottleReasons(dev,c.byref(v));bounds['throttle_reasons']=[a,time.monotonic_ns(),rc];row['throttle_reasons']=v.value if rc==0 else 'NA:'+str(rc)
  fans=[]
  for path in glob.glob('/sys/class/hwmon/hwmon*/fan1_input'):
   a=time.monotonic_ns()
   try:fans.append(path+':'+open(path).read().strip());bounds[path]=[a,time.monotonic_ns(),0]
   except OSError as e:bounds[path]=[a,time.monotonic_ns(),str(e)]
  row['fan_rpm']='|'.join(fans);row['field_query_bounds_json']=json.dumps(bounds,separators=(',',':'));w.writerow(row);f.flush();time.sleep(max(0,period-(time.monotonic()-start)))
lib.nvmlShutdown()
