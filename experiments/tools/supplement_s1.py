from runlib import *
import sys,itertools
BASE=ROOT/'preregistration/supplement';campaign='T10_ADDENDUM_20261015'
inputs=['bonsai','ca-GrQc','train','web-Google'];perms=['ERM','EMR','REM','RME','MER','MRE']
specs=[dict(campaign=campaign,input=inp,block=b,sequence=0,policies='N'+perms[b]+'N',frames=512,conditioning_seconds=30) for b in range(6) for inp in inputs[b%4:]+inputs[:b%4]]
(BASE/'S1_matrix.json').write_text(json.dumps(specs,indent=2))
def launch(c,qual=False):
 inp=c['input'];typ='renderer' if inp in ['bonsai','train'] else 'sparse';build=(ROOT/'build'/('supplement_'+typ+'_current')).resolve();plans=ROOT/'preregistration'/('W1' if typ=='renderer' else 'W2')/inp
 c={**c,'build':str(build.relative_to(ROOT)),'frozen_plans':{p:sha(plans/(p+'.txt')) for p in ['R','M']},'asset_sha256':sha(ROOT/'assets/prepared'/inp/('model.bin' if typ=='renderer' else 'csr.bin'))}
 if typ=='renderer':args=['--assets',ROOT/'assets/prepared'/inp]
 else:args=['--input',ROOT/'assets/prepared'/inp/'csr.bin','--native-backend','cusparse','--cubin',build/'sparse.cubin']
 args+=['--purpose','qualify' if qual else 'supplement','--policies','NERM' if qual else c['policies'],'--plans',plans,'--sequence',0,'--frames',2 if qual else 512,'--conditioning-seconds',0 if qual else 30]
 p,m=run('S1_qualification' if qual else 'S1',c,args,build=build,executable=typ+'_runner')
 if m['status']!='SUCCESS':raise RuntimeError(str(p))
if __name__=='__main__':
 if sys.argv[1:] == ['qualify']:
  for inp in inputs:launch(dict(campaign=campaign,input=inp,qualification=True),True)
 else:
  done={ (r['config']['input'],r['config']['block']) for r in map(json.loads,(ROOT/'run_index.jsonl').read_text().splitlines()) if r['stage']=='S1' and r['status']=='SUCCESS'}
  for c in specs:
   if (c['input'],c['block']) not in done:launch(c)
