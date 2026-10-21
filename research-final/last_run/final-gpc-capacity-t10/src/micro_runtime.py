from control import *
lib=C.CDLL(str(ROOT/'build/micro.so'));lib.micro_error.restype=C.c_char_p
lib.micro_launch.argtypes=[P,P,I,I,I,I,I,C.c_ulonglong]
class Micro:
 def __init__(self,recipe,grid,seed):
  self.recipe=recipe;self.grid=grid;self.compute=recipe=='REG_FMA';self.passes=16 if recipe.startswith('HOT') else 1;self.cg=recipe.endswith('CG')
  self.nbytes=1024 if self.compute else 2<<20 if recipe.startswith('HOT') else 128<<20 if '128' in recipe else 32<<20
  self.nvec=self.nbytes//16;self.host=np.random.default_rng(seed).integers(0,4,self.nbytes//4,dtype=np.int32).astype(np.float32)
  self.inputs=[torch.tensor(self.host+(i if not self.compute else i*.125),device='cuda') for i in range(4)]
  self.out=torch.empty((grid*128,8 if self.compute else 4),device='cuda');self.expected=[]
  for slot in range(4):
   a=self.host+(slot if not self.compute else slot*.125)
   if not self.compute:
    v=a.reshape(-1,4);ref=np.zeros((grid*128,4),np.float64)
    for offset in range(0,len(v),grid*128):ref[:len(v[offset:offset+grid*128])]+=v[offset:offset+grid*128]
    self.expected.append((ref*self.passes).astype(np.float32))
   else:
    x=a[np.arange(grid*128)%256];v=x[:,None]+np.arange(8,dtype=np.float32);mul=np.array([1.0001,1.0002,1.0003,1.0004,1.0005,1.0006,1.0007,1.0008],np.float32)
    for _ in range(128):v=(v.astype(np.float64)*mul+x[:,None]).astype(np.float32)
    self.expected.append(v)
 def op(self,slot):
  def launch(stream):
   rc=lib.micro_launch(self.inputs[slot].data_ptr(),self.out.data_ptr(),self.nvec,self.passes,int(self.cg),self.grid,int(self.compute),stream)
   if rc:raise RuntimeError(lib.micro_error().decode())
  return launch
 def check(self,slot):
  a=self.out.cpu().numpy();b=self.expected[slot]
  assert np.array_equal(a,b),float(np.max(np.abs(a-b)))
  return dict(status='PASS',raw_bit_equal=True,output_sha256=hashlib.sha256(a.tobytes()).hexdigest())
