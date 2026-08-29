#pragma once

#include <cstddef>
#include <cstdint>

// Compile-only fallback. The native transport deliberately reports not ready
// unless the byte-exact header generated from a validated live capture exists.
inline constexpr bool g_EndfieldUberCapturePayloadAvailable = false;
inline constexpr std::uint8_t g_EndfieldUberEarlyVsB0[16] = {};
inline constexpr std::size_t g_EndfieldUberEarlyVsB0Size = sizeof(g_EndfieldUberEarlyVsB0);
inline constexpr std::uint8_t g_EndfieldUberEarlyPsB0[28 * 16] = {};
inline constexpr std::size_t g_EndfieldUberEarlyPsB0Size = sizeof(g_EndfieldUberEarlyPsB0);
inline constexpr std::uint8_t g_EndfieldUberEarlyPsB1[26 * 16] = {};
inline constexpr std::size_t g_EndfieldUberEarlyPsB1Size = sizeof(g_EndfieldUberEarlyPsB1);
inline constexpr std::uint8_t g_EndfieldUberVsB0[16] = {};
inline constexpr std::size_t g_EndfieldUberVsB0Size = sizeof(g_EndfieldUberVsB0);
inline constexpr std::uint8_t g_EndfieldUberPsB0[28 * 16] = {};
inline constexpr std::size_t g_EndfieldUberPsB0Size = sizeof(g_EndfieldUberPsB0);
inline constexpr std::uint8_t g_EndfieldUberPsB1[26 * 16] = {};
inline constexpr std::size_t g_EndfieldUberPsB1Size = sizeof(g_EndfieldUberPsB1);
