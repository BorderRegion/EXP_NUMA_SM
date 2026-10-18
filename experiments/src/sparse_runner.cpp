#include "driver_backend.hpp"
#include <cusparse.h>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <filesystem>
#include <map>
#include <algorithm>
#include <numeric>
#include <memory>
#include <cstring>
static void sp(cusparseStatus_t e,const char*s){if(e!=CUSPARSE_STATUS_SUCCESS)throw std::runtime_error(std::string(s)+": "+cusparseGetErrorString(e));}
static void read(std::ifstream&f,void*p,size_t n){if(!f.read((char*)p,n))throw std::runtime_error("truncated CSR");}
int main(int argc,char**argv){try{
 std::map<std::string,std::string>a;for(int i=1;i+1<argc;i+=2)a[argv[i]]=argv[i+1];auto get=[&](std::string k,std::string d){return a.count(k)?a[k]:d;};std::string input=get("--input",""),out=get("--out","."),plans_dir=get("--plans",""),purpose=get("--purpose","formal"),policies=get("--policies","NRM");int seq=std::stoi(get("--sequence","0"));bool native_library=get("--native-backend","row")=="cusparse";
 std::filesystem::create_directories(out);auto start=Clock::now();Backend b(1);unsigned n,nz;std::ifstream f(input,std::ios::binary);read(f,&n,4);read(f,&nz,4);std::vector<int>row(n+1),col(nz);read(f,row.data(),row.size()*4);read(f,col.data(),col.size()*4);
 unsigned maxdegree=0;for(unsigned i=0;i<n;i++){if(row[i]>row[i+1])throw std::runtime_error("bad CSR row");maxdegree=std::max(maxdegree,unsigned(row[i+1]-row[i]));}if(row[n]!=int(nz)||maxdegree*31>=16777216)throw std::runtime_error("exact integer float contract invalid");
 int rpt=std::max(4,int((n+4095)/4096));rpt=(rpt+3)/4*4;int tasks=(n+rpt-1)/rpt;
 Buffer dr(row.size()*4),dc(col.size()*4),dx(n*4),dy(n*4),dv(nz*4),visits(n*4),partial(256*8);dr.upload(row.data());dc.upload(col.data());std::vector<float>ones(nz,1);dv.upload(ones.data());
 CUmodule module;ck(cuModuleLoad(&module,get("--cubin","build/current/sparse.cubin").c_str()),"sparse module");CUfunction kernel,vec,digest;ck(cuModuleGetFunction(&kernel,module,"spmv_rows"),"row kernel");ck(cuModuleGetFunction(&vec,module,"vector_input"),"vector kernel");ck(cuModuleGetFunction(&digest,module,"sparse_digest"),"digest kernel");int occ;ck(cuOccupancyMaxActiveBlocksPerMultiprocessor(&occ,kernel,128,0),"occupancy");
 cusparseHandle_t handle;sp(cusparseCreate(&handle),"cusparse create");cusparseSpMatDescr_t mat;cusparseDnVecDescr_t vx,vy;sp(cusparseCreateCsr(&mat,n,n,nz,(void*)dr.p,(void*)dc.p,(void*)dv.p,CUSPARSE_INDEX_32I,CUSPARSE_INDEX_32I,CUSPARSE_INDEX_BASE_ZERO,CUDA_R_32F),"csr descriptor");sp(cusparseCreateDnVec(&vx,n,(void*)dx.p,CUDA_R_32F),"x descriptor");sp(cusparseCreateDnVec(&vy,n,(void*)dy.p,CUDA_R_32F),"y descriptor");float alpha=1,beta=0;size_t ws=0;sp(cusparseSpMV_bufferSize(handle,CUSPARSE_OPERATION_NON_TRANSPOSE,&alpha,mat,vx,&beta,vy,CUDA_R_32F,CUSPARSE_SPMV_ALG_DEFAULT,&ws),"cusparse workspace");Buffer workspace(std::max(ws,size_t(4)));int version;sp(cusparseGetVersion(handle,&version),"cusparse version");
 CUevent begin,end;ck(cuEventCreate(&begin,0),"begin event");ck(cuEventCreate(&end,0),"end event");
 std::vector<std::vector<float>>reference(32,std::vector<float>(n));std::vector<uint64_t>reference_hash(32);for(unsigned seed=0;seed<32;seed++){for(unsigned r=0;r<n;r++){unsigned sum=0;for(int j=row[r];j<row[r+1];j++)sum+=(unsigned(col[j])*1664525u+seed*1013904223u)%32;reference[seed][r]=float(sum);}uint64_t hash=0;for(unsigned r=0;r<n;r++){unsigned v;memcpy(&v,&reference[seed][r],4);hash+=uint64_t(v)*(r+1);}reference_hash[seed]=hash;}
 std::vector<std::vector<int>>lists(2);std::vector<std::unique_ptr<Buffer>>maps;std::ofstream initlog(out+"/init_costs.csv");initlog<<"policy,plan_load_upload_ms,plan_bytes\n";
 auto load_plan=[&](char policy){auto t=Clock::now();ck(cuCtxSetCurrent(b.primary),"plan context");maps.clear();lists.assign(2,{});std::vector<int>assignment(tasks);if(plans_dir.empty()){for(int t=0;t<tasks;t++)assignment[t]=t%2;}else{std::ifstream p(plans_dir+"/"+std::string(1,policy)+".txt");for(int&t:assignment)if(!(p>>t)||t<0||t>1)throw std::runtime_error("invalid CSR plan");}for(int t=0;t<tasks;t++)lists[assignment[t]].push_back(t);for(auto&l:lists){maps.emplace_back(new Buffer(std::max(size_t(4),l.size()*4)));if(!l.empty())ck(cuMemcpyHtoD(maps.back()->p,l.data(),l.size()*4),"CSR map upload");}initlog<<policy<<','<<ms(t,Clock::now())<<','<<tasks*4<<'\n';};
 auto seed_input=[&](unsigned seed){ck(cuCtxSetCurrent(b.primary),"input primary");void*args[]={&dx.p,&n,&seed};ck(cuLaunchKernel(vec,128,1,1,256,1,1,0,nullptr,args,nullptr),"input launch");};
 std::vector<float>gtime(2);auto launch=[&](int g,CUdeviceptr table,int count,int row_task,bool native,CUdeviceptr diag){b.current(g);int ni=n,flag=native?1:0;void*args[]={&dr.p,&dc.p,&dx.p,&dy.p,&ni,&table,&count,&row_task,&flag,&diag};ck(cuEventRecord(b.groups[g].start,b.groups[g].stream),"start");if(count)ck(cuLaunchKernel(kernel,native?count:std::min(count,b.groups[g].sms*occ),1,1,128,1,1,0,b.groups[g].stream,args,nullptr),"CSR launch");ck(cuEventRecord(b.groups[g].end,b.groups[g].stream),"end");};
 auto execute=[&](char policy,unsigned seed,bool diagnose){auto t=Clock::now();ck(cuCtxSetCurrent(b.primary),"primary");ck(cuEventRecord(begin,nullptr),"pipeline begin");seed_input(seed);int ni=n;CUdeviceptr diag=diagnose?visits.p:0;
  if(policy=='N'&&!native_library){int count=(n+3)/4,row_task=4,flag=1;CUdeviceptr table=0;void*args[]={&dr.p,&dc.p,&dx.p,&dy.p,&ni,&table,&count,&row_task,&flag,&diag};ck(cuLaunchKernel(kernel,count,1,1,128,1,1,0,nullptr,args,nullptr),"native row launch");}
  else if(policy=='B'||(policy=='N'&&native_library)){sp(cusparseSpMV(handle,CUSPARSE_OPERATION_NON_TRANSPOSE,&alpha,mat,vx,&beta,vy,CUDA_R_32F,CUSPARSE_SPMV_ALG_DEFAULT,(void*)workspace.p),"cusparse SpMV");}
  else{ck(cuCtxSynchronize(),"input readiness");for(int g=0;g<2;g++)launch(g,maps[g]->p,lists[g].size(),rpt,false,diag);b.join();for(int g=0;g<2;g++)ck(cuEventElapsedTime(&gtime[g],b.groups[g].start,b.groups[g].end),"group time");}
  ck(cuCtxSetCurrent(b.primary),"finish primary");ck(cuEventRecord(end,nullptr),"pipeline end");ck(cuEventSynchronize(end),"pipeline ready");double cpu=ms(t,Clock::now());float gpu;ck(cuEventElapsedTime(&gpu,begin,end),"gpu elapsed");return std::pair<double,float>(cpu,gpu);
 };
 auto screen=[&](){ck(cuCtxSetCurrent(b.primary),"screen context");void*args[]={&dy.p,&partial.p,&n};ck(cuLaunchKernel(digest,256,1,1,256,1,1,0,nullptr,args,nullptr),"screen");uint64_t p[256];partial.download(p);return std::accumulate(p,p+256,uint64_t(0));};
 auto full=[&](unsigned seed){std::vector<float>y(n);dy.download(y.data());if(memcmp(y.data(),reference[seed%32].data(),n*4)){std::ofstream bad(out+"/FAILED_output.bin",std::ios::binary);bad.write((char*)y.data(),n*4);throw std::runtime_error("full CSR bitwise mismatch");}return y;};
 std::ofstream frames(out+"/frames.csv"),groups(out+"/groups.csv");frames<<"policy,frame,request_seed,cpu_ready_ms,gpu_pipeline_ms,digest,planner_calls,plan_D2H_bytes,plan_H2D_bytes,recompile_count\n";groups<<"policy,frame,group,tasks,gpu_ms\n";frames<<std::setprecision(10);
 if(purpose=="calibrate"){
  std::vector<int>classes(tasks);std::vector<double>weights(tasks);std::ifstream cfile(get("--classes","").c_str());for(int t=0;t<tasks;t++)if(!(cfile>>classes[t]>>weights[t]))throw std::runtime_error("classes file");
  seed_input(17);ck(cuCtxSynchronize(),"calibration input ready");std::ofstream c(out+"/calibration.csv");c<<"class,mode,group,tasks,work,gpu_ms\n";
  for(int cl=0;cl<3;cl++){maps.clear();lists.assign(2,{});int rank=0;for(int t=0;t<tasks;t++)if(classes[t]==cl)lists[(rank++)%2].push_back(t);for(auto&l:lists){maps.emplace_back(new Buffer(std::max(size_t(4),l.size()*4)));if(!l.empty())ck(cuMemcpyHtoD(maps.back()->p,l.data(),l.size()*4),"cal map");}
   for(int concurrent=0;concurrent<2;concurrent++)for(int e=-32;e<128;e++){for(int g=0;g<2;g++){launch(g,maps[g]->p,lists[g].size(),rpt,false,0);if(!concurrent)ck(cuStreamSynchronize(b.groups[g].stream),"isolated CSR");}b.join();if(e>=0)for(int g=0;g<2;g++){float elapsed;ck(cuEventElapsedTime(&elapsed,b.groups[g].start,b.groups[g].end),"cal elapsed");double work=0;for(int t:lists[g])work+=weights[t];c<<cl<<','<<(concurrent?"concurrent":"isolated")<<','<<g<<','<<lists[g].size()<<','<<work<<','<<elapsed<<'\n';}}
  }
 }else{
  int epochs=std::stoi(get("--frames",purpose=="qualify"?"32":"512"));
  for(char policy:policies){if(policy==',')continue;if(policy!='N'&&policy!='B')load_plan(policy);
   ck(cuMemsetD32(visits.p,0,n),"visits clear");execute(policy,17,policy!='B'&&!(policy=='N'&&native_library));full(17);if(policy!='B'&&!(policy=='N'&&native_library)){std::vector<unsigned>v(n);visits.download(v.data());for(unsigned x:v)if(x!=1)throw std::runtime_error("CSR row exactly-once failed");}
   auto warm_start=Clock::now();int warm=0;do{execute(policy,(warm+seq*7)%32,false);warm++;}while(warm<128||ms(warm_start,Clock::now())<1000);
   for(int e=0;e<epochs;e++){unsigned seed=(e+seq*7)%32;auto ts=execute(policy,seed,false);uint64_t digest=screen();if(digest!=reference_hash[seed])throw std::runtime_error("CSR screen mismatch");if(purpose=="qualify"||e==epochs-1)full(seed);if(e==0||e==epochs/2||e==epochs-1){auto y=full(seed);std::ofstream f(out+"/"+std::string(1,policy)+"_frame_"+std::to_string(e)+".bin",std::ios::binary);f.write((char*)y.data(),n*4);}
    frames<<policy<<','<<e<<','<<seed<<','<<ts.first<<',';if(policy=='N'||policy=='B')frames<<ts.second;else frames<<"null";frames<<','<<digest<<",0,0,0,0\n";if(policy!='N'&&policy!='B')for(int g=0;g<2;g++)groups<<policy<<','<<e<<','<<g<<','<<lists[g].size()<<','<<gtime[g]<<'\n';
   }std::cout<<"SESSION_COMPLETE "<<policy<<" warmup="<<warm<<" measured="<<epochs<<std::endl;
  }
 }
 ck(cuCtxSetCurrent(b.primary),"cleanup");std::ofstream summary(out+"/summary.json");summary<<"{\"native_backend\":\""<<(native_library?"cusparse":"row")<<"\",\"status\":\"SUCCESS\",\"rows\":"<<n<<",\"nnz\":"<<nz<<",\"rows_per_task\":"<<rpt<<",\"tasks\":"<<tasks<<",\"occupancy\":"<<occ<<",\"cusparse_version\":"<<version<<",\"total_process_ms\":"<<ms(start,Clock::now())<<",\"scope\":\"REAL_INPUT_CSR_OPERATOR\"}\n";std::ofstream correctness(out+"/correctness.json");correctness<<"{\"status\":\"PASS\",\"contract\":\"exact_integer_valued_float; sum below 2^24; full CPU reference\"}\n";
 maps.clear();cusparseDestroySpMat(mat);cusparseDestroyDnVec(vx);cusparseDestroyDnVec(vy);cusparseDestroy(handle);cuEventDestroy(begin);cuEventDestroy(end);cuModuleUnload(module);return 0;
}catch(std::exception&e){std::cerr<<e.what()<<'\n';return 2;}}
