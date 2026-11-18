#include "../semi_diagnostic/SEMI_Diagnostic/SemiBenchGuard.h"
#include <cassert>
#include <cstdio>

int main() {
  semi::BenchGuard wheels(1500), rack(300);
  semi::DriveDemand stop{}, forward{1,false,250}, up{1,false,250};
  assert(wheels.tick(0,true,forward)==0);
  wheels.tick(1,true,stop); rack.tick(1,true,stop);
  assert(wheels.tick(2,true,forward)==1 && rack.tick(2,true,up)==1);
  assert(wheels.tick(250,true,forward)==0); // No network calls to expire.
  forward.deadline=500;
  assert(wheels.tick(251,true,forward)==0); // Requires observed neutral.
  up.deadline=501;
  assert(rack.tick(301,true,up)==1 && rack.tick(302,true,up)==0);
  wheels.tick(310,true,stop);
  assert(wheels.tick(311,true,forward)==1);
  assert(wheels.tick(312,true,{2,false,500})==0);
  wheels.tick(320,true,stop);
  assert(wheels.tick(321,true,forward)==1 && wheels.tick(322,false,forward)==0);
  assert(wheels.tick(323,true,forward)==0);
  wheels.tick(0xfffffff0,true,stop);
  assert(wheels.tick(0xfffffff1,true,{1,false,16})==1);
  assert(wheels.tick(16,true,{1,false,16})==0);
  std::puts("PASS bench guard: boot, expiry, hard limit, reversal, link, rollover");
}

