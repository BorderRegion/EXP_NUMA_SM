from pathlib import Path
import subprocess,io,json
OUT=Path(__file__).parent
prefix=(OUT/'scan_credentials.py').read_text().split('for base,ds,fs in os.walk(ROOT):')[0]
ns={'__file__':str(OUT/'scan_credentials.py')};exec(prefix,ns)
objects=subprocess.check_output(['git','rev-list','--objects','--all'],cwd='/home/ubuntu/文档/ChatGPT/numa_gpu',text=True).splitlines()
proc=subprocess.Popen(['git','cat-file','--batch'],cwd='/home/ubuntu/文档/ChatGPT/numa_gpu',stdin=subprocess.PIPE,stdout=subprocess.PIPE)
for entry in objects:
 a=entry.split(' ',1)
 if len(a)<2 or Path(a[1]).suffix.lower() not in ns['ext']:continue
 proc.stdin.write((a[0]+'\n').encode());proc.stdin.flush()
 header=proc.stdout.readline().split();size=int(header[2]);data=proc.stdout.read(size);assert proc.stdout.read(1)==b'\n'
 if header[1]==b'blob':ns['scan_stream'](io.BytesIO(data),'git:'+a[0]+':'+a[1])
proc.stdin.close();assert proc.wait()==0
result={'scanned_historical_text_blobs':ns['count'],'hits':ns['hits'],'values_printed':False}
(OUT/'history_credential_scan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
