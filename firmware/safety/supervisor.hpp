#pragma once
#include <cstdint>

namespace semi {
struct MotorOutput {
    virtual ~MotorOutput() = default;
    virtual void apply(int left, int right) = 0;
};
enum class State { Stop, Moving, Latched };
// Platform-independent core. Caller serializes tick/command calls.
// The transport must authenticate the sender before passing authorized=true.
class Supervisor {
    MotorOutput& motor;
    uint64_t boot, epoch_ = 0, owner = 0, sequence = 0, deadline = 0, last = 0;
    bool ready = false;
    State state_ = State::Stop;
    void stop(bool latch = false) {
        motor.apply(0, 0); ready = false; deadline = 0; ++epoch_;
        state_ = latch ? State::Latched : State::Stop;
    }
public:
    static constexpr uint64_t max_ttl_ms = 450;
    Supervisor(MotorOutput& output, uint64_t boot_nonce) : motor(output), boot(boot_nonce) { motor.apply(0, 0); }
    State state() const { return state_; }
    uint64_t epoch() const { return epoch_; }
    void tick(uint64_t now) {
        if (now < last) { stop(true); return; }
        last = now;
        if (state_ == State::Moving && now >= deadline) stop();
    }
    bool arm(uint64_t session, uint64_t nonce, bool authorized) {
        if (!authorized || !session || nonce != boot || state_ != State::Stop) return false;
        owner = session; sequence = 0; ready = true; ++epoch_; return true;
    }
    bool command(uint64_t now, uint64_t nonce, uint64_t session, uint64_t epoch,
                 uint64_t seq, uint64_t until, int left, int right, bool authorized) {
        tick(now);
        if (!authorized || nonce != boot || !ready || session != owner || epoch != epoch_ ||
            seq <= sequence || until <= now || until - now > max_ttl_ms ||
            left < -500 || left > 500 || right < -500 || right > 500 || state_ == State::Latched) return false;
        sequence = seq; deadline = until;
        motor.apply(left, right);
        state_ = (left || right) ? State::Moving : State::Stop;
        if (!left && !right) stop();
        return true;
    }
    void request_stop() { stop(state_ == State::Latched); }
    void fault() { stop(true); }
    bool clear_fault(bool authorized) {
        if (!authorized) return false;
        stop(); return true; // remains disarmed
    }
};
}
