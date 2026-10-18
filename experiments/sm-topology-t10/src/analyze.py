"""CPU-only derivation and audit. Can run on an independently extracted archive."""
from pathlib import Path
import argparse,json,hashlib,csv,numpy as np
from analysis_lib import *
def dump(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def gm(a):return float(np.exp(np.mean(np.log(a))))
def gains(logratios):
 a=np.asarray(logratios);return dict(gain_percent=float(100*(1-np.exp(a.mean()))),block_gain_percent=(100*(1-np.exp(a))).tolist(),block_min_gain_percent=float(np.min(100*(1-np.exp(a)))),block_max_gain_percent=float(np.max(100*(1-np.exp(a)))),positive_blocks=int(np.sum(a<0)),processes=len(a))
def analyze(root,out):
 runs=sorted((root/'runs').iterdir());assert len(runs)==1;run=runs[0];out.mkdir(parents=True,exist_ok=True)
 rule=json.loads((root/'freeze/MAPPING.json').read_text());v2=json.loads((root/'freeze/PROTOCOL_V2.json').read_text())
 ps=[];cs=[]
 for b in range(6):
  p,c,ids=matrices(run/'raw'/f'matrix_{b}');ps.append(p);cs.append(c)
 P={u:np.stack([p[u] for p in ps]) for u in ['ns','cycles']};C={u:np.stack([c[u] for c in cs]) for u in ['ns','cycles']};off=~np.eye(56,dtype=bool)
 np.savez_compressed(out/'matrices.npz',**{f'pair_{u}':v for u,v in P.items()},**{f'chase_{u}':v for u,v in C.items()},sm_ids=ids)
 result=dict(scope='Tesla T10 empirical source-clock communication and SM/address affinity; not physical wiring',roster=ids,matrix_processes=6,matrix_launches=6*51968,mode_names=['notification','payload64B'],address_mode_names=['warm_cg','warm_ca'],stability=[],matrix_distributions=[],address_class_interaction=[],mapping_predictions=[],v1=[],v2=[],edges=[])
 rowcol=[]
 for unit in ['ns','cycles']:
  for mode in [0,1]:
   block=[np.log(P[unit][b,:,mode]).mean(axis=(0,1)) for b in range(6)];res=[residual(a,True) for a in block];adr=[residual(np.log(C[unit][b,:,mode]).mean(axis=0)) for b in range(6)]
   dev=np.mean(res[:2],axis=0);devaddr=np.mean(adr[:2],axis=0)
   for stage,bs in [('v1_confirmation',[2,3]),('fresh_v2_confirmation',[4,5])]:
    test=np.mean([res[b] for b in bs],axis=0);testaddr=np.mean([adr[b] for b in bs],axis=0)
    result['stability'].append(dict(unit=unit,mode=mode,stage=stage,pair_row_column_residual_correlation=corr(dev,test),address_row_column_residual_correlation=corr(devaddr,testaddr),pair_between_confirmation_correlation=corr(res[bs[0]],res[bs[1]]),address_between_confirmation_correlation=corr(adr[bs[0]],adr[bs[1]])))
   for b in range(6):
    a=np.exp(block[b]);aa=np.exp(np.log(C[unit][b,:,mode]).mean(axis=0))
    result['matrix_distributions'].append(dict(block=b,unit=unit,mode=mode,pair_offdiag_quantile_levels=[0,5,25,50,75,95,100],pair_offdiag_quantiles=np.percentile(a[off],[0,5,25,50,75,95,100]).tolist(),same_CTA_diagonal_median=float(np.median(a.diagonal())),chase_step_quantiles=np.percentile(aa,[0,5,25,50,75,95,100]).tolist(),pair_dev_residual_correlation=corr(dev,res[b])))
    rowcol.append(dict(block=b,unit=unit,mode=mode,total_log_variance=float(np.var(block[b][off])),residual_log_variance=float(np.var(res[b][off])),row_geomean=np.exp(np.mean(block[b],axis=1)).tolist(),column_geomean=np.exp(np.mean(block[b],axis=0)).tolist()))
   for slot in range(3):
    devslot=residual(np.log(P[unit][:2,:,mode,:2]).mean(axis=(0,1,2)),True);testslot=residual(np.log(P[unit][4:,:,mode,slot]).mean(axis=(0,1)),True)
    result['stability'].append(dict(unit=unit,mode=mode,stage='fresh_v2_address_slot',slot=slot,pair_row_column_residual_correlation=corr(devslot,testslot)))
 # Frozen address groups, paired with parity(region &0x33). No refitting on confirmations.
 group=[[ids.index(sm) for sm in g] for g in rule['address_exploratory_2groups']];classes=[[r for r in range(64) if (r&0x33).bit_count()%2==d] for d in [0,1]]
 for unit in ['ns','cycles']:
  for mode in [0,1]:
   for b in range(6):
    x=np.log(C[unit][b,:,mode]).mean(axis=0);cells=np.array([[x[np.ix_(g,cl)].mean() for cl in classes] for g in group]);interaction=(cells[0,0]+cells[1,1]-cells[0,1]-cells[1,0])/2
    result['address_class_interaction'].append(dict(block=b,unit=unit,mode=mode,cells_geomean=np.exp(cells).tolist(),matched_vs_reversed_gain_percent=float(100*(1-np.exp(-interaction))),scope='isolated dependent loads, not concurrent kernel speedup'))
 # Export every matrix, preserving coordinates and diagonal semantics.
 with (out/'pair_matrix.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['block','mode','slot','source_sm','destination_sm','same_CTA_diagonal','rtt_ns_geomean','rtt_cycles_geomean'])
  for b in range(6):
   for mode in [0,1]:
    for slot in range(3):
     for i,s in enumerate(ids):
      for j,d in enumerate(ids):w.writerow([b,mode,slot,s,d,int(s==d),gm(P['ns'][b,:,mode,slot,i,j]),gm(P['cycles'][b,:,mode,slot,i,j])])
 with (out/'address_matrix.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['block','cache_policy','sm','region','parity_0x33','ns_per_step_geomean','cycles_per_step_geomean'])
  for b in range(6):
   for mode in [0,1]:
    for i,s in enumerate(ids):
     for reg in range(64):w.writerow([b,['cg','ca'][mode],s,reg,(reg&0x33).bit_count()%2,gm(C['ns'][b,:,mode,i,reg]),gm(C['cycles'][b,:,mode,i,reg])])
 # Frozen mutual-top3 edges, no removal based on confirmation sign.
 for a,b in v2['mutual_top3_residual_edges']:
  vals=[]
  for bi in range(6):
   x=np.log(P['cycles'][bi,:,1]).mean(axis=(0,1));rr=residual(x,True);vals.append(float(100*np.expm1((rr[a,b]+rr[b,a])/2)))
  result['edges'].append(dict(sm_a=a,sm_b=b,block_symmetric_residual_percent=vals,new_confirmation_mean_percent=float(np.mean(vals[4:])),note='Negative = faster than row/column-adjusted expectation; not physical adjacency'))
 for version,rulemaps in [('v1',rule['maps']),('v2',v2['maps'])]:
  for b in range(6):
   for unit in ['ns','cycles']:
    x=P[unit][b,:,1].mean(axis=(0,1))
    for name,pairs in rulemaps.items():
     v=np.array([x[ids.index(a),ids.index(b)] for a,b in pairs]);result['mapping_predictions'].append(dict(version=version,block=b,unit=unit,policy=name,isolated_mean=float(v.mean()),isolated_max=float(v.max())))
 deployments=[];loop_diagnostics=[]
 for version,blocks,policies in [('v1',4,rule['policy_order']),('v2',6,v2['policy_order'])]:
  all_ratios={};all_process={};all_loop_process={};primary=0 if version=='v1' else 2
  for b in range(blocks):
   folder=run/'raw'/(f'deploy_{b}' if version=='v1' else f'deploy_v2_{b}')
   if not (folder/'records.bin').exists():folder=run/'raw'/f'deploy_v2_{b}_resume'
   e,r,_=load_worker(folder);assert len(e)==(152 if version=='v1' else 450)
   ratios={};loop_ratios={};max_loop_us=np.array([np.max(r['ns'][o:o+28])/1000 for o in e['record_offset']])
   for steps in [128,512]:
    for slot in ([0] if version=='v1' else range(3)):
     values=[];loop_values=[]
     for pi,name in enumerate(policies):
      mask=(e['steps']==steps)&(e['slot']==slot)&(e['policy']==pi)&(e['round']>=0);selected=e[mask];assert len(selected)==(16 if version=='v1' else 12)
      val=gm(selected['event_us']);values.append(val);loop_values.append(gm(max_loop_us[mask]))
      deployments.append(dict(version=version,block=b,steps=steps,slot=slot,policy=name,event_us_geomean=val,event_us_min=float(selected['event_us'].min()),event_us_max=float(selected['event_us'].max()),longest_source_loop_us_geomean=loop_values[-1],samples=len(selected),warm_excluded_from_estimate_not_deleted=True))
     for pi,name in enumerate(policies):
      if pi==primary:continue
      contrast=policies[primary]+'/'+name;lr=float(np.log(values[primary]/values[pi]));ratios.setdefault(contrast,[]).append(lr);all_ratios.setdefault((contrast,steps,slot),[]).append(lr);loop_ratios.setdefault(contrast,[]).append(float(np.log(loop_values[primary]/loop_values[pi])))
   for contrast,rr in ratios.items():all_process.setdefault(contrast,[]).append(float(np.mean(rr)))
   for contrast,rr in loop_ratios.items():all_loop_process.setdefault(contrast,[]).append(float(np.mean(rr)))
  for contrast,vals in all_process.items():result[version].append(dict(contrast=contrast,scope='equal-weight mean of all frozen steps/slots within each independent process',**gains(vals)))
  for (contrast,steps,slot),vals in all_ratios.items():result[version].append(dict(contrast=contrast,steps=steps,slot=slot,scope='one frozen condition',**gains(vals)))
  for contrast,vals in all_loop_process.items():loop_diagnostics.append(dict(version=version,contrast=contrast,scope='Longest source-thread measured-loop duration, excludes16 in-kernel warm handshakes and initial barrier; diagnostic, not whole kernel makespan',**gains(vals)))
 result['loop_diagnostics']=loop_diagnostics
 audit=dict(status='PASS',successful_workers=[],failed_workers=[],not_started_workers=[],execution_sources_unchanged=True,source_checks=0,placement_launches_checked=0,records_checked=0,source_placement_checks=0,checksum_status_records_checked=0,actual_binary_bindings=[])
 for freeze in ['EXECUTION_SOURCES.json','V2_EXECUTION.json']:
  j=json.loads((root/'freeze'/freeze).read_text());sha_map=j.get('sha256',j.get('files',{}))
  for rel,want in sha_map.items():assert digest(root/rel)==want,(freeze,rel);audit['source_checks']+=1
 for folder in sorted((run/'raw').iterdir()):
  if (folder/'NOT_STARTED.json').exists():audit['not_started_workers'].append(folder.name);continue
  manifest=json.loads((folder/'manifest.json').read_text())
  if manifest['status']!='COMPLETED':audit['failed_workers'].append(dict(key=folder.name,returncode=manifest.get('returncode'),stderr=(folder/'stderr.log').read_text(),stdout=(folder/'stdout.log').read_text()));continue
  audit['successful_workers'].append(folder.name)
  cmd=manifest['command'];cubin=Path(cmd[cmd.index('--cubin')+1]);actualdir='build_v2' if 'build_v2' in cubin.parts else 'build'
  audit['actual_binary_bindings'].append(dict(key=folder.name,runner_relative=actualdir+'/runner',cubin_relative=actualdir+'/probe.cubin',runner_sha256=digest(root/actualdir/'runner'),cubin_sha256=digest(root/actualdir/'probe.cubin'),note='Actual command and frozen binary resolve v2; wrapper manifest binaries field is the original-build reference and is not v2 provenance.'))
  if not (folder/'epochs.csv').exists():continue
  e,r,_=load_worker(folder);audit['placement_launches_checked']+=len(e);audit['records_checked']+=len(r)
  starts={int(x['region']):int(x['index']) for x in csv.DictReader((folder/'chain_starts.csv').open())}
  mapname='frozen_maps_v2.txt' if '--maps' in cmd and 'frozen_maps_v2' in cmd[cmd.index('--maps')+1] else 'qualification_maps.txt' if '--maps' in cmd and 'qualification_maps' in cmd[cmd.index('--maps')+1] else 'frozen_maps.txt'
  allmap=[]
  if '--maps' in cmd:
   arr=list(map(int,(root/'plans'/mapname).read_text().split()));allmap=np.array(arr[1:]).reshape(arr[0],28,2)
  for row in e:
   rr=r[row['record_offset']:row['record_offset']+row['record_count']];assert (rr['ns']>0).all() and (rr['cycles']>0).all()
   if row['kind']==2:
    assert rr[0]['src_begin']==row['src'] and rr[0]['src_value']==starts[row['region']]
   else:
    assert np.all(rr['src_value']==row['steps']+16) and np.all(rr['dst_value']==row['steps']+16) and np.all(rr['dst_begin']==rr['dst_end'])
    if row['kind']==1:assert rr[0]['src_begin']==row['src'] and rr[0]['dst_begin']==row['dst']
    else:assert np.array_equal(np.stack([rr['src_begin'],rr['dst_begin']],axis=1),allmap[row['policy']])
   audit['source_placement_checks']+=len(rr);audit['checksum_status_records_checked']+=len(rr)
  if folder.name.startswith(('memcheck','synccheck')):
   text=(folder/'stdout.log').read_text()+(folder/'stderr.log').read_text();assert 'ERROR SUMMARY: 0 errors' in text
 ledger=[json.loads(l) for l in (run/'ledger.jsonl').read_text().splitlines()]
 telemetry=[]
 for folder in (run/'raw').iterdir():
  f=folder/'telemetry.jsonl'
  if f.exists():telemetry += [json.loads(l) for l in f.read_text().splitlines()]
 temperatures=[r['temperature_c']['value'] for r in telemetry if r['temperature_c']['value'] is not None];powers=[r['limit_mw']['value'] for r in telemetry if r['limit_mw']['value'] is not None]
 assert set(powers)=={100000} and max(temperatures)<82
 result['resources']=dict(gpu_worker_seconds=sum(r['worker_seconds'] for r in ledger),cap_seconds=900,temperatures_C=[min(temperatures),max(temperatures)],enforced_limit_W=100,new_downloads=False,admin_changes=False,desktop_client_present=True,clock_locked=False,raw_hardware_counters=False)
 cg=C['cycles'][:,:,0].mean(axis=1);parity=np.array([(r&0x33).bit_count()%2 for r in range(64)]);delta=cg[:,:,parity==1].mean(axis=2)-cg[:,:,parity==0].mean(axis=2);devsign=np.sign(delta[:2].mean(axis=0));preferred0=[ids[i] for i in np.where(devsign>0)[0]];preferred1=[ids[i] for i in np.where(devsign<0)[0]]
 result['address_preference']=dict(definition='Mean dependent-load cycles(class1)-cycles(class0), fixed old parity(region &0x33); sign learned from processes0,1 only',class0_preferred_sms=preferred0,class1_preferred_sms=preferred1,per_block_delta_cycles=delta.tolist(),per_block_sign_agreement_with_development=[int(np.sum(np.sign(x)==devsign)) for x in delta],natural_group_sizes=[len(preferred0),len(preferred1)],descriptive_short_rule='In this observed SM numbering only: SM%10 in {4,5,6,7} prefers class1; remaining observed IDs prefer class0',mod10_rule_matches=preferred1==[i for i in ids if i%10 in [4,5,6,7]],boundary='Descriptive coding of measured affinity, not GPC numbering, physical coordinate or physical-address home. These34/22 signed groups differ from the exploratory balanced28/28 SVD partition frozen earlier.',allocation_VAs=[json.loads((run/'raw'/f'matrix_{b}'/'environment.json').read_text()) for b in range(6)])
 result['address_groups']=rule['address_exploratory_2groups'];result['audit_summary']={k:audit[k] for k in ['status','source_checks','placement_launches_checked','records_checked','checksum_status_records_checked','failed_workers','not_started_workers']}
 dump(out/'RESULTS.json',result);dump(out/'AUDIT.json',audit);dump(out/'DEPLOYMENT_PHASES.json',deployments);dump(out/'ROW_COLUMN_COMPONENTS.json',rowcol)
 print(json.dumps(dict(resources=result['resources'],v1=[x for x in result['v1'] if 'steps' not in x],v2=[x for x in result['v2'] if 'steps' not in x],fresh_payload_cycle_stability=[x for x in result['stability'] if x['unit']=='cycles' and x['mode']==1 and x['stage']=='fresh_v2_confirmation'],audit=result['audit_summary']),indent=2))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1]);p.add_argument('--out',type=Path);a=p.parse_args();analyze(a.root,a.out or a.root/'derived')
