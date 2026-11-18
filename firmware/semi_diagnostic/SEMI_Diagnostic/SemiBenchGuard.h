#pragma once
#include <stdint.h>

namespace semi {
// Signed differences are valid for the short intervals used here, including rollover.
struct DriveDemand { int action = 0; bool medium = false; uint32_t deadline = 0; };

class BenchGuard {
 public:
  explicit BenchGuard(uint32_t maxMs) : maxMs_(maxMs) {}
  int tick(uint32_t now, bool online, const DriveDemand& demand) {
    if (!online || demand.action == 0) {
      blocked_ = !online;
      active_ = 0;
      return 0;
    }
    if (int32_t(demand.deadline - now) <= 0 ||
        (active_ && (active_ != demand.action || now - start_ >= maxMs_))) {
      blocked_ = true;
    }
    if (blocked_) { active_ = 0; return 0; }
    if (!active_) start_ = now;
    return active_ = demand.action;
  }
 private:
  uint32_t maxMs_, start_ = 0;
  int active_ = 0;
  bool blocked_ = true;  // Require a neutral frame after startup.
};
}

