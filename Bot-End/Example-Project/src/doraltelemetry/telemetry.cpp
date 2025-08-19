#include "doraltelemetry/telemetry.hpp"
#include "doraltelemetry/cobs_crc.hpp"

#include <algorithm>
#include <cstring>
#include <memory>
#include <random>

namespace doraltelemetry {

static pros::Serial* g_uart = nullptr;
static pros::Task* g_task = nullptr;

void init(pros::Serial* uart) { g_uart = uart; }

static void write_frame(const std::uint8_t* payload, std::size_t len) {
    if (!g_uart || !payload || !len) return;
    // append CRC16
    std::uint16_t crc = crc16_ccitt(payload, len, 0xFFFF);
    std::unique_ptr<std::uint8_t[]> tmp(new std::uint8_t[len + 2]);
    std::memcpy(tmp.get(), payload, len);
    tmp[len + 0] = static_cast<std::uint8_t>(crc & 0xFF);
    tmp[len + 1] = static_cast<std::uint8_t>((crc >> 8) & 0xFF);

    // COBS encode
    const std::size_t max_enc = len + 2 + (len + 2) / 254 + 1;
    std::unique_ptr<std::uint8_t[]> enc(new std::uint8_t[max_enc + 1]);
    std::size_t enc_len = cobs_encode(tmp.get(), len + 2, enc.get(), max_enc);
    if (!enc_len) return;

    // zero delimiter
    enc[enc_len] = 0x00;
    g_uart->write(enc.get(), enc_len + 1);
}

void submit(const float* motor_temps,
            const float* motor_rpm,
            const float* motor_volt,
            int motor_count,
            float x,
            float y,
            float theta,
            float battery) {
    if (!g_uart) return;
    if (motor_count < 0) motor_count = 0;
    if (motor_count > 6) motor_count = 6;

    // Prepare payload buffer
    // header (2 + 4*4 = 18 bytes) + arrays (3 * m * 4)
    const std::size_t header = 2 + 4 * 4; // ver, count, battery,x,y,theta
    const std::size_t arrays = static_cast<std::size_t>(motor_count) * 3 * 4;
    const std::size_t len = header + arrays;

    std::unique_ptr<std::uint8_t[]> buf(new std::uint8_t[len]);
    std::size_t w = 0;
    buf[w++] = 1; // version
    buf[w++] = static_cast<std::uint8_t>(motor_count);

    auto wfloat = [&](float f) {
        std::uint32_t u; std::memcpy(&u, &f, sizeof(float));
        buf[w++] = static_cast<std::uint8_t>(u & 0xFF);
        buf[w++] = static_cast<std::uint8_t>((u >> 8) & 0xFF);
        buf[w++] = static_cast<std::uint8_t>((u >> 16) & 0xFF);
        buf[w++] = static_cast<std::uint8_t>((u >> 24) & 0xFF);
    };

    wfloat(battery);
    wfloat(x);
    wfloat(y);
    wfloat(theta);

    auto warray = [&](const float* arr) {
        for (int i = 0; i < motor_count; ++i) {
            float v = arr ? arr[i] : 0.0f;
            wfloat(v);
        }
    };

    warray(motor_temps);
    warray(motor_rpm);
    warray(motor_volt);

    write_frame(buf.get(), len);
}

static void fake_loop(void*) {
    std::mt19937 rng(pros::millis());
    std::uniform_real_distribution<float> tempR(30.0f, 55.0f);
    std::uniform_real_distribution<float> rpmR(0.0f, 600.0f);
    std::uniform_real_distribution<float> voltR(0.0f, 12.0f);
    std::uniform_real_distribution<float> xyR(0.0f, 144.0f);
    std::uniform_real_distribution<float> thR(0.0f, 360.0f);

    int m = 4;
    while (g_task) {
        float t[6], r[6], v[6];
        for (int i = 0; i < m; ++i) { t[i] = tempR(rng); r[i] = rpmR(rng); v[i] = voltR(rng); }
        float x = xyR(rng), y = xyR(rng), th = thR(rng);
        float bat = 90.0f;
        submit(t, r, v, m, x, y, th, bat);
        pros::delay(5);
    }
}

void start_fake_task(int motor_count) {
    stop_task();
    g_task = new pros::Task(fake_loop, nullptr, TASK_PRIORITY_DEFAULT + 1, TASK_STACK_DEPTH_DEFAULT, "DTM Fake");
}

void stop_task() {
    if (g_task) { delete g_task; g_task = nullptr; }
}

} // namespace doraltelemetry

