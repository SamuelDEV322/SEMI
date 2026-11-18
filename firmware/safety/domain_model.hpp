#pragma once
#include "supervisor.hpp"
// Native preparation only: private fake outputs, no Arduino, pins or driver calls.
// Transport authentication must be verified before authenticated=true is supplied.
namespace semi {
enum class Domain { Traction, Rack };
struct BenchIntent final : MotorOutput {
    int a = 0, b = 0;
    void apply(int left, int right) override { a=left; b=right; }
};
class DomainModel {
    BenchIntent traction_intent, rack_intent;
    Supervisor traction, rack;
    bool bench_approved=false, rack_limits=false;
    Supervisor& controller(Domain d) { return d==Domain::Traction ? traction : rack; }
public:
    explicit DomainModel(uint64_t boot):traction(traction_intent,boot),rack(rack_intent,boot) {}
    // This enables simulated intentions only. No physical output interface exists.
    void approve_bench(bool approved) { bench_approved=approved; if(!approved) stop_all(); }
    void set_rack_limits(bool healthy) { rack_limits=healthy; if(!healthy) rack.fault(); }
    bool arm(Domain d,uint64_t session,uint64_t boot,bool authenticated) {
        return bench_approved && (d!=Domain::Rack || rack_limits) && controller(d).arm(session,boot,authenticated);
    }
    uint64_t epoch(Domain d) { return controller(d).epoch(); }
    State state(Domain d) { return controller(d).state(); }
    bool command(Domain d,uint64_t now,uint64_t boot,uint64_t session,uint64_t epoch,
                 uint64_t seq,uint64_t duration_ms,int a,int b,bool authenticated) {
        tick(now);
        if(!bench_approved || (d==Domain::Rack && (!rack_limits || b!=0))) return false;
        // Rack opposite direction requires an explicit stop/re-arm.
        if(d==Domain::Rack && rack_intent.a && a && ((rack_intent.a<0)!=(a<0))) return false;
        return controller(d).command(now,boot,session,epoch,seq,now+duration_ms,a,b,authenticated);
    }
    void tick(uint64_t now) { traction.tick(now); rack.tick(now); }
    void stop(Domain d) { controller(d).request_stop(); }
    void stop_all() { traction.request_stop(); rack.request_stop(); }
    bool physical_authorized() const { return false; }
};
}
