"""CPU-only full raw audit, including all three statistical stages."""
from common import *
from analyze import main as core
from analyze_append import main as append
from analyze_append_strong import main as strong

def main():
 core();append();strong()
 for phase,n in [('qualification',264),('qualification_v2',264),('append_qualification',144),('stress_numeric',24)]:
  w=RUN/phase;assert read(w/'complete.json')['status']=='PASS';rows=read(w/'numerical.json');assert len(rows)==n and all(x['status']=='PASS' for x in rows)
 for name in ['memcheck','synccheck','append_memcheck','append_synccheck']:assert 'ERROR SUMMARY: 0 errors' in (RUN/name/'stdout.log').read_text()
 assert '0 hazards displayed (0 errors, 0 warnings)' in (RUN/'racecheck_targeted/stdout.log').read_text()
 for rel,dig in read(ROOT/'freeze/API_SHA256.json').items():assert sha(ROOT/rel)==dig,rel
 api=read(RUN/'verify_public_api/verification.json');assert len(api)==28 and all(x['status']=='PASS' for x in api)
 manifest=read(RUN/'verify_public_api/manifest.json')
 for name in ['optimized_decode.py','kernel_api.py']:
  assert manifest['sources']['src/'+name]==sha(ROOT/'src'/name)
 print('ALL_FROZEN_SOURCES_RAW_RESULTS_AND_CORRECTNESS_RECOMPUTED_PASS')
if __name__=='__main__':main()
