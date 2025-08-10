use crate::crc16::{crc16_ccitt_false, INIT};
use crate::types::{self, EncErr};
use heapless::Vec as HVec;

/// A single zero byte separates frames on the wire.
pub const DELIM: u8 = 0x00;

/// Little-endian write helpers
#[inline(always)] fn put_u16(dst: &mut [u8], v: u16) { dst[0] = (v & 0xFF) as u8; dst[1] = (v >> 8) as u8; }
#[inline(always)] fn put_i16(dst: &mut [u8], v: i16) { put_u16(dst, v as u16); }
#[inline(always)] fn put_i32(dst: &mut [u8], v: i32) { 
    dst[0] =  (v        & 0xFF) as u8;
    dst[1] = ((v >> 8)  & 0xFF) as u8;
    dst[2] = ((v >> 16) & 0xFF) as u8;
    dst[3] = ((v >> 24) & 0xFF) as u8;
}

/// Encode TYPE=0x10 roles: [type, count, (id,kind)*, crc] then COBS + 0x00
pub fn encode_roles(roles: &types::Roles, out: &mut [u8]) -> Result<usize, EncErr> {
    // Raw buffer (pre-COBS). Worst case with 16 motors fits easily in 64 bytes.
    let mut raw: HVec<u8, 96> = HVec::new();

    raw.push(types::ftype::ROLES).map_err(|_| EncErr::NoSpace)?;
    raw.push(roles.entries.len() as u8).map_err(|_| EncErr::NoSpace)?;

    for e in roles.entries.iter() {
        raw.push(e.id).map_err(|_| EncErr::NoSpace)?;
        raw.push(e.kind as u8).map_err(|_| EncErr::NoSpace)?;
    }

    let crc = crc16_ccitt_false(INIT, &raw);
    raw.push((crc >> 8) as u8).map_err(|_| EncErr::NoSpace)?;
    raw.push((crc & 0xFF) as u8).map_err(|_| EncErr::NoSpace)?;

    // COBS encode
    let need = cobs::max_encoding_length(raw.len());
    if need + 1 > out.len() { return Err(EncErr::NoSpace); }
    let enc_len = cobs::encode(&raw, &mut out[..need]).map_err(|_| EncErr::NoSpace)?;
    out[enc_len] = DELIM;
    Ok(enc_len + 1)
}

