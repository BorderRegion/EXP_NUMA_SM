import pathlib,gzip,json,struct,hashlib,numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[1]
for name in ['ca-GrQc','web-Google']:
 p=ROOT/'assets/sparse'/(name+'.txt.gz')
 with gzip.open(p,'rt') as f:a=np.loadtxt(f,dtype=np.int64,comments='#')
 ids=np.unique(a);edges=np.searchsorted(ids,a);order=np.lexsort((edges[:,1],edges[:,0]));edges=edges[order];n=len(ids);nz=len(edges);counts=np.bincount(edges[:,0],minlength=n);ptr=np.r_[0,np.cumsum(counts)].astype('<i4');col=edges[:,1].astype('<i4')
 # No invented edges, duplication, or performance-based sampling. Preserve
 # all source records after deterministic node-ID compaction and row sorting.
 out=ROOT/'assets/prepared'/name;out.mkdir(parents=True,exist_ok=True)
 with open(out/'csr.bin','wb') as f:f.write(struct.pack('<II',n,nz));f.write(ptr.tobytes());f.write(col.tobytes())
 np.asarray(ids,dtype='<i8').tofile(out/'original_ids.bin')
 (out/'manifest.json').write_text(json.dumps(dict(name=name,rows=n,nnz=nz,max_degree=int(counts.max()),source=f'https://snap.stanford.edu/data/{name}.html',download_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),csr_sha256=hashlib.sha256((out/'csr.bin').read_bytes()).hexdigest(),operator='unweighted adjacency CSR gather; complete original graph',values='matrix all ones; integer-valued float vectors 0..31; exact sums below 2^24',program_source='NVIDIA CUDALibrarySamples cuSPARSE/spmv_csr; custom whole-row mapping adapter',program_scope='real-input standalone operator, not complete application'),indent=2))
 print(name,n,nz,int(counts.max()),flush=True)
