import experiment as ex
from locality_runtime import *
import sys
prev=C.CDLL(str(ROOT/'build/legacy/append.so'));prev.ll_error.restype=C.c_char_p;prev.ll_launch.argtypes=[C.POINTER(P),C.POINTER(I),C.c_ulonglong]
class FullJob(LocalJob):
 def __init__(self,*args,deployed=False,**kwargs):
  self.deployed=deployed;super().__init__(*args,**kwargs)
 def op(self):
  if not self.deployed:return super().op()
  rc=prev.ll_launch(self.extargs,self.extcfg,torch.cuda.current_stream().cuda_stream)
  if rc:raise RuntimeError(prev.ll_error().decode())
  self.state['out']=self.d.out
original_configs=ex.configs
def configs(phase,c):
 conf=original_configs(phase,c);conf['PREVIOUS_DEPLOYED']=dict(conf['LEGACY'],deployed=c['id']!='GQA8_LONG');return conf
ex.configs=configs;ex.LocalJob=FullJob
if __name__=='__main__':ex.run(Path(sys.argv[1]),'append',int(sys.argv[2]))
