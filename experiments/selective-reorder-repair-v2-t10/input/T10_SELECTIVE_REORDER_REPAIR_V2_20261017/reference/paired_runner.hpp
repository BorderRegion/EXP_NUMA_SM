#pragma once
#include <array>
#include <cstddef>
#include <stdexcept>
#include <cmath>

// Host-only reference. Connect to already-prepared C++ CUDA plans.
// No CUDA compilation, graph setup, validation, disk I/O or policy fitting here.
namespace t10_pair {
struct Sample { double cpu_ready_us=0.; double gpu_span_us=0.; };
struct Plan {
    void* user=nullptr;
    Sample (*run_ready)(void*, unsigned input_slot)=nullptr;
};
struct Window {
    char label='A'; unsigned count=0;
    std::array<Sample,128> samples{};
};
struct Quartet { std::array<Window,4> windows{}; };
inline Quartet run(const Plan& a,const Plan& b,unsigned n,unsigned warm,unsigned ring,bool baab) {
    if (!a.run_ready || !b.run_ready || n<1 || n>128 || ring<1)
        throw std::invalid_argument("prepared callbacks and bounded request count required");
    Quartet out;
    const char* labels=baab?"BAAB":"ABBA";
    for(unsigned w=0;w<4;++w){
        Window& dest=out.windows[w];dest.label=labels[w];dest.count=n;
        const Plan& p=labels[w]=='A'?a:b;
        // Production adapter must not allocate/create graphs/check tensors in this callback.
        for(unsigned i=0;i<warm;++i)(void)p.run_ready(p.user,i%ring);
        for(unsigned i=0;i<n;++i){
            Sample x=p.run_ready(p.user,i%ring);
            if(!(x.cpu_ready_us>0.) || !(x.gpu_span_us>0.) || !std::isfinite(x.cpu_ready_us) || !std::isfinite(x.gpu_span_us))
                throw std::runtime_error("nonfinite timing");
            dest.samples[i]=x;
        }
    }
    return out; // fixed-size host storage; no heap allocation by this helper
}
}
