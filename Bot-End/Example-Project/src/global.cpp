#include "main.h"
#include "lemlib/api.hpp"
#include "global.hpp"

//-----Device Definitions---------------------------------------------------------------
//all ports placeholders
pros::Serial serial(21, 512000);
pros::MotorGroup left_motors({1,2,3}, pros::MotorGearset::blue);    
pros::MotorGroup right_motors({-4,-5,-6}, pros::MotorGearset::blue);
pros::Imu imu(10);

//-----LemLib Definitions---------------------------------------------------------------
lemlib::Drivetrain drivetrain(&left_motors, //left motors
                              &right_motors, //right motors
                              10, //track width - placeholder value
                              lemlib::Omniwheel::NEW_325,//wheel type, placeholder value, change according to lemlib docs
                              2 //horizontal drift
);

lemlib::OdomSensors sensors(nullptr,
                            nullptr,
                            nullptr,
                            nullptr,
                            &imu
); //Change first 4 sensors according to lemlib docs, these are the sensors used for odometry. In this example, we are using the internal motor encoders and the IMU as our only sensors.

// lateral PID controller
lemlib::ControllerSettings lateral_controller(10, // proportional gain (kP)
                                               0, // integral gain (kI)
                                               3, // derivative gain (kD)
                                               3, // anti windup
                                               1, // small error range, in inches
                                               100, // small error range timeout, in milliseconds
                                               3, // large error range, in inches
                                               500, // large error range timeout, in milliseconds
                                               20 // maximum acceleration (slew)
);

// angular PID controller
lemlib::ControllerSettings angular_controller(2, // proportional gain (kP)
                                               0, // integral gain (kI)
                                               10, // derivative gain (kD)
                                               3, // anti windup
                                               1, // small error range, in degrees
                                               100, // small error range timeout, in milliseconds
                                               3, // large error range, in degrees
                                               500, // large error range timeout, in milliseconds
                                               0 // maximum acceleration (slew)
);

//creating chassis
lemlib::Chassis chassis(drivetrain, // drivetrain settings
                         lateral_controller, // lateral PID settings
                         angular_controller, // angular PID settings
                         sensors // odometry sensors
);