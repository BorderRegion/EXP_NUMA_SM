"""Independent finite delivery checks, CPU-only, no reruns or favourable filtering."""
import datetime,hashlib,json,math,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[1]
RUN=pathlib.Path((ROOT/'implementation_same_q_v2/CURRENT_RUN.txt').read_text().strip())
def main():
    prefix=(RUN/'registry_prefix.jsonl').read_bytes();allbytes=(ROOT/'registry/runs.jsonl').read_bytes()
    assert allbytes.startswith(prefix)
    rows=[json.loads(s) for s in allbytes.splitlines()];new=rows[92:]
    assert all(m['campaign']=='T10_SAME_Q_AND_BACKBONE_V2' and m['status']=='COMPLETED' for m in new)
    assert sum(m['worker_occupied_s'] for m in new)<=14400
    assert sum(m['worker_occupied_s'] for m in rows)<=57600
    for a,b in zip(rows,rows[1:]):assert a['released_at']<=b['lock_acquired_at']
    lock=json.loads((RUN/'INPUT_LOCK.json').read_text())
    for p,digest in lock.items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==digest,p
    protocol=json.loads((RUN/'PROTOCOL_V2.json').read_text());freeze=json.loads((RUN/'BODY_AND_BASELINE_FREEZE_V2.json').read_text())
    records={};phasecount=0;numchecks=0;bitwise=0;raw=[];sources={};binary=set()
    for m in new:
        path=ROOT/m['path'];manifest=json.loads((path/'frozen/op-fused/FROZEN_SOURCE_MANIFEST.json').read_text())
        table={x['path']:x['sha256'] for x in manifest}
        for p in ['src/same_q_v2/libopf_grouped.so','src/same_q_v2/q1_minimal.h','src/same_q_v2/packet_visitor.h','src/same_q_v2/backend.cu']:
            source=path/'frozen/op-fused'/p
            assert hashlib.sha256(source.read_bytes()).hexdigest()==table[p]
            sources.setdefault(p,set()).add(table[p])
        if 'formal_' in m['key']:
            assert freeze['frozen_at']<m['process_started_at']
            copied=json.loads((path/'input/BODY_AND_BASELINE_FREEZE_V2.json').read_text());assert copied==freeze
        for p in path.glob('*.json'):
            d=json.loads(p.read_text())
            if not isinstance(d,dict) or 'case' not in d:continue
            assert d['status']=='PASS',(m['key'],p.name,d.get('error'))
            if d.get('phases'):
                for row in d['phases']:
                    assert row['warmup_repeats']>=64 and row['warmup_device_ms']>=150
                    assert row['measured_requests']==64 if d['case']['suite']=='moe_layer' else 32<=row['measured_requests']<=256
                    for check in row.get('correctness',[]):assert check['pass'];numchecks+=1
                    if row.get('same_body_bitwise') is not None:assert row['same_body_bitwise'];bitwise+=1
                    for col,mean in [('request_device_ms','device_interval_ms'),('request_ready_ms','operator_or_layer_ready_ms')]:
                        if col in row:assert math.isclose(sum(row[col])/len(row[col]),row[mean],rel_tol=1e-13)
                    phasecount+=1
                records.setdefault(m['key'].rsplit('_',1)[0],[]).append((m,p,d))
            raw.append(dict(worker=m['key'],case_id=d['case']['case_id'],path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
            for meta in d.get('metadata',{}).values():
                for adapter in ([meta['adapter']] if 'adapter' in meta else [meta[k] for k in ['up','down'] if k in meta]):binary.add(adapter['binary_sha256'])
    assert all(len(x)==1 for x in sources.values()),sources
    assert binary==sources['src/same_q_v2/libopf_grouped.so']
    assert len(records['sameq_v2_develop'])==36
    assert len(records['sameq_v2_diagnose'])==18
    assert len(records['sameq_v2_formal'])==(len(freeze['regression_ids'])+6)*6
    assert len(records['sameq_v2_layer'])==24
    assert len(records.get('sameq_v2_fusion',[])) in (0,12)
    assert len(records['sameq_v2_ring'])==6
    # Independently recompute every emitted central ratio from raw per-block logs.
    data=json.loads((RUN/'derived/analyses.json').read_text());maximum=0.;comparisons=0
    cohort={}
    for key,vals in records.items():
        for item in vals:
            d=item[2]
            name='development' if key.endswith('develop') else 'single_problem_diagnostic' if key.endswith('diagnose') else d['case']['split'] if key.endswith('formal') else 'layer_main' if key.endswith('layer') else 'layer_fusion' if key.endswith('fusion') else 'layer_ring'
            cohort.setdefault(name,[]).append(d)
    for name,modes in data.items():
        for mode,metrics in modes.items():
            for metric,result in metrics.items():
                for pair,reported in result['aggregate'].items():
                    a,b=pair.split('/');logs=[]
                    for d in cohort[name]:
                        vals={p['variant']:p[metric] for p in d['phases'] if p['phase_role']=='primary' and p.get('input_mode','STATIC')==mode}
                        for alias,original in d.get('aliases',{}).items():vals[alias]=vals[original]
                        if a in vals and b in vals:logs.append(math.log(vals[a]/vals[b]))
                    actual=math.exp(sum(logs)/len(logs));error=abs(actual-reported['ratio']);maximum=max(maximum,error);assert error<1e-12
                    comparisons+=1
    state=json.loads((RUN/'RUN_STATE.json').read_text());now=datetime.datetime.now(datetime.timezone.utc)
    end=datetime.datetime.fromisoformat(state['completed_at']) if state.get('completed_at') else now
    elapsed=(end-datetime.datetime.fromisoformat(state['started_at'])).total_seconds()+state.get('pre_record_reading_allowance_seconds',0)
    assert elapsed<420*60
    receipt=dict(status='PASS',checked_at=now.isoformat(),central_ratios_recomputed=comparisons,max_ratio_difference=maximum,
      all_measured_phase_count=phasecount,phase_numerical_summaries=numchecks,same_body_equality_phase_summaries=bitwise,
      source_versions={k:sorted(v) for k,v in sources.items()},old_prefix_sha256=hashlib.sha256(prefix).hexdigest(),
      wall_elapsed_seconds_at_audit=elapsed,new_worker_seconds=sum(m['worker_occupied_s'] for m in new),
      total_worker_seconds=sum(m['worker_occupied_s'] for m in rows),scope='CPU raw-summary recomputation and source/accounting audit, not independent tensor reproduction')
    (RUN/'reports/DELIVERY_AUDIT.json').write_text(json.dumps(receipt,indent=2)+'\n')
    (RUN/'RAW_INDEX.json').write_text(json.dumps(raw,indent=2)+'\n')
    run_index=[]
    for m in new:
        folder=ROOT/m['path']
        run_index.append(dict(worker=m['key'],run_id=m['run_id'],status=m['status'],worker_seconds=m['worker_occupied_s'],
          files=[dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size)
            for p in sorted(folder.rglob('*')) if p.is_file() and 'frozen' not in p.relative_to(folder).parts]))
    (RUN/'RUN_INDEX.json').write_text(json.dumps(run_index,indent=2)+'\n')
    print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
