#!/usr/bin/env python3
"""Temporary authorized clock controller. Fixed UUID, official CLI, no arbitrary command.
No credential handling. Exits restore the original observed dynamic/default state.
"""
import os,socket,json,subprocess,signal,time,datetime,struct,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];RUN=Path((ROOT/'CURRENT_RUN.txt').read_text().strip())
UUID='GPU-8cfbc08d-0090-bc29-db9a-b2a2f7261ca5';SOCK=RUN/'clock-control.sock';LOG=RUN/'environment/ADMIN_CLOCK_COMMANDS.jsonl'
assert os.geteuid()==0
initial=subprocess.run(['/usr/bin/nvidia-smi','-q','-x','-i',UUID],capture_output=True,text=True,check=True).stdout
x=ET.fromstring(initial).find('gpu');assert x.findtext('uuid')==UUID
assert x.findtext('gpu_power_readings/requested_power_limit')=='100.00 W'
assert ET.tostring(x.find('applications_clocks')) .replace(b'applications_clocks',b'clocks')==ET.tostring(x.find('default_applications_clocks')).replace(b'default_applications_clocks',b'clocks')
supported={int(e.text.split()[0]) for e in x.findall('supported_clocks/supported_mem_clock/supported_graphics_clock')}
(RUN/'environment/ADMIN_ENTRY_INITIAL.xml').write_text(initial)
seen=[];active=False;stop=False

def command(args):
 t=datetime.datetime.now(datetime.timezone.utc).isoformat();c=['/usr/bin/nvidia-smi','-i',UUID]+args
 r=subprocess.run(c,capture_output=True,text=True,timeout=15)
 d={'utc':t,'command':c,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr}
 with LOG.open('a') as f:f.write(json.dumps(d)+'\n')
 return d

def restore():
 global active
 if active:
  d=command(['-rgc']);active=False if d['returncode']==0 else active
  return d
 return {'status':'NO_CLOCK_MUTATION_TO_RESTORE'}

def sig(*a):
 global stop
 stop=True
signal.signal(signal.SIGTERM,sig);signal.signal(signal.SIGINT,sig)
s=socket.socket(socket.AF_UNIX);s.bind(str(SOCK));os.chown(SOCK,1000,1000);os.chmod(SOCK,0o600);s.listen(1);s.settimeout(2)
print('ADMIN_CLOCK_READY',flush=True);deadline=time.monotonic()+23*3600
try:
 while not stop and time.monotonic()<deadline:
  try:conn,_=s.accept()
  except socket.timeout:continue
  with conn:
   conn.settimeout(10)
   try:
    pid,uid,gid=struct.unpack('3i',conn.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12));assert uid==1000
    req=json.loads(conn.recv(4096));op=req['op']
    if op=='lock':
     f=int(req['mhz']);assert f in supported and 300<=f<=1065
     if f not in seen:
      assert len(seen)<3 and (not seen or f<seen[-1]);seen.append(f)
     else:assert f==seen[-1]
     # A supported request may fail; still attempt restoration at exit if state is uncertain.
     active=True;out=command(['-lgc',str(f)+','+str(f)])
    elif op=='restore':out=restore()
    elif op=='read':out=command(['-q','-x'])
    elif op=='shutdown':out=restore();stop=True
    else:raise ValueError('Unsupported operation')
    conn.sendall(json.dumps(out).encode())
   except Exception as e:conn.sendall(json.dumps({'error':str(e)}).encode())
finally:
 print(json.dumps({'exit_restore':restore()}),flush=True);s.close();SOCK.unlink(missing_ok=True)
