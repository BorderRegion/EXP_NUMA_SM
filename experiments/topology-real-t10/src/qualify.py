from real_runtime import *
import sys
def run(out,san=False):
    verify_topology(out);w=Workspace();d=Data(PROTOCOL['V'],1510000000,w);checks=[]
    d.source[1].zero_();d.source[2].fill_(-30);d.source[2][123]=30;d.source[3]=torch.linspace(-80,80,d.V,device='cuda')
    for i in range(4):d.x[i].copy_(d.source[i]);d.refs[i]=torch.softmax(d.source[i].cpu().double(),dim=0)
    for scope in SCOPES:
        q=out/scope;q.mkdir()
        for slot in range(1 if san else 4):
            job=SharedJob(d,slot,scope)
            choices=CANDIDATES+[56] if not san else [11,54,56,112,120]
            for k in choices:job.set(k);job.run();checks.append(dict(scope=scope,slot=slot,choice=k,**job.check()))
            write(q/f'graph{slot}.json',job.dag)
            if not san:
                result=calibrate(job,q/f'calibration{slot}',1510010000+slot);checks.append(dict(scope=scope,slot=slot,kind='compiled_calibration',**job.check()))
                assert result['setup_ms']>0
            job.close()
    # Verify full baseline binary roster at representatives of all families.
    for k in [11,12,13,54,120]:
        c=CHOICES[k];schedule=(I*56)(*MAPS[k]);a=(P*6)(d.x[0].data_ptr(),d.y.data_ptr(),w.flags.data_ptr()+c['offset']*4096,C.addressof(schedule),w.trace.data_ptr(),d.partial.data_ptr());args=(I*4)(d.V,1,c['page'],1)
        assert fast.sf_launch(a,args,torch.cuda.current_stream().cuda_stream)==0,fast.sf_error();torch.cuda.synchronize()
        t=w.trace.cpu().numpy().reshape(56,2);assert np.array_equal(np.sort(t[:,0]),np.arange(56)) and np.array_equal(t[:,0],t[:,1])
        checks.append(dict(kind='roster',choice=k,**d.check(0,c['offset'])))
    write(out/'numerical.json',checks);write(out/'complete.json',dict(status='PASS',numerical_checks=len(checks),sanitizer=san));print('QUALIFICATION PASS',len(checks),flush=True)
if __name__=='__main__':run(Path(sys.argv[1]),len(sys.argv)>2)
