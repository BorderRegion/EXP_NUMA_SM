#include <algorithm>
#include <cmath>
#include <limits>
#include <vector>
static std::vector<int> hungarian(const std::vector<double>& c,int n){
 std::vector<double> u(n+1),v(n+1);std::vector<int> p(n+1),way(n+1);
 for(int i=1;i<=n;i++){
  p[0]=i;int j0=0;std::vector<double> minimum(n+1,std::numeric_limits<double>::infinity());std::vector<char> used(n+1);
  do{used[j0]=1;int i0=p[j0],j1=0;double delta=std::numeric_limits<double>::infinity();
   for(int j=1;j<=n;j++)if(!used[j]){double x=c[(i0-1)*n+j-1]-u[i0]-v[j];if(x<minimum[j]){minimum[j]=x;way[j]=j0;}if(minimum[j]<delta){delta=minimum[j];j1=j;}}
   for(int j=0;j<=n;j++)if(used[j]){u[p[j]]+=delta;v[j]-=delta;}else minimum[j]-=delta;
   j0=j1;
  }while(p[j0]);
  do{int j1=way[j0];p[j0]=p[j1];j0=j1;}while(j0);
 }
 std::vector<int>a(n);for(int j=1;j<=n;j++)if(p[j])a[p[j]-1]=j-1;return a;
}
extern "C" int fit_bottleneck(const double *cost,const unsigned char *allowed,int n,int *out){
 if(n<=0||n>64)return -1;
 std::vector<double> values,costs(cost,cost+n*n),bad(n*n);for(int i=0;i<n*n;i++){if(!std::isfinite(cost[i]))return -2;if(allowed[i])values.push_back(cost[i]);}
 if(values.empty())return -3;
 std::sort(values.begin(),values.end());values.erase(std::unique(values.begin(),values.end()),values.end());
 auto feasible=[&](int mid){for(int i=0;i<n*n;i++)bad[i]=!allowed[i]||cost[i]>values[mid];auto a=hungarian(bad,n);for(int i=0;i<n;i++)if(bad[i*n+a[i]])return false;return true;};
 if(!feasible(values.size()-1))return -4;
 int lo=0,hi=values.size()-1;while(lo<hi){int mid=(lo+hi)/2;if(feasible(mid))hi=mid;else lo=mid+1;}
 double penalty=(*std::max_element(costs.begin(),costs.end())-*std::min_element(costs.begin(),costs.end())+1)*(n+1);
 for(int i=0;i<n*n;i++)if(!allowed[i]||cost[i]>values[lo])costs[i]+=penalty;
 auto a=hungarian(costs,n);for(int i=0;i<n;i++){if(!allowed[i*n+a[i]]||cost[i*n+a[i]]>values[lo])return -5;out[i]=a[i];}return 0;
}
