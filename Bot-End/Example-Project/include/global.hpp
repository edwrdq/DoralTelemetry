#pragma once
#include "api.h"
#include "lemlib/api.hpp"

//declaring external objects
extern pros::Serial serial;
extern pros::MotorGroup left_motors;
extern pros::MotorGroup right_motors;
extern pros::Imu imu;


extern lemlib::Drivetrain drivetrain;
extern lemlib::OdomSensors sensors;
extern lemlib::ControllerSettings lateral_controller;
extern lemlib::ControllerSettings angular_controller;
extern lemlib::Chassis chassis;