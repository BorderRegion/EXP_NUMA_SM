#pragma once
// CPU scheduling reference only. Caller supplies existing CUDA submission/wait
// operations. No CUDA implementation or timing claim is provided by this file.
#include <cstddef>
#include <cstdint>
#include <stdexcept>

namespace t10_diag {
enum class Condition { BurstSlot0, BurstRing4, ReadySlot0, ReadyRing4 };
inline std::uint32_t slot_for(Condition mode, std::uint64_t request,
                              std::uint32_t ring) {
  if (ring == 0) throw std::invalid_argument("ring must be nonzero");
  return (mode == Condition::BurstRing4 || mode == Condition::ReadyRing4)
             ? static_cast<std::uint32_t>(request % ring) : 0u;
}
// execute_condition_chunk must use one already selected/common stream for the
// asynchronous path. drain() waits for the whole finite chunk; ready(slot)
// performs the original request-completion contract. Do not feed one reused
// timing event to every asynchronous launch and report it as per-launch time.
template <class Enqueue, class Drain, class Ready>
void execute_condition_chunk(Condition mode, std::uint64_t& cursor,
                             std::size_t count, std::uint32_t ring,
                             Enqueue enqueue, Drain drain, Ready ready) {
  if (!count || !ring) throw std::invalid_argument("empty chunk or ring");
  const bool burst = mode == Condition::BurstSlot0 || mode == Condition::BurstRing4;
  for (std::size_t i = 0; i < count; ++i) {
    auto slot = slot_for(mode, cursor++, ring);
    if (burst) enqueue(slot); else ready(slot);
  }
  if (burst) drain();
}
struct Stamp {
  std::int64_t begin_ns{}, context_ready_ns{}, launch_return_ns{}, ready_ns{},
               event_read_end_ns{};
  bool ordered() const noexcept {
    return begin_ns <= context_ready_ns && context_ready_ns <= launch_return_ns &&
           launch_return_ns <= ready_ns && ready_ns <= event_read_end_ns;
  }
  double cpu_ready_us() const {
    if (!ordered()) throw std::invalid_argument("nonmonotonic request");
    return static_cast<double>(ready_ns-begin_ns)/1000.0;
  }
};
} // namespace t10_diag
