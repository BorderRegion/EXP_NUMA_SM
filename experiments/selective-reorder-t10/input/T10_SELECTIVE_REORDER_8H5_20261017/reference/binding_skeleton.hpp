#pragma once
// Backend-neutral host skeleton. It contains no CUDA implementation.
// Bind this to the locally qualified PC engine. Do not call make_plan per tile.
#include <memory>
#include <stdexcept>
namespace selective_binding {
enum class Action { Lib, Single, Split, Pc00, Pc01, Pc10, Pc11, Pc20, Pc21 };
inline bool is_placement(Action a) { return static_cast<int>(a)>=3; }
struct Plan {
  Action action;
  int partition; // meaningful only for placement
  virtual ~Plan()=default;
  // Must submit only: no allocation, calibration, host join or selector here.
  virtual void enqueue(const void* inputs, void* output)=0;
};
struct Factory {
  virtual ~Factory()=default;
  virtual std::unique_ptr<Plan> native_plan(Action)=0;
  // This is the only path allowed to create Green resources/PC workspace.
  virtual std::unique_ptr<Plan> placement_plan(Action)=0;
};
inline std::unique_ptr<Plan> bind(Action a,Factory& factory) {
  if(!is_placement(a)) return factory.native_plan(a);
  return factory.placement_plan(a);
}
} // namespace selective_binding
