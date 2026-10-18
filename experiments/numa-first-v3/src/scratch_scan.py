"""Existing finite SM-read diagnostic, not a scheduler or production operator."""
import ctypes as C
import torch
from common import runroot
class ScratchScan:
 def __init__(self):
  self.lib=C.CDLL('libcuda.so.1');self.module=C.c_void_p();self.function=C.c_void_p()
  self.lib.cuModuleLoad.argtypes=[C.POINTER(C.c_void_p),C.c_char_p]
  self.lib.cuModuleGetFunction.argtypes=[C.POINTER(C.c_void_p),C.c_void_p,C.c_char_p]
  self.lib.cuLaunchKernel.argtypes=[C.c_void_p]+[C.c_uint]*7+[C.c_void_p,C.POINTER(C.c_void_p),C.POINTER(C.c_void_p)]
  self.lib.cuModuleUnload.argtypes=[C.c_void_p]
  self.data=torch.full((2**25,),0x5a5a5a5a,device='cuda',dtype=torch.int32);self.output=torch.empty(256,device='cuda',dtype=torch.int64)
  self.check(self.lib.cuModuleLoad(C.byref(self.module),str(runroot()/'compiled/probe.cubin').encode()))
  self.check(self.lib.cuModuleGetFunction(C.byref(self.function),self.module,b'sweep'))
  self.values=[C.c_uint64(self.data.data_ptr()),C.c_uint(self.data.numel()),C.c_uint64(self.output.data_ptr())]
  self.args=(C.c_void_p*3)(*[C.addressof(x) for x in self.values]);self()
  assert int(self.output.sum())==self.data.numel()*0x5a5a5a5a
 def check(self,code):
  if code:raise RuntimeError('CUDA driver scratch scan error '+str(code))
 def __call__(self):
  self.check(self.lib.cuLaunchKernel(self.function,256,1,1,128,1,1,0,torch.cuda.current_stream().cuda_stream,self.args,None))
 def close(self):
  if self.module.value:self.check(self.lib.cuModuleUnload(self.module));self.module=C.c_void_p()
