#include "doraltelemetry/cobs_crc.hpp"

namespace doraltelemetry {

std::uint16_t crc16_ccitt(const std::uint8_t* data, std::size_t len, std::uint16_t init) {
    std::uint16_t crc = init;
    for (std::size_t i = 0; i < len; ++i) {
        crc ^= static_cast<std::uint16_t>(data[i]) << 8;
        for (int b = 0; b < 8; ++b) {
            if (crc & 0x8000) crc = (crc << 1) ^ 0x1021;
            else crc <<= 1;
        }
    }
    return crc;
}

std::size_t cobs_encode(const std::uint8_t* src, std::size_t src_len, std::uint8_t* dst, std::size_t dst_cap) {
    if (!src_len) { if (dst_cap) { dst[0] = 1; return 1; } else return 0; }
    std::size_t read_index = 0;
    std::size_t write_index = 1;
    std::size_t code_index = 0;
    std::uint8_t code = 1;

    while (read_index < src_len) {
        if (write_index >= dst_cap) return 0;
        if (src[read_index] == 0) {
            dst[code_index] = code;
            code_index = write_index++;
            code = 1;
            read_index++;
        } else {
            dst[write_index++] = src[read_index++];
            code++;
            if (code == 0xFF) {
                if (code_index >= dst_cap) return 0;
                dst[code_index] = code;
                code_index = write_index++;
                code = 1;
            }
        }
    }
    if (code_index >= dst_cap) return 0;
    dst[code_index] = code;
    return write_index;
}

std::size_t cobs_decode(const std::uint8_t* src, std::size_t src_len, std::uint8_t* dst, std::size_t dst_cap) {
    if (!src_len) return 0;
    std::size_t read_index = 0;
    std::size_t write_index = 0;
    while (read_index < src_len) {
        std::uint8_t code = src[read_index++];
        if (code == 0 || read_index + code - 1 > src_len + 0) return 0;
        for (std::uint8_t i = 1; i < code; ++i) {
            if (write_index >= dst_cap) return 0;
            dst[write_index++] = src[read_index++];
        }
        if (code < 0xFF && read_index < src_len) {
            if (write_index >= dst_cap) return 0;
            dst[write_index++] = 0;
        }
    }
    return write_index;
}

} // namespace doraltelemetry

