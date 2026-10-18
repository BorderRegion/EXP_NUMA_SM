"""Supplementary full directed 56-SM survey; never feeds learned schedules."""
from runtime import *
import sys
def run(out,process):
    verify_topology(out);w=Workspace();rng=np.random.default_rng(810000000+process)
    warm=[[1,0,1,17+i,2*i,2*i+1,128,0,0] for i in range(28)]
    w.micro(warm,out,'conditioning')
    plans=[]
    for rd in range(2):
        part=[[1,rd,1,page+src//2,src,dst,128,0,0] for page in PAGES for src in range(56) for dst in range(56) if src!=dst]
        rng.shuffle(part);plans.extend(part)
    r,info=w.micro(plans,out,'full_direction')
    write(out/'complete.json',dict(**info,process=process,
          survey_note='Both directions/all SM parities; every source retains a TPC-index-owned mailbox. No mapping fitting or operator tuning.'))
if __name__=='__main__':run(Path(sys.argv[1]),int(sys.argv[2]))
