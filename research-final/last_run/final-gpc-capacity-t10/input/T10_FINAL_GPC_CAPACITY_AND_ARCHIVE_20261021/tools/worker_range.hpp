#pragma once
// CPU-testable coordinate reference only. Not a CUDA adapter or placement API.
#include <cstdint>
#include <stdexcept>
struct LogicalTask {
  std::int64_t task, batch, kv_head, worker;
};
inline LogicalTask decode_task(std::int64_t local, std::int64_t begin,
                               std::int64_t count, std::int64_t W, std::int64_t HK) {
  if (local < 0 || begin < 0 || local >= count || count <= 0 || W <= 0 || HK <= 0)
    throw std::invalid_argument("invalid logical task range");
  auto t = begin + local;
  auto h = t / W;
  return {t, h / HK, h % HK, t % W};
}
