from __future__ import annotations
from pathlib import Path
import collections
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'reference'))
from layout_and_stats import workspace_bytes, kv_bytes, balanced_even_orders

def validate():
    cfg=json.loads((ROOT/'campaign.json').read_text())
    g=json.loads((ROOT/'plans/gemm_cases.json').read_text())
    a=json.loads((ROOT/'plans/attention_cases.json').read_text())
    red=json.loads((ROOT/'plans/reduced_confirmation.json').read_text())
    assert sum(cfg['stage_hours'].values())==cfg['gpu_worker_hours_cap']==24
    assert len(cfg['policies'])==len(set(cfg['policies']))==8
    assert len(g)==48 and len(a)==36
    assert collections.Counter(c['split'] for c in g)=={'development':16,'test':32}
    assert collections.Counter(c['split'] for c in a)=={'development':12,'test':24}
    assert len({c['case_id'] for c in g+a})==84
    assert all(not c['measured'] for c in g+a)
    assert set(red['gemm'])<=set(c['case_id'] for c in g if c['split']=='test')
    assert set(red['attention'])<=set(c['case_id'] for c in a if c['split']=='test')
    assert len(red['gemm'])==len(set(red['gemm']))==12
    assert len(red['attention'])==len(set(red['attention']))==12
    assert cfg['additional_schedule_kernel_limit']==0
    assert cfg['completed_gpu_phases']==0 and not cfg['network_during_experiment']
    counts={
        'baseline_gemm_development_cap':16*5*4*2+64,
        'pc_matrix_cell_episodes':6*4*4*2*4*4,
        'pc_counterfactual_phases':6*6*4,
        'pc_full_resource_bridge_phases':6*3*4,
        'gemm_formal_phases_including_anchors':32*8*10,
        'attention_formal_phases_including_anchors':24*8*10,
        'layer_phases':12*6*4,
        'layer_anchor_phases':12*6*2,
        'fusion_phases':6*6*4,
        'power_sensitivity_phases':4*4*4,
        'power_sensitivity_anchor_phases':4*4*2,
        'lifetime_sessions':4*3*3,
        'reduced_gemm_or_attention_phases_including_anchors':12*6*6
    }
    assert counts['pc_matrix_cell_episodes']==3072
    # Report explicit input / partial buffer sizes only, not total GPU peak.
    max_g=max(2*(c['M']*c['K']+c['K']*c['N'])+workspace_bytes(c['M'],c['N'],16,padded=True)
              +4*c['M']*c['N'] for c in g)
    max_a=max(kv_bytes(c['batch'],c['kv_length'],c['kv_heads'],c['head_dim']) for c in a)
    orders=balanced_even_orders(8)
    pairs=collections.Counter((row[i],row[i+1]) for row in orders for i in range(7))
    assert len(pairs)==56 and set(pairs.values())=={1}
    return {'status':'CPU_PLAN_VALID','gpu_executed':False,'counts':counts,
            'maximum_explicit_gemm_tensor_bytes_example':max_g,
            'maximum_KV_only_bytes':max_a,
            'memory_note':'excludes backend workspaces, graph/runtime, references and other process use',
            'gpu_worker_hours_cap':24,'cases':{'gemm':48,'attention':36}}

if __name__=='__main__':
    print(json.dumps(validate(),ensure_ascii=False,indent=2))
