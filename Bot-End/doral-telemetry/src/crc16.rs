/// CRC16-CCITT-FALSE: poly 0x1021, init 0xFFFF, refin=false, refout=false, xorout=0x0000
#[inline(always)]
pub fn crc16_ccitt_false(mut crc: u16, data: &[u8]) -> u16 {
    for &b in data {
        crc ^= (b as u16) << 8;
        for _ in 0..8 {
            crc = if (crc & 0x8000) != 0 { (crc << 1) ^ 0x1021 } else { crc << 1 };
        }
    }
    crc
}
pub const INIT: u16 = 0xFFFF;
