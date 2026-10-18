from runlib import *
import sys,random
C='T10_ADDENDUM_20261015';BASE=ROOT/'preregistration/supplement'
def build():return (ROOT/'build/supplement_address_current').resolve()
def run_probe(allocation,mode,small=False,sanitizer=None):
 b=build();c=dict(campaign=C,allocation=allocation,mode=mode,qualification=small,sanitizer=sanitizer,configurations=4 if small else 12)
 args=['--allocation',allocation,'--mode',mode,'--rounds',1 if small else 6,'--qualify',int(small),'--cubin',b/'address.cubin']
 if mode=='confirm':
  choice=json.loads((BASE/'S2_layout_choice.json').read_text());args+=['--window-bytes',choice['window_bytes']];c['layout_choice_sha256']=sha(BASE/'S2_layout_choice.json')
 prefix=None
 if sanitizer:prefix=[ROOT/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer','--tool',sanitizer,'--error-exitcode','42']
 p,m=run('S2_sanitizer' if sanitizer else 'S2_qualification' if small else 'S2',c,args,executable='address_probe_runner',build=b,prefix=prefix)
 if m['status']!='SUCCESS':raise RuntimeError(p)
 return p

def run_deploy(c,small=False,sanitizer=None):
 b=build();c={**c,'campaign':C,'qualification':small,'sanitizer':sanitizer};window=json.loads((BASE/'S2_layout_choice.json').read_text())['window_bytes'] if (BASE/'S2_layout_choice.json').exists() else 4096
 args=['--bytes',65536 if small else c['bytes'],'--block',c['block'],'--window-bytes',window,'--irregular',c['irregular'],'--policies',c['policies'],'--qualify',int(small),'--warmup',1 if small else 32,'--epochs',2 if small else 128,'--cubin',b/'address.cubin']
 prefix=[ROOT/'vendor/cuda_sanitizer_api-linux-x86_64-12.8.93-archive/bin/compute-sanitizer','--tool',sanitizer,'--error-exitcode','42'] if sanitizer else None
 p,m=run('S3_sanitizer' if sanitizer else 'S3_qualification' if small else 'S3',c,args,executable='address_deploy_runner',build=b,prefix=prefix)
 if m['status']!='SUCCESS':raise RuntimeError(p)
 return p
if __name__=='__main__':
 action=sys.argv[1]
 if action=='qualify':
  run_probe(99,'dev',True)
  for irregular in [0,1]:run_deploy(dict(bytes=65536,irregular=irregular,block=99,policies='NIABCN'),True)
  for tool in ['memcheck','synccheck']:
   run_probe(99,'dev',True,tool)
   run_deploy(dict(bytes=65536,irregular=1,block=99,policies='NIABCN'),True,tool)
 elif action in ['dev','confirm']:
  done={r['config']['allocation'] for r in map(json.loads,(ROOT/'run_index.jsonl').read_text().splitlines()) if r['stage']=='S2' and r['status']=='SUCCESS'}
  for allocation in range(3) if action=='dev' else range(3,6):
   if allocation not in done:run_probe(allocation,action)
 elif action=='deploy':
  choice=json.loads((BASE/'S2_layout_choice.json').read_text());assert choice['valid_group_matrix']
  specs=[]
  for block in range(6):
   cells=[(2097152,0),(33554432,1),(2097152,1),(33554432,0)];cells=cells[block%4:]+cells[:block%4]
   for size,irregular in cells:
    p=list('IABC');random.Random(2026101503+block*101+size+irregular).shuffle(p);specs.append(dict(bytes=size,irregular=irregular,block=block,policies='N'+''.join(p)+'N'))
  (BASE/'S3_matrix.json').write_text(json.dumps(specs,indent=2))
  done={(r['config']['bytes'],r['config']['irregular'],r['config']['block']) for r in map(json.loads,(ROOT/'run_index.jsonl').read_text().splitlines()) if r['stage']=='S3' and r['status']=='SUCCESS'}
  for c in specs:
   if (c['bytes'],c['irregular'],c['block']) not in done:run_deploy(c)
