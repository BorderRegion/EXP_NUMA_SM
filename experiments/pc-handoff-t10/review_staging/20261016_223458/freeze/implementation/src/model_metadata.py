"""Read existing GGUF metadata only; no model execution or dequantization."""
from common import *
import struct
manifest=Path('/home/ubuntu/.ollama/models/manifests/registry.ollama.ai/library/qwen3.5/0.8b')
m=json.loads(manifest.read_text());entry=next(x for x in m['layers'] if x['mediaType'].endswith('.model'));p=Path('/home/ubuntu/.ollama/models/blobs')/entry['digest'].replace(':','-')
f=p.open('rb')
def take(fmt):return struct.unpack('<'+fmt,f.read(struct.calcsize('<'+fmt)))[0]
def string():return f.read(take('Q')).decode('utf8')
def val(t):
 if t==8:return string()
 if t==9:
  st=take('I');n=take('Q');return [val(st) for _ in range(n)]
 return take({0:'B',1:'b',2:'H',3:'h',4:'I',5:'i',6:'f',7:'?',10:'Q',11:'q',12:'d'}[t])
assert f.read(4)==b'GGUF';v=take('I');nt=take('Q');nk=take('Q');data={}
for _ in range(nk):
 key=string();value=val(take('I'))
 if not key.startswith('tokenizer.'):data[key]=value
end=f.tell();f.close();record=dict(path=str(p),file_bytes=p.stat().st_size,mtime_ns=p.stat().st_mtime_ns,manifest_sha256=sha(manifest),declared_blob_digest=entry['digest'],full_blob_rehashed=False,header_bytes_read=end,format_version=v,tensor_count=nt,metadata=data,scope='Only quantized GGUF checkpoint found. Shapes may inform LLM_SHAPED_OPERATOR_CHAIN; no claim of actual FP16 model execution or unmodified quantized numerics.')
write(ROOT/'freeze/local_model_metadata.json',record);print(json.dumps(record,ensure_ascii=False,indent=2))
