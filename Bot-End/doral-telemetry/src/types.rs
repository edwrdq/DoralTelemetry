use heapless::Vec;

pub const MAX_MOTORS: usize=16;

pub mod presence {
    pub const BATTERY_MVC: u8 = 1 << 0;
    pub const TEMP: u8 = 1 << 1;
    pub const RPM: u8 = 1 << 2;
    pub const POSE: u8 = 1 << 3;
    pub const BATTERY_PCT: u8 = 1 << 4;
    pub const MOTOR_MVC: u8 = 1 << 5;
}

pub mod ftype {
    pub const ROLES: u8 = 0x10;
    pub const METRICS: u8 = 0x11;
}

#[repr(u8)]
#[derive(Clone, Copy, PartialEq, Eq)]
pub enum MotorKind {Drivetrain=0, Single=1}

#[derive(Clone, Copy)]
pub struct RoleEntry {
    pub id: u8,
    pub kind: MotorKind,
}

pub struct Roles {
    pub entries: Vec<RoleEntry, MAX_MOTORS>,
}

impl Roles {
    pub fn new() -> Self { Self { entries: Vec::new() } }
    pub fn push(&mut self, id: u8, kind: MotorKind) -> Result<(), ()> {
        self.entries.push(RoleEntry {id, kind}).map_err(|_| ())
    } 
}

#[derive(Clone, Copy)]
pub struct MotorSample {
    pub id: u8,
    pub temp_c_centi: Option<i16>,
    pub rpm: Option<i16>,
    pub mv : Option<u16>,
}

pub struct Pose{
    pub x_mm: i32,
    pub y_mm: i32,
    pub heading_cdeg: i16,
}

pub struct Metrics {
    pub battery_mv: Option<u16>,
    pub battery_pct: Option<u8>,
    pub pose: Option<Pose>,
    pub motors: Vec<MotorSample, MAX_MOTORS>,
}

impl Metrics {
    pub fn new() -> Self {
        Self {
            battery_mv: None,
            battery_pct: None,
            pose: None,
            motors: Vec::new(),
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EncErr { NoSpace, Malformed }