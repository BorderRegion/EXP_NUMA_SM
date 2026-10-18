// CPU-only drop-in acceleration of the frozen deterministic Hungarian solver.
// No CUDA and no fast-math; the cost matrix is supplied by NumPy without recomputation.
#include <vector>
#include <limits>
extern "C" int ag_hungarian(const double*cost,int n,int m,int*answer){
 if(n<=0||n>m)return -1;
 std::vector<double>u(n+1),v(m+1);std::vector<int>p(m+1),way(m+1);
 for(int i=1;i<=n;i++){
  p[0]=i;int j0=0;std::vector<double>minimum(m+1,std::numeric_limits<double>::infinity());std::vector<bool>used(m+1,false);
  while(true){
   used[j0]=true;int i0=p[j0],j1=0;double delta=std::numeric_limits<double>::infinity();
   for(int j=1;j<=m;j++)if(!used[j]){
    double cur=cost[(i0-1)*m+j-1]-u[i0]-v[j];
    if(cur<minimum[j]){minimum[j]=cur;way[j]=j0;}
    if(minimum[j]<delta){delta=minimum[j];j1=j;}
   }
   for(int j=0;j<=m;j++){if(used[j]){u[p[j]]+=delta;v[j]-=delta;}else minimum[j]-=delta;}
   j0=j1;if(p[j0]==0)break;
  }
  while(true){int j1=way[j0];p[j0]=p[j1];j0=j1;if(j0==0)break;}
 }
 for(int j=1;j<=m;j++)if(p[j])answer[p[j]-1]=j-1;
 return 0;
}
