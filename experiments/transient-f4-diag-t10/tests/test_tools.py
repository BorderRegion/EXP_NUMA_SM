import unittest,sys,json,tempfile,math,csv
from pathlib import Path
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'tools'))
from analyze_focus import quartet,decomposition,trace_account,geomean,analyze
from extract_prior_focus import extract
class Tests(unittest.TestCase):
 def test_aa_equal(self):self.assertAlmostEqual(quartet('ABBA',[3]*4)['B_over_A'],1)
 def test_middle_invariant(self):
  a=quartet('ABBA',[1,2,2,1]);b=quartet('BAAB',[1,2,2,1]);self.assertEqual(a['middle_over_outer'],b['middle_over_outer']);self.assertAlmostEqual(a['B_over_A']*b['B_over_A'],1)
 def test_bad_labels(self):
  with self.assertRaises(ValueError):quartet('AAAA',[1]*4)
 def test_bad_time(self):
  with self.assertRaises(ValueError):geomean([1,float('nan')])
 def test_decomposition(self):
  x=decomposition(0,1000,3000,7000,8000);self.assertEqual(x['ready_us'],x['context_us']+x['launch_us']+x['wait_us']);self.assertEqual(x['event_read_us'],1)
 def test_nonmonotonic(self):
  with self.assertRaises(ValueError):decomposition(0,2,1,4,5)
 def test_trace_closure(self):
  x=trace_account(20,[dict(request=0,case_id='a',cpu_ready_us=5,gpu_us=4),dict(request=1,case_id='b',cpu_ready_us=12,gpu_us=10)])
  self.assertEqual(x['other_host_intervals_us'],3);self.assertEqual(x['requests'],2)
 def test_duplicate_request(self):
  with self.assertRaises(ValueError):trace_account(20,[dict(request=0,case_id='a',cpu_ready_us=5)]*2)
 def test_trace_signed_residual_preserved(self):self.assertEqual(trace_account(3,[dict(request=0,case_id='a',cpu_ready_us=5)])['other_host_intervals_us'],-2)
 def test_budget(self):
  c=json.loads((R/'campaign.json').read_text());self.assertEqual(sum(x['wall_minutes'] for x in c['stages']),510);self.assertEqual(sum(x['gpu_worker_minutes'] for x in c['stages']),85);self.assertLess(sum(c['historical_reported_used_minutes'])+85,330)
 def test_plan_ids(self):
  e=json.loads((R/'plans/episodes.json').read_text());self.assertEqual(len(e),len({x['id'] for x in e}));self.assertTrue(all(x['status']=='NOT_RUN' for x in e))
 def test_plan_counts(self):
  from collections import Counter
  e=json.loads((R/'plans/episodes.json').read_text());a=Counter(x['kind'] for x in e);self.assertEqual(dict(a),json.loads((R/'plans/COUNTS.json').read_text())['by_kind']);self.assertEqual(a['aa_factor'],48);self.assertEqual(a['trace'],36);self.assertEqual(a['aa_independent'],16)
 def test_focus_shapes(self):
  c={x['id']:x for x in json.loads((R/'plans/focus_cases.json').read_text())['cases']};self.assertEqual(tuple(c['V16'][k] for k in ['M','N','K']),(224,7168,20480))
 def test_trace_same_multiset(self):
  from collections import Counter
  t=json.loads((R/'plans/inherited_traces.json').read_text())['signatures'];self.assertEqual(Counter(t['MIX_ALL16']),Counter(t['BURST_ALL16']));self.assertEqual(len(t['MIX_ALL16']),128)
 def test_extractor(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);raw=p/'run/raw/S4_0';raw.mkdir(parents=True);win=[dict(label=l,mean_cpu_us=t,samples=[[0,t]]) for l,t in zip('ABBA',[1,2,2,1])]
   (raw/'anchors.jsonl').write_text(json.dumps(dict(case_id='R_G017',block=0,anchor='BEGIN',quartet_id='x',windows=win))+'\n')
   o=extract(p/'run',p/'out');self.assertEqual(o['counts']['anchor_rows'],1);self.assertEqual(o['aa_from_explicit_raw'][0]['middle_over_outer'],2)
 def test_missing_run(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):extract(Path(d)/'missing',Path(d)/'out')
 def test_analyzer_missing_gpu(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'a.csv'
   with p.open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=['episode_id','process_block','case_id','phase','window','label','input_slot','cpu_ready_us','gpu_span_us']);w.writeheader()
    for i,(l,t) in enumerate(zip('ABBA',[1,2,2,1])):w.writerow(dict(episode_id='e',process_block=0,case_id='c',phase='measure',window=i,label=l,input_slot=0,cpu_ready_us=t,gpu_span_us=''))
   x=analyze(p)['episodes'][0]['quartets'][0];self.assertEqual(x['cpu']['middle_over_outer'],2);self.assertIsNone(x['gpu'])
if __name__=='__main__':unittest.main()
