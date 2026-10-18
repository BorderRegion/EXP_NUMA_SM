from pathlib import Path
import os,re,json,zipfile
ROOT=Path('/home/ubuntu/文档/ChatGPT/numa_gpu');OUT=Path(__file__).parent
patterns={
 'private_key':re.compile(rb'-----BEGIN (?:OPENSSH |RSA |EC |DSA )?PRIVATE KEY-----'),
 'github_token':re.compile(rb'(?:gh[pousr]_[A-Za-z0-9]{20,128}|github_pat_[A-Za-z0-9_]{30,200})'),
 'credential_assignment':re.compile(rb'(?i)(?:password|passwd|api[_-]?key|access[_-]?token|auth[_-]?token|secret)\s{0,20}[=:]\s{0,20}[\"\'][^\"\'\r\n]{6,200}[\"\']'),
 'url_credential':re.compile(rb'https?://[^\s/@:\"\']{1,128}:[^\s/@\"\']{1,128}@'),
 'sudo_password_pipe':re.compile(rb'(?i)(?:echo|printf)[^\n]{1,120}\|[^\n]{0,50}sudo\s+-S')}
ext={'.md','.py','.sh','.json','.jsonl','.yaml','.yml','.toml','.txt','.log','.csv','.cu','.cuh','.cpp','.h','.hpp','.c','.xml','.html','.js','.ini','.conf','.service','.diff','.patch'}
hits=[];count=0;zipcount=0

def scan_stream(f,label):
 global count
 count+=1;overlap=b'';offset=0
 if count%5000==0:print('SCANNED',count,flush=True)
 while True:
  b=f.read(2**20)
  if not b:break
  buf=overlap+b
  low=buf.lower()
  needles={'private_key':[b'private key-----'],'github_token':[b'ghp_',b'gho_',b'ghu_',b'ghs_',b'ghr_',b'github_pat_'],'credential_assignment':[b'password',b'passwd',b'apikey',b'api_key',b'api-key',b'access',b'auth',b'secret'],'url_credential':[b'://'],'sudo_password_pipe':[b'sudo']}
  for name,rx in patterns.items():
   if not any(n in low for n in needles[name]):continue
   found=list(rx.finditer(buf))
   if found:hits.append({'path':label,'kind':name,'approx_byte_offset':offset,'matches':len(found)})
  overlap=buf[-1024:];offset+=len(b)

def visit(p,label):
 global zipcount
 if p.suffix.lower() in ext or p.name in ['.env','.netrc']:
  with p.open('rb') as f:scan_stream(f,label)
 elif p.suffix.lower()=='.zip':
  zipcount+=1
  with zipfile.ZipFile(p) as z:
   for info in z.infolist():
    if Path(info.filename).suffix.lower() in ext:
     with z.open(info) as f:scan_stream(f,label+'::'+info.filename)
for base,ds,fs in os.walk(ROOT):
 ds[:]=[d for d in ds if d not in ['.git','__pycache__','.venv']]
 for n in fs:
  p=Path(base)/n
  if not p.is_symlink():visit(p,str(p.relative_to(ROOT)))
for p in Path('/home/ubuntu/下载').iterdir():
 if p.is_file() and any(s in p.name for s in ['T10','GPU','NUMA','FUSED']):visit(p,'downloads/'+p.name)
for base,ds,fs in os.walk('/home/ubuntu/桌面/GPU双卡拓扑实验_交付_20261014'):
 for n in fs:
  p=Path(base)/n
  if not p.is_symlink():visit(p,'desktop/'+str(p.relative_to('/home/ubuntu/桌面/GPU双卡拓扑实验_交付_20261014')))
r={'scanned_text_members':count,'zip_files':zipcount,'hits':hits,'values_printed':False}
(OUT/'credential_scan.json').write_text(json.dumps(r,ensure_ascii=False,indent=2))
print(json.dumps(r,ensure_ascii=False),flush=True)
