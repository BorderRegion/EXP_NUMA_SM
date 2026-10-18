"""List planned counts and block orders. Does not execute experiments."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from math import prod
from reference_math import even_williams_orders

ROOT = Path(__file__).resolve().parents[1]

def validate(config: dict) -> None:
    assert config['status'] == 'DESIGN_NOT_EXECUTED'
    for platform, values in config['platforms'].items():
        assert sum(values['stage_hours'].values()) == values['worker_hours_cap'], platform
    assert config['runtime']['offline']
    assert not config['runtime']['disable_thermal_protection']
    assert config['runtime']['new_standalone_schedule_kernels'] == 0
    assert not config['runtime']['schedule_task_lookup_tables']
    assert not config['runtime']['schedule_page_lookup_tables']
    assert not config['runtime']['new_driver_install_authorized']
    assert len(set(config['strategies'])) == 8
    assert config['numa']['development_allocations'] + config['numa']['confirmation_allocations'] == config['numa']['allocations']
    assert config['numa']['fit_regions'] + config['numa']['confirm_regions'] == config['numa']['regions_max']


def plan(config: dict) -> dict:
    validate(config)
    counts = {key: prod(values.values()) for key, values in config['matrix'].items()}
    a=config['numa']
    count_strata=a['allocations']*len(a['workset_l2_factors'])*len(a['load_recipes'])*len(a['concurrency'])
    main=sum(counts[key] for key in ('render','sparse','inference'))
    blockcount=sum(config['matrix'][key]['cases']*config['matrix'][key]['blocks'] for key in ('render','sparse','inference'))
    return {'status':'PLANNED_ONLY_NOT_GPU_RESULTS','counts':counts,
            'numa_strata_max':count_strata,'main_application_sessions_max':main,
            'main_application_blocks_max':blockcount,
            'extra_native_anchor_measurements_max':2*blockcount,
            'main_plus_anchors_max':main+2*blockcount,
            'total_worker_hours_cap_all_platforms':sum(v['worker_hours_cap'] for v in config['platforms'].values()),
            'eight_strategy_orders':[[config['strategies'][i] for i in row] for row in even_williams_orders(8)],
            'notes':['All counts are conditional caps. Missing cells keep their reason.',
                     'NUMA cache/order/scout subconditions are recorded separately, not hidden as one observation.',
                     'Native head/tail anchors are diagnostic, never replace the balanced primary N.']}

if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output', default='generated_plan.json')
    args=parser.parse_args()
    cfg=json.loads((ROOT/'campaign.json').read_text(encoding='utf-8'))
    output=Path(args.output)
    if output.exists():
        raise SystemExit(f'Refusing to overwrite {output}; choose a new output path.')
    output.write_text(json.dumps(plan(cfg),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Wrote plan only: {output}')
