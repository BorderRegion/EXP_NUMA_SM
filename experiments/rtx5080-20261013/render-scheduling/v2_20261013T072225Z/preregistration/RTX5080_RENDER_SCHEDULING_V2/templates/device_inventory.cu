// Optional local inventory template; NOT compiled or GPU-tested by the task author.
// Uses the installed CUDA runtime. No network, allocation stress, or configuration writes.
// Build with a locally supported target; inspect `nvcc --list-gpu-code` first.
#include <cuda_runtime.h>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

static void check(cudaError_t status, const char* operation) {
    if (status != cudaSuccess)
        throw std::runtime_error(std::string(operation) + ": " + cudaGetErrorString(status));
}
static std::string quote(const std::string& value) {
    std::ostringstream out;
    out << '"';
    for (unsigned char c : value) {
        if (c == '"' || c == '\\') out << '\\' << c;
        else if (c == '\n') out << "\\n";
        else if (c == '\r') out << "\\r";
        else if (c == '\t') out << "\\t";
        else if (c < 0x20) out << '?';
        else out << c;
    }
    out << '"';
    return out.str();
}
int main(int argc, char** argv) {
    try {
        int count = 0, driver = 0, runtime = 0;
        check(cudaGetDeviceCount(&count), "cudaGetDeviceCount");
        if (count <= 0) throw std::runtime_error("No CUDA device visible.");
        if (argc > 2) throw std::runtime_error("Usage: device_inventory [device_ordinal]");
        int device = 0;
        if (argc == 2) {
            std::size_t pos = 0;
            const std::string text(argv[1]);
            device = std::stoi(text, &pos);
            if (pos != text.size()) throw std::runtime_error("Invalid device ordinal.");
        }
        if (device < 0 || device >= count) throw std::runtime_error("Device ordinal out of range.");
        check(cudaSetDevice(device), "cudaSetDevice");
        cudaDeviceProp prop{};
        check(cudaGetDeviceProperties(&prop, device), "cudaGetDeviceProperties");
        check(cudaDriverGetVersion(&driver), "cudaDriverGetVersion");
        check(cudaRuntimeGetVersion(&runtime), "cudaRuntimeGetVersion");
        // Memory query can initialize a context; record this as inventory/setup, not benchmark data.
        size_t free_bytes = 0, total_bytes = 0;
        check(cudaMemGetInfo(&free_bytes, &total_bytes), "cudaMemGetInfo");
        std::cout << "{\n"
            << "  \"device_ordinal\": " << device << ",\n"
            << "  \"name\": " << quote(prop.name) << ",\n"
            << "  \"compute_major\": " << prop.major << ",\n"
            << "  \"compute_minor\": " << prop.minor << ",\n"
            << "  \"multiprocessor_count\": " << prop.multiProcessorCount << ",\n"
            << "  \"l2_bytes\": " << prop.l2CacheSize << ",\n"
            << "  \"total_global_bytes\": " << prop.totalGlobalMem << ",\n"
            << "  \"context_visible_total_bytes\": " << total_bytes << ",\n"
            << "  \"free_bytes_snapshot\": " << free_bytes << ",\n"
            << "  \"shared_bytes_per_sm\": " << prop.sharedMemPerMultiprocessor << ",\n"
            << "  \"shared_bytes_per_block\": " << prop.sharedMemPerBlock << ",\n"
            << "  \"max_threads_per_sm\": " << prop.maxThreadsPerMultiProcessor << ",\n"
            << "  \"warp_size\": " << prop.warpSize << ",\n"
            << "  \"kernel_timeout_enabled\": " << prop.kernelExecTimeoutEnabled << ",\n"
            << "  \"driver_api_version\": " << driver << ",\n"
            << "  \"runtime_api_version\": " << runtime << ",\n"
            << "  \"locality_domain_count\": null,\n"
            << "  \"locality_api_status\": \"NOT_CHECKED_BY_THIS_TEMPLATE\",\n"
            << "  \"application_benchmark_executed\": false\n"
            << "}\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "inventory_error: " << e.what() << '\n';
        return 2;
    }
}
