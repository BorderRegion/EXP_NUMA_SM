"""Observed execution coverage of low-concurrency fine-group calibration."""
import csv,json
from collections import Counter,defaultdict
import numpy as np
from common import *
from analyze_probe import DT
r=runroot();led=[json.loads(x) for x in (r/'ledger.jsonl').read_text().splitlines()];rows=[]
for w in led:
 if w['key'] not in [f'fine_shift_{i}' for i in range(4)] or w['status']!='COMPLETED':continue
 p=Path(w['out']);raw=np.memmap(p/'records.bin',DT,mode='r');stats=defaultdict(lambda:dict(epochs=0,records=0,sm_counts=Counter(),observed_cells=set(),configured_cells=set()))
 for e in csv.DictReader((p/'epochs.csv').open()):
  key=tuple(int(e[k]) for k in ['bytes','cache','cg','mode']);g=int(e['group']);start=int(e['raw_record_offset']);v=raw[start:start+512];assert np.all(v['sm_begin']==v['sm_end']);a=stats[key];a['epochs']+=1;a['records']+=len(v);a['sm_counts'][len(np.unique(v['sm_begin']))]+=1;a['observed_cells'].update((g,int(sm),int(reg)) for sm,reg in zip(v['sm_begin'],v['region']))
 for key,a in stats.items():rows.append(dict(worker=w['key'],**dict(zip(['bytes','cache','cg','mode'],key)),epochs=a['epochs'],records=a['records'],actual_sms_per_epoch_histogram=dict(a['sm_counts']),observed_group_sm_region_cells=len(a['observed_cells']),possible_cells_if_all56sms_x64=56*64,observed_cell_fraction=len(a['observed_cells'])/(56*64)))
write(r/'derived/FINE_COVERAGE_AUDIT.json',dict(generated_at=utc(),rows=rows,scope='Actual saved calibration records, not inferred from64CTA roster launch. Same resource-group membership does not imply same active-SM set or concurrency as compiled32CTA-per-group consumer. Reported union coverage across8rounds, not perround.',consumer_coverage='Compiled consumer saves SM IDs at selected complete-output checks; outputready Graph and actual membership independently verified. No perSM full-load or cache-domain guarantee.'))
print('fine execution coverage conditions',len(rows))
