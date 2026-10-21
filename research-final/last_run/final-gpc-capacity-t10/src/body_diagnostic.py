from range_runtime import *
folder=Path(os.environ['T10_WORKER_DIR']);c=Control();out=[]
for cid in ['A01','A02','A03','A04']:
 d=GQAData(shape(cid),212100+int(cid[1:]),0);old=NativePlan(c,d,True,'E56',True);new=RangePlan(c,d,True,[0],[dict(task_begin=0,task_count=d.B*d.HK*old.W)])
 qualify(old);qualify(new);warm(old);warm(new);vals=[]
 for label,p in [('OLD_DIRECT',old),('RANGE_DIRECT',new),('RANGE_DIRECT',new),('OLD_DIRECT',old)]:vals.append(dict(label=label,values=p.run(128).tolist()))
 out.append(dict(case=cid,kind='single diagnostic process, not confirmation/reselection',segments=vals,old_info=old.info,new_info=new.info));old.close();new.close();d.close()
write(folder/'BODY_DIAGNOSTIC.json',out);print('BODY_DIAGNOSTIC_PASS',flush=True)
