from tail_runtime import *
import sys
def run(out,sanitizer=False):
    verify_topology(out);w=Workspace();d=Data(PROTOCOL['V'],1290000000,w);checks=[];solver=[]
    # Finite-input cases cover flat distribution, a strong peak and extremes.
    d.source[1].zero_();d.source[2].fill_(-30);d.source[2][123]=30
    d.source[3]=torch.linspace(-80,80,d.V,device='cuda')
    for i in range(4):d.x[i].copy_(d.source[i]);d.refs[i]=torch.softmax(d.source[i].cpu().double(),dim=0)
    for scope in SCOPES:
        q=out/scope;q.mkdir();trace,delay,check=profile(d,scope);checks.append(dict(kind='profile',scope=scope,**check));np.save(q/'arrival.npy',trace)
        x=probe_batch(w,delay,2,1299000000);save_probe(q,'qualification',x)
        maps,scores=select(x['costs']);assert scores[maps['JOINT']]==scores.min();solver.append(dict(scope=scope,mapping=maps))
        job=SharedJob(d,0,scope);write(q/'graph.json',job.dag);write(q/'handles.json',job.identity)
        choices=list(range(len(CHOICES))) if not sanitizer else [0,IDENTITY,10,33,65,98,131]
        for slot in range(4):
            if slot:job.close();job=SharedJob(d,slot,scope)
            for idx in choices:
                job.set(idx);job.run();checks.append(dict(kind='operator',scope=scope,slot=slot,choice=idx,**job.check()))
        job.close()
    # Trace the actual original kernel at extreme placements, with each topology family.
    for idx in [0,IDENTITY,10,33,65,98,131]:
        c=CHOICES[idx];schedule=(I*56)(*MAPS[NAMES.index(c['family'])]);a=(P*6)(d.x[0].data_ptr(),d.y.data_ptr(),w.flags.data_ptr()+c['offset']*4096,C.addressof(schedule),w.trace.data_ptr(),d.partial.data_ptr());args=(I*4)(d.V,1,c['page'],1)
        assert fast.sf_launch(a,args,torch.cuda.current_stream().cuda_stream)==0,fast.sf_error()
        torch.cuda.synchronize();tr=w.trace.cpu().numpy().reshape(56,2);assert np.array_equal(np.sort(tr[:,0]),np.arange(56)) and np.array_equal(tr[:,0],tr[:,1])
        checks.append(dict(kind='roster',choice=idx,**d.check(0,c['offset'])))
    write(out/'numerical.json',checks);write(out/'selection_checks.json',solver)
    write(out/'complete.json',dict(status='PASS',numerical_checks=len(checks),sanitizer=sanitizer));print('QUALIFICATION PASS',len(checks),flush=True)
if __name__=='__main__':run(Path(sys.argv[1]),len(sys.argv)>2)
