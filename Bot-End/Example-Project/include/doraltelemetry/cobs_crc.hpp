#pragma once
#include <cstddef>
#include <cstdint>

namespace doraltelemetry {

// CRC16-CCITT (poly 0x1021, init 0xFFFF)
std::uint16_t crc16_ccitt(const std::uint8_t* data, std::size_t len, std::uint16_t init = 0xFFFF);

// COBS encode. Returns encoded size (<= src_len + src_len/254 + 1)
// dst must have sufficient space. Returns 0 on error.
std::size_t cobs_encode(const std::uint8_t* src, std::size_t src_len, std::uint8_t* dst, std::size_t dst_cap);

// COBS decode. Returns decoded size, 0 on error.
std::size_t cobs_decode(const std::uint8_t* src, std::size_t src_len, std::uint8_t* dst, std::size_t dst_cap);

} // namespace doraltelemetry

