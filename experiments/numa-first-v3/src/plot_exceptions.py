import numpy as np,matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from common import *
r=runroot();out=r/'figures';out.mkdir(exist_ok=True);plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'savefig.dpi':170});fig,axes=plt.subplots(2,4,figsize=(15,8),sharex=True,sharey=True);cmap=plt.get_cmap('RdBu_r').copy();cmap.set_bad('#d6d6d6')
for col,allocation in enumerate(['confirm_2','confirm_3','confirm_4','confirm_5']):
 z=np.load(r/'raw'/allocation/'sm_address_evidence.npz');i=np.flatnonzero((z['keys']==[2097152,4096,1,0,2,2]).all(1))[0]
 for half in range(2):
  im=axes[half,col].imshow(z['residual'][i,half]*100,aspect='auto',cmap=cmap,vmin=-.8,vmax=.8);axes[half,col].set_title(allocation+(' early' if half==0 else ' late'));axes[half,col].set_xlabel('Original region ID');axes[half,col].set_ylabel('SM ID (unsorted)')
fig.suptitle('A retained positive exception: 2 MiB, sparse, cg repeat4, primer C1\nGray = unobserved; local residual stability alone does not identify physical NUMA',y=.99);fig.subplots_adjust(top=.86,bottom=.12,wspace=.15,hspace=.3,right=.92);cax=fig.add_axes([.94,.2,.012,.55]);fig.colorbar(im,cax=cax,label='100 x log-cycle residual');fig.savefig(out/'small_sparse_sm_exception.png',bbox_inches='tight');fig.savefig(out/'small_sparse_sm_exception.pdf',bbox_inches='tight');print('saved exception figure')
