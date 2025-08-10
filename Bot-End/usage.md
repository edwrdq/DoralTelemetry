```rust
use doral_telemetry::types::*;
use doral_telemetry::encode::{encode_roles, encode_metrics};

fn boot_roles_example(mut write: impl FnMut(&[u8])) {
    let mut roles = Roles::new();
    for &id in &[1,2,3,4] { roles.push(id, MotorKind::Drivetrain).ok(); }
    for &id in &[5,6]     { roles.push(id, MotorKind::Single).ok(); }
    let mut out = [0u8; 96];
    let n = encode_roles(&roles, &mut out).unwrap();
    write(&out[..n]);
}

fn tick_metrics_example(mut write: impl FnMut(&[u8])) {
    let mut out = [0u8; 192];

    let mut m = Metrics::new();
    m.battery_mv  = Some(12150);
    m.battery_pct = Some(88);
    m.pose        = Some(Pose { x_mm: 1234, y_mm: -210, heading_cdeg: 9150 });

    m.motors.push(MotorSample { id: 1, temp_c_centi: Some(3150), rpm: Some(1275) }).ok();
    m.motors.push(MotorSample { id: 2, temp_c_centi: Some(3120), rpm: Some(1280) }).ok();
    // Optional: skip temp/rpm or entire motors as needed:
    m.motors.push(MotorSample { id: 5, temp_c_centi: None, rpm: Some(4500) }).ok();

    let n = encode_metrics(&m, &mut out).unwrap();
    write(&out[..n]);
}
```

example of how to use in your code, should actually loop & call values though. ts example will be updated