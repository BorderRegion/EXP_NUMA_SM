from worker import ROOT,run
for b in range(6):
 m=run('E4','E4_request_block_'+str(b),ROOT/'tools/request_layer_bench.py',['--block',b])
 if m['status']!='COMPLETED':raise SystemExit('Request-boundary worker failed')
