#include "domain_model.hpp"
#include <cassert>
#include <cstdio>
int main() {
    using semi::Domain; using semi::State;
    semi::DomainModel q(7);
    assert(!q.physical_authorized());
    assert(q.state(Domain::Traction)==State::Stop && q.state(Domain::Rack)==State::Stop);
    assert(!q.arm(Domain::Traction,11,7,true));
    q.approve_bench(true);
    assert(!q.arm(Domain::Traction,11,7,false));
    assert(q.arm(Domain::Traction,11,7,true));
    assert(!q.arm(Domain::Rack,22,7,true));
    q.set_rack_limits(true);
    assert(q.arm(Domain::Rack,22,7,true));
    auto t=q.epoch(Domain::Traction),r=q.epoch(Domain::Rack);
    assert(q.command(Domain::Traction,0,7,11,t,1,450,250,250,true));
    assert(q.command(Domain::Rack,0,7,22,r,1,300,120,0,true));
    assert(!q.command(Domain::Rack,1,7,22,r,1,300,120,0,true));
    assert(!q.command(Domain::Rack,1,7,22,r,2,300,-120,0,true));
    assert(!q.command(Domain::Rack,1,7,11,r,2,300,120,0,true));
    q.tick(300); // No HTTP, new commands or LiDAR condition.
    assert(q.state(Domain::Rack)==State::Stop && q.state(Domain::Traction)==State::Moving);
    q.tick(450); assert(q.state(Domain::Traction)==State::Stop);
    assert(!q.command(Domain::Traction,451,7,11,t,2,100,250,250,true));
    assert(q.arm(Domain::Traction,11,7,true));
    assert(q.command(Domain::Traction,452,7,11,q.epoch(Domain::Traction),1,100,250,250,true));
    assert(q.arm(Domain::Rack,22,7,true));
    assert(q.command(Domain::Rack,452,7,22,q.epoch(Domain::Rack),1,100,120,0,true));
    q.set_rack_limits(false);
    assert(q.state(Domain::Rack)==State::Latched && q.state(Domain::Traction)==State::Moving);
    q.stop_all(); assert(q.state(Domain::Traction)==State::Stop);
    assert(!q.arm(Domain::Rack,22,7,true));
    semi::DomainModel reboot(8);
    assert(!reboot.physical_authorized());
    assert(!reboot.command(Domain::Traction,0,7,11,t,3,100,250,250,true));
    std::puts("PASS: independent native domains, default STOP, authorization, leases, limits, expiry without HTTP, STOP all, reboot. Fake outputs only.");
}
