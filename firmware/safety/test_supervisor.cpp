#include "supervisor.hpp"
#include <cassert>
#include <cstdio>
struct FakeMotor : semi::MotorOutput {
    int left=0, right=0, calls=0;
    void apply(int l, int r) override {left=l;right=r;++calls;}
};
int main() {
    FakeMotor motor; semi::Supervisor s(motor,42);
    assert(s.state()==semi::State::Stop && motor.left==0);
    assert(!s.arm(1,42,false)); assert(!s.arm(1,41,true));
    assert(s.arm(1,42,true)); auto epoch=s.epoch();
    assert(!s.command(0,42,2,epoch,1,450,250,250,true));
    assert(!s.command(0,42,1,epoch,1,450,501,0,true));
    assert(!s.command(0,42,1,epoch,1,451,250,250,true));
    assert(!s.command(0,42,1,epoch,1,450,250,250,false));
    assert(s.command(0,42,1,epoch,1,450,250,250,true));
    assert(!s.command(0,42,1,epoch,1,450,250,250,true));
    assert(s.command(150,42,1,epoch,2,600,250,250,true));
    // Autonomous timer ticks: no Django, browser, transport, or new command.
    for(uint64_t t=151;t<600;++t){s.tick(t);assert(motor.left==250);}
    s.tick(600); assert(motor.left==0 && s.state()==semi::State::Stop);
    assert(!s.command(601,42,1,epoch,3,900,250,250,true));
    assert(s.arm(1,42,true));epoch=s.epoch();
    assert(s.command(610,42,1,epoch,1,1000,250,-250,true));
    s.fault();assert(motor.left==0 && s.state()==semi::State::Latched);
    assert(!s.arm(1,42,true)); assert(!s.clear_fault(false)); assert(s.clear_fault(true));
    assert(s.arm(1,42,true));epoch=s.epoch();
    assert(!s.command(620,42,1,epoch,1,619,250,250,true));
    s.tick(1); assert(s.state()==semi::State::Latched); // backward time fails closed
    semi::Supervisor reboot(motor,43);assert(motor.left==0);
    assert(!reboot.arm(1,42,true));assert(reboot.arm(1,43,true));
    assert(reboot.command(0,43,1,reboot.epoch(),1,450,500,500,true));
    reboot.request_stop();assert(motor.left==0);
    // Deterministic jitter budget. Timer gaps 1..10 ms; lateness <=10 ms.
    unsigned worst=0;
    for(unsigned phase=1;phase<=10;++phase){
        FakeMotor fake;semi::Supervisor q(fake,1);assert(q.arm(1,1,true));
        assert(q.command(0,1,1,q.epoch(),1,450,250,250,true));
        uint64_t t=0;while(fake.left){t+=phase;q.tick(t);}
        assert(t>=450 && t-450<=10);if(t-450>worst)worst=unsigned(t-450);
    }
    std::printf("Supervisor native tests PASS: boot, authorization, lease, renewal, duplicate, expiry, STOP, latch, reboot, old boot, backward clock, limits. Worst deterministic expiry lateness: %u ms. No HTTP or real output.\n",worst);
}
