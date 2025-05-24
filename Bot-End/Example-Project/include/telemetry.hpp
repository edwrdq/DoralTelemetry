#pragma once
#include "main.h"

void telemetry_task(float m1Temp, float m2Temp, float m3Temp, float m4Temp, float m5Temp, float m6Temp, float m1Throttle, float m2Throttle, float m3Throttle, float m4Throttle, float m5Throttle, float m6Throttle, float xCoord, float yCoord, float heading, float systemTime);
void controlLoop200Hz(void*);
void startTelemetryTask();