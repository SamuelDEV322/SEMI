#include "supervisor.hpp"
#include "esp_timer.h"
#include "esp_random.h"
#include "esp_log.h"
// No motor driver, GPIO or PWM. No transport accepts motion in this project.
struct FakeOutput : semi::MotorOutput {
    int left=0, right=0;
    void apply(int l,int r) override {left=l;right=r;}
};
static FakeOutput output;
static semi::Supervisor* supervisor;
static void local_timer(void*) {
    supervisor->tick(static_cast<uint64_t>(esp_timer_get_time()) / 1000);
}
extern "C" void app_main() {
    static semi::Supervisor core(output,esp_random());
    supervisor=&core;
    esp_timer_handle_t timer;
    const esp_timer_create_args_t args={.callback=local_timer,.arg=nullptr,.dispatch_method=ESP_TIMER_TASK,.name="motion_lease",.skip_unhandled_events=false};
    ESP_ERROR_CHECK(esp_timer_create(&args,&timer));
    ESP_ERROR_CHECK(esp_timer_start_periodic(timer,10000));
    ESP_LOGI("SEMI_FAKE","STOP. Local 10 ms timer. Fake outputs only; no GPIO/PWM.");
}