/// Encode TYPE=0x11 metrics: presence + optional fields + per-motor tuples, then CRC, COBS, delimiter.
/// Optional motors: simply push as many as you have this tick.
pub fn encode_metrics(m: &types::Metrics, out: &mut [u8]) -> Result<usize, EncErr> {
    // Rough bound: ~18 + 5*MAX_MOTORS fits in 128; be generous.
    let mut raw: HVec<u8, 192> = HVec::new();

    raw.push(types::ftype::METRICS).map_err(|_| EncErr::NoSpace)?;

    // Presence bits
    let mut pres: u8 = 0;
    if m.battery_mv.is_some()  { pres |= types::presence::BATTERY_MV; }
    if m.battery_pct.is_some() { pres |= types::presence::BATTERY_PCT; }
    if m.pose.is_some()        { pres |= types::presence::POSE; }

    // Do we have at least one temp or rpm anywhere?
    let any_temp = m.motors.iter().any(|x| x.temp_c_centi.is_some());
    let any_rpm  = m.motors.iter().any(|x| x.rpm.is_some());
    if any_temp { pres |= types::presence::TEMP; }
    if any_rpm  { pres |= types::presence::RPM; }

    raw.push(pres).map_err(|_| EncErr::NoSpace)?;
    raw.push(m.motors.len() as u8).map_err(|_| EncErr::NoSpace)?;

    // battery_mv (u16 le) then battery_pct (u8)
    if let Some(v) = m.battery_mv {
        let off = raw.len();
        raw.resize(off + 2, 0).map_err(|_| EncErr::NoSpace)?;
        put_u16(&mut raw[off..off+2], v);
    }
    if let Some(p) = m.battery_pct {
        raw.push(p).map_err(|_| EncErr::NoSpace)?;
    }

    // pose if present: i32 x, i32 y, i16 heading_cdeg
    if let Some(pose) = m.pose {
        let off = raw.len();
        raw.resize(off + 4 + 4 + 2, 0).map_err(|_| EncErr::NoSpace)?;
        put_i32(&mut raw[off..off+4], pose.x_mm);
        put_i32(&mut raw[off+4..off+8], pose.y_mm);
        put_i16(&mut raw[off+8..off+10], pose.heading_cdeg);
    }

    // per-motor entries
    for ms in m.motors.iter() {
        raw.push(ms.id).map_err(|_| EncErr::NoSpace)?;
        if pres & types::presence::TEMP != 0 {
            let t = ms.temp_c_centi.unwrap_or(0);
            let off = raw.len();
            raw.resize(off + 2, 0).map_err(|_| EncErr::NoSpace)?;
            put_i16(&mut raw[off..off+2], t);
        }
        if pres & types::presence::RPM != 0 {
            let r = ms.rpm.unwrap_or(0);
            let off = raw.len();
            raw.resize(off + 2, 0).map_err(|_| EncErr::NoSpace)?;
            put_i16(&mut raw[off..off+2], r);
        }
    }

    // CRC over everything so far
    let crc = crc16_ccitt_false(INIT, &raw);
    raw.push((crc >> 8) as u8).map_err(|_| EncErr::NoSpace)?;
    raw.push((crc & 0xFF) as u8).map_err(|_| EncErr::NoSpace)?;

    // COBS encode (+ delimiter)
    let need = cobs::max_encoding_length(raw.len());
    if need + 1 > out.len() { return Err(EncErr::NoSpace); }
    let enc_len = cobs::encode(&raw, &mut out[..need]).map_err(|_| EncErr::NoSpace)?;
    out[enc_len] = DELIM;
    Ok(enc_len + 1)
}
use crate::crc16::{crc16_ccitt_false, INIT};
use crate::types::{self, EncErr};
use heapless::Vec as HVec;

/// A single zero byte separates frames on the wire.
pub const DELIM: u8 = 0x00;

/// Little-endian write helpers
#[inline(always)]
fn put_u16(dst: &mut [u8], v: u16) {
    dst[0] = (v & 0xFF) as u8;
    dst[1] = (v >> 8) as u8;
}
#[inline(always)]
fn put_i16(dst: &mut [u8], v: i16) { put_u16(dst, v as u16); }
#[inline(always)]
fn put_i32(dst: &mut [u8], v: i32) {
    dst[0] =  (v        & 0xFF) as u8;
    dst[1] = ((v >> 8)  & 0xFF) as u8;
    dst[2] = ((v >> 16) & 0xFF) as u8;
    dst[3] = ((v >> 24) & 0xFF) as u8;
}

/// Encode TYPE=0x10 roles: [type, count, (id,kind)*, crc] then COBS + 0x00
pub fn encode_roles(roles: &types::Roles, out: &mut [u8]) -> Result<usize, EncErr> {
    // Raw buffer (pre-COBS). Worst case with 16 motors fits easily in 64 bytes.
    let mut raw: HVec<u8, 96> = HVec::new();

    raw.push(types::ftype::ROLES).map_err(|_| EncErr::NoSpace)?;
    raw.push(roles.entries.len() as u8).map_err(|_| EncErr::NoSpace)?;

    for e in roles.entries.iter() {
        raw.push(e.id).map_err(|_| EncErr::NoSpace)?;
        raw.push(e.kind as u8).map_err(|_| EncErr::NoSpace)?;
    }

    let crc = crc16_ccitt_false(INIT, &raw);
    raw.push((crc >> 8) as u8).map_err(|_| EncErr::NoSpace)?;
    raw.push((crc & 0xFF) as u8).map_err(|_| EncErr::NoSpace)?;

    // COBS encode
    let need = cobs::max_encoding_length(raw.len());
    if need + 1 > out.len() { return Err(EncErr::NoSpace); }
    let enc_len = cobs::encode(&raw, &mut out[..need]).map_err(|_| EncErr::NoSpace)?;
    out[enc_len] = DELIM;
    Ok(enc_len + 1)
}

