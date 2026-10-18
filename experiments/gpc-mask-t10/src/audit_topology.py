"""CPU-only cross-check and rendering of the saved NVIDIA RM query results."""
from pathlib import Path
import collections
import csv
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
E = ROOT / 'evidence'
R = ROOT / 'reports'
R.mkdir(exist_ok=True)
data = [json.loads((E / f'topology_{i}.json').read_text()) for i in (1, 2, 3)]
assert data[0] == data[1] == data[2], 'Independent process snapshots differ'
d = data[0]
assert d['gr_info']['status'] == d['gpc_mask']['status'] == 0
capacity = {v['index']: v['value'] for v in d['gr_info']['values']}
gpc_slots, tpc_slots, sm_per_tpc = [capacity[i] for i in (20, 23, 32)]
assert gpc_slots <= 32 and tpc_slots <= 32
fs = d['floor_sweep_info']
assert fs['status'] == fs['count_status'] == 0
assert all(x['map_status'] == x['tpc_status'] == 0 for x in fs['entries'])
phys = {x['logical_gpc']: x['physical_gpc'] for x in fs['entries']}
assert len(set(phys.values())) == fs['gpc_count']
assert sum(1 << p for p in phys.values()) == d['gpc_mask']['mask']
tpcs = {x['physical_gpc']: x['mask'] for x in d['tpc_masks']}
assert all(x['status'] == 0 for x in d['tpc_masks'])
assert all(tpcs[x['physical_gpc']] == x['physical_tpc_mask'] for x in fs['entries'])
order = d['global_sm_order']
mapping = d['sm_mapping']
assert order['status'] == mapping['status'] == 0
sm = order['entries']
assert order['num_sm'] == len(sm) == mapping['count']
assert [x['sm'] for x in sm] == list(range(len(sm)))
for a, b in zip(sm, mapping['entries']):
    assert (a['sm'], a['gpc'], a['local_tpc']) == (b['sm'], b['gpc'], b['tpc'])
cuda = json.loads((E / 'cuda_device.json').read_text())
assert cuda['multiprocessor_count'] == len(sm)
assert order['num_tpc'] == sum(m.bit_count() for m in tpcs.values())
assert len(sm) == order['num_tpc'] * sm_per_tpc
groups = collections.defaultdict(list)
for x in sm:
    groups[phys[x['gpc']]].append(x['sm'])
local_tpcs = collections.defaultdict(list)
for x in sm:
    local_tpcs[x['gpc'], x['local_tpc']].append(x)
assert len(local_tpcs) == order['num_tpc']
assert all(sorted(x['local_sm'] for x in v) == list(range(sm_per_tpc)) for v in local_tpcs.values())
assert len(set(x['global_tpc'] for x in sm)) == order['num_tpc']
for g in range(gpc_slots):
    assert len(groups[g]) == tpcs[g].bit_count() * sm_per_tpc
rows = []
for g in range(gpc_slots):
    enabled = [t for t in range(tpc_slots) if tpcs[g] & (1 << t)]
    disabled = [t for t in range(tpc_slots) if not tpcs[g] & (1 << t)]
    rows.append(dict(physical_gpc=g, enabled_tpc_mask=f'0x{tpcs[g]:02x}',
                     enabled_physical_tpcs=enabled, disabled_physical_tpcs=disabled,
                     enabled_sm_count=len(groups[g]), disabled_sm_count=len(disabled)*sm_per_tpc,
                     global_logical_sm_ids=groups[g]))
with (R / 'SM_TO_GPC_TPC.csv').open('w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['global_logical_sm', 'logical_gpc', 'physical_gpc', 'logical_local_tpc', 'logical_local_sm', 'global_logical_tpc'])
    w.writeheader()
    for x in sm:
        w.writerow(dict(global_logical_sm=x['sm'], logical_gpc=x['gpc'], physical_gpc=phys[x['gpc']], logical_local_tpc=x['local_tpc'], logical_local_sm=x['local_sm'], global_logical_tpc=x['global_tpc']))
previous = json.loads((E / 'previous_SOFTMAX_MAPS.json').read_text())
pair_classes = []
for m in previous['maps']:
    counts = collections.Counter()
    for p, c in enumerate(m['consumer_per_producer']):
        a, b = sm[2*p], sm[c]
        label = 'same_tpc' if a['global_tpc'] == b['global_tpc'] else ('same_gpc_other_tpc' if a['gpc'] == b['gpc'] else 'cross_gpc')
        counts[label] += 1
    pair_classes.append(dict(page=m['page'], policy=m['policy'], **{k: counts[k] for k in ['same_tpc','same_gpc_other_tpc','cross_gpc']}))
assert all(x['same_tpc'] == 28 for x in pair_classes if x['policy'] == 'IDENTITY')
audit = dict(passed=True, independent_matching_processes=3, cuda_sm_count=len(sm),
             full_die_capacity_sm=gpc_slots*tpc_slots*sm_per_tpc,
             enabled_gpcs=len(phys), enabled_tpcs=order['num_tpc'],
             enabled_gpc_mask=f"0x{d['gpc_mask']['mask']:02x}", distribution=rows,
             logical_to_physical_gpc=phys, previous_pair_classification=pair_classes,
             optional_phys_gpc_query=dict(status=d['phys_gpc_mask']['status'],
                meaning='NV_ERR_INSUFFICIENT_PERMISSIONS; mask output invalid and not used'),
             limitations=['Effective driver-reported floorsweeping configuration, not raw fuse diagnosis.',
                          'GPC IDs are hardware identifiers, not x/y positions or interconnect hop counts.',
                          'Local logical TPC IDs must not be equated with physical TPC mask bit positions.',
                          'No new latency or operator performance measurement in this inspection.'])
(R / 'AUDIT.json').write_text(json.dumps(audit, indent=2)+'\n')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Patch
fig, ax = plt.subplots(figsize=(11, 5.7))
enabled_color, off_color = '#187f77', '#e6e8ed'
for g in range(gpc_slots):
    y = gpc_slots-1-g
    for t in range(tpc_slots):
        on = bool(tpcs[g] & (1 << t))
        ax.add_patch(Rectangle((t+.06,y+.1),.88,.73,facecolor=enabled_color if on else off_color,edgecolor='white',lw=1))
        ax.text(t+.5,y+.465,'2 SM' if on else 'OFF',ha='center',va='center',color='white' if on else '#637083',fontsize=12,fontweight='bold')
    ax.text(-.13,y+.465,f'GPC {g}',ha='right',va='center',fontsize=12)
    ax.text(6.15,y+.465,f'{len(groups[g]):2d} / 12 SM',va='center',fontsize=12,fontweight='bold')
for t in range(tpc_slots):
    ax.text(t+.5,6.05,f'TPC {t}',ha='center',fontsize=11)
ax.set(xlim=(-.9,7.6),ylim=(-.1,6.5));ax.axis('off')
fig.suptitle('Tesla T10: enabled SM distribution by physical GPC',x=.08,ha='left',fontsize=17,fontweight='bold')
fig.text(.08,.895,'56 / 72 SM enabled  |  28 / 36 TPC enabled  |  GPC mask 0x2f',fontsize=12,color='#4b5563')
fig.text(.08,.07,'NVIDIA RM 580.178.04: three independent reads agree; CUDA reports 56 SM.\nConnectivity inventory only — row/column placement is not a silicon floorplan.',fontsize=10,color='#4b5563')
fig.subplots_adjust(left=.07,right=.98,top=.84,bottom=.17)
fig.savefig(R/'GPC_DISTRIBUTION.png',dpi=160,facecolor='white')
fig.savefig(R/'GPC_DISTRIBUTION.svg',facecolor='white')
plt.close(fig)
print(json.dumps({'passed':True,'sm_distribution':[x['enabled_sm_count'] for x in rows],
                  'identity':next(x for x in pair_classes if x['page']==17 and x['policy']=='IDENTITY'),
                  'minimax_page17':next(x for x in pair_classes if x['page']==17 and x['policy']=='MINIMAX')},indent=2))
