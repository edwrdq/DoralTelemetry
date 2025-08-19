#pragma once

#include <cstddef>
#include <cstdint>
#include "api.h"

namespace doraltelemetry {

// Initialize telemetry with an existing PROS Serial instance
void init(pros::Serial* uart);

// Submit one telemetry frame. Arrays may be null if motor_count==0.
// motor_count: typically 4 or 6. Extra values ignored if >6.
void submit(const float* motor_temps,
            const float* motor_rpm,
            const float* motor_volt,
            int motor_count,
            float x,
            float y,
            float theta,
            float battery);

// Optional: start/stop a 200 Hz fake generator
void start_fake_task(int motor_count = 4);
void stop_task();

// Binary payload layout (little-endian), COBS+CRC16 framed:
// [u8 version=1][u8 motor_count][f32 battery][f32 x][f32 y][f32 theta]
// [f32 temps[m]][f32 rpm[m]][f32 volt[m]] [u16 crc16]

} // namespace doraltelemetry

