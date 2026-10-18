// Read-only capability query. GPU builds/runs were NOT performed in the authoring environment.
// Example (use the locally supported architecture):
// nvcc -O2 -std=c++17 -arch=sm_75 device_probe.cu -o device_probe
#include <cuda_runtime.h>
#include <iostream>
#include <iomanip>
#include <sstream>
#include <string>
#include <stdexcept>
static void ck(cudaError_t e, const char* w) {
    if(e != cudaSuccess) throw std::runtime_error(std::string(w)+": "+cudaGetErrorString(e));
}
static std::string quote(const std::string& x) {
    std::ostringstream o; o << '"';
    for(unsigned char c: x) {
        if(c=='"' || c=='\\') o << '\\' << char(c);
        else if(c>=32 && c<127) o << char(c);
        else o << "\\u" << std::hex << std::setw(4) << std::setfill('0') << int(c) << std::dec;
    }
    o << '"'; return o.str();
}
int main(int argc,char** argv) {
 try {
    int d=argc>1?std::stoi(argv[1]):0, count=0;
    ck(cudaGetDeviceCount(&count),"cudaGetDeviceCount");
    if(d<0||d>=count)throw std::runtime_error("device index out of range");
    ck(cudaSetDevice(d),"cudaSetDevice");
    cudaDeviceProp p{};ck(cudaGetDeviceProperties(&p,d),"cudaGetDeviceProperties");
    int drv=0,rt=0,coop=0;ck(cudaDriverGetVersion(&drv),"driver version");ck(cudaRuntimeGetVersion(&rt),"runtime version");
    cudaError_t ce=cudaDeviceGetAttribute(&coop,cudaDevAttrCooperativeLaunch,d);
    int cluster=-1;cudaError_t cl=cudaErrorNotSupported;
#if CUDART_VERSION >= 12000
    cl=cudaDeviceGetAttribute(&cluster,cudaDevAttrClusterLaunch,d);
#endif
    size_t free_b=0,total_b=0;cudaError_t me=cudaMemGetInfo(&free_b,&total_b);
    std::cout<<"{\n  \"name\": "<<quote(p.name)<<",\n"
      <<"  \"device_index\": "<<d<<",\n  \"cc_major\": "<<p.major<<",\n  \"cc_minor\": "<<p.minor
      <<",\n  \"sm_count\": "<<p.multiProcessorCount<<",\n  \"l2_bytes\": "<<p.l2CacheSize
      <<",\n  \"global_bytes\": "<<p.totalGlobalMem<<",\n  \"shared_per_sm\": "<<p.sharedMemPerMultiprocessor
      <<",\n  \"max_threads_per_sm\": "<<p.maxThreadsPerMultiProcessor
      <<",\n  \"driver_api_version\": "<<drv<<",\n  \"runtime_version\": "<<rt
      <<",\n  \"compiled_headers\": "<<CUDART_VERSION
      <<",\n  \"cooperative_launch\": "<<(ce==cudaSuccess?std::to_string(coop):"null")
      <<",\n  \"cluster_launch\": "<<(cl==cudaSuccess?std::to_string(cluster):"null")
      <<",\n  \"cluster_query_status\": "<<quote(cudaGetErrorString(cl))
      <<",\n  \"free_bytes_snapshot\": "<<(me==cudaSuccess?std::to_string(free_b):"null")
      <<",\n  \"total_bytes_meminfo\": "<<(me==cudaSuccess?std::to_string(total_b):"null")
      <<",\n  \"gpu_kernel_executed\": false,\n  \"green_context_status\": \"NOT_PROBED\",\n"
      <<"  \"note\": \"snapshot only; not proof of isolation, topology, or performance\"\n}\n";
    return 0;
 }catch(const std::exception& e){std::cerr<<e.what()<<"\n";return 2;}
}
