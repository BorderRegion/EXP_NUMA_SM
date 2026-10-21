from common import *
import socket,sys

def request(op,**kwargs):
 s=socket.socket(socket.AF_UNIX);s.connect(str(RUN/'clock-control.sock'));s.sendall(json.dumps(dict(op=op,**kwargs)).encode());parts=[]
 while True:
  d=s.recv(65536)
  if not d:break
  parts.append(d)
 s.close();return json.loads(b''.join(parts))
if __name__=='__main__':
 print(json.dumps(request(sys.argv[1],**({'mhz':int(sys.argv[2])} if len(sys.argv)>2 else {})),ensure_ascii=False,indent=2))