/// Encode TYPE=0x11 metrics: presence + optional fields + per-motor tuples, then CRC, COBS, delimiter.
/// Optional motors: simply push as many as you have this tick.
pub fn encode_metrics(m: &types::Metrics, out: &mut [u8]) -> Result<usize, EncErr> {
    // Rough bound: header/presence + pose/battery + ~7 bytes per motor (id + temp + rpm + mv).
    let mut raw: HVec<u8, 192> = HVec::new();

    raw.push(types::ftype::METRICS).map_err(|_| EncErr::NoSpace)?;

    // Presence bits
    let mut pres: u8 = 0;
    if m.battery_mv.is_some()  { pres |= types::presence::BATTERY_MV; }
    if m.battery_pct.is_some() { pres |= types::presence::BATTERY_PCT; }
    if m.pose.is_some()        { pres |= types::presence::POSE; }

    // At least one motor field present?
    let any_temp = m.motors.iter().any(|x| x.temp_c_centi.is_some());
    let any_rpm  = m.motors.iter().any(|x| x.rpm.is_some());
    let any_mv   = m.motors.iter().any(|x| x.mv.is_some());
    if any_temp { pres |= types::presence::TEMP; }
    if any_rpm  { pres |= types::presence::RPM; }
    if any_mv   { pres |= types::presence::MOTOR_MV; }

    raw.push(pres).map_err(|_| EncErr::NoSpace)?;
    raw.push(m.motors.len() as u8).map_err(|_| EncErr::NoSpace)?;

    // battery_mv (u16 le) then battery_pct (u8)
    if let Some(v) = m.battery_mv {
        let off = raw.len();
        raw.resize(off + 2, 0).map_err(|_| EncErr::NoSpace)?;
        put_u16(&mut raw[off..off + 2], v);
    }
    if let Some(p) = m.battery_pct {
        raw.push(p).map_err(|_| EncErr::NoSpace)?;
    }

    // pose if present: i32 x, i32 y, i16 heading_cdeg
    if let Some(pose) = m.pose {
        let off = raw.len();
        raw.resize(off + 4 + 4 + 2, 0).map_err(|_| EncErr::NoSpace)?;
        put_i32(&mut raw[off..off + 4], pose.x_mm);
        put_i32(&mut raw[off + 4..off + 8], pose.y_mm);
        put_i16(&mut raw[off + 8..off + 10], pose.heading_cdeg);
    }

    // per-motor entries
    for ms in m.motors.iter() {
        raw.push(ms.id).map_err(|_| EncErr::NoSpace)?;
        if pres & types::presence::TEMP != 0 {
            let t = ms.temp_c_centi.unwrap_or(0);
            let off = raw.len();
            raw.resize(off + 2, 0).map_err(|_| EncErr::NoSpace)?;
            put_i16(&mut raw[off..off + 2], t);
        }
        if pres & types::presence::RPM != 0 {
            let r = ms.rpm.unwrap_or(0);
            let off = raw.len();
            raw.resize(off + 2, 0).map_err(|_| EncErr::NoSpace)?;
            put_i16(&mut raw[off..off + 2], r);
        }
        if pres & types::presence::MOTOR_MV != 0 {
            let mv = ms.mv.unwrap_or(0);
            let off = raw.len();
            raw.resize(off + 2, 0).map_err(|_| EncErr::NoSpace)?;
            put_u16(&mut raw[off..off + 2], mv);
        }
    }

    // CRC over everything so far
    let crc = crc16_ccitt_false(INIT, &raw);
    raw.push((crc >> 8) as u8).map_err(|_| EncErr::NoSpace)?;
    raw.push((crc & 0xFF) as u8).map_err(|_| EncErr::NoSpace)?;

    // COBS encode (+ delimiter)
    let need = cobs::max_encoding_length(raw.len());
    if need + 1 > out.len() { return Err(EncErr::NoSpace); }
    let enc_len = cobs::encode(&raw, &mut out[..need]).map_err(|_| EncErr::NoSpace)?;
    out[enc_len] = DELIM;
    Ok(enc_len + 1)
}
