#pragma once

#include <cstddef>
#include <cstdint>
#include <cstring>

#include "EmbeddedDxbc.generated.h"

namespace EndfieldM27Substitution
{
enum class Stage : std::uint32_t
{
    Vertex = 1,
    Pixel = 2,
};

struct Entry
{
    Stage stage;
    bool shellHashPinned;
    unsigned char shellSha256[32];
    const unsigned char* replacementDxbc;
    std::size_t replacementDxbcSize;
    const unsigned char* replacementSha256;
};

// These Unity-compiled shell hashes were isolated by activating dedicated
// reserved material variants after arming the compiler extension. Stage-only,
// size-only, keyword-only, and first-seen matching remain forbidden because the
// binary callback carries no shader name. The first pair is M27 HGBuffer; the
// second pair is M14 VFXBaseV2 SceneColor/SceneMV.
inline constexpr Entry kEntries[] = {
    {
        Stage::Vertex,
        true,
        {
            0xb6, 0xff, 0xa6, 0xa6, 0x50, 0xc4, 0x3f, 0xa8,
            0x6c, 0xfe, 0xd1, 0xa1, 0x46, 0xec, 0xdf, 0xb0,
            0x46, 0xd6, 0xc9, 0x2c, 0x7e, 0x86, 0x6f, 0xf6,
            0xf5, 0x1a, 0xc7, 0x9a, 0x6c, 0x7d, 0x48, 0x33,
        },
        g_EndfieldM27VertexDxbc,
        g_EndfieldM27VertexDxbcSize,
        g_EndfieldM27VertexDxbcSha256,
    },
    {
        Stage::Pixel,
        true,
        {
            0x9a, 0x68, 0x03, 0x52, 0x76, 0x79, 0xaa, 0x4d,
            0x48, 0x22, 0xca, 0x38, 0xa4, 0x25, 0x7c, 0x2d,
            0xaf, 0xcb, 0xce, 0x27, 0x48, 0xa6, 0x7c, 0x7e,
            0x33, 0x87, 0xf6, 0x3e, 0x3e, 0xe5, 0x47, 0x07,
        },
        g_EndfieldM27PixelDxbc,
        g_EndfieldM27PixelDxbcSize,
        g_EndfieldM27PixelDxbcSha256,
    },
    {
        Stage::Vertex,
        true,
        {
            0x0d, 0xc6, 0xbf, 0x25, 0x9f, 0x85, 0x10, 0xc1,
            0xe2, 0x80, 0x16, 0x05, 0x43, 0xca, 0xb0, 0xb5,
            0x91, 0x48, 0x5a, 0x34, 0xbf, 0x22, 0x6c, 0x04,
            0x8b, 0xf3, 0xf2, 0x45, 0xfd, 0xad, 0x67, 0x14,
        },
        g_EndfieldM14VertexDxbc,
        g_EndfieldM14VertexDxbcSize,
        g_EndfieldM14VertexDxbcSha256,
    },
    {
        Stage::Pixel,
        true,
        {
            0x46, 0x5a, 0x86, 0xbc, 0x25, 0x08, 0x35, 0x37,
            0xc7, 0xcf, 0xa6, 0xd8, 0xf4, 0x81, 0x25, 0x3d,
            0x90, 0x7a, 0x29, 0xe4, 0x09, 0x7f, 0xc5, 0xce,
            0x37, 0x8d, 0x08, 0x00, 0x83, 0xe2, 0x5b, 0x57,
        },
        g_EndfieldM14PixelDxbc,
        g_EndfieldM14PixelDxbcSize,
        g_EndfieldM14PixelDxbcSha256,
    },
};

inline const Entry* Resolve(Stage stage, const unsigned char shellSha256[32])
{
    if (shellSha256 == nullptr)
        return nullptr;
    for (const Entry& entry : kEntries)
    {
        if (entry.stage == stage && entry.shellHashPinned &&
            std::memcmp(entry.shellSha256, shellSha256, 32) == 0)
        {
            return &entry;
        }
    }
    return nullptr;
}

inline bool Ready()
{
    for (const Entry& entry : kEntries)
    {
        if (!entry.shellHashPinned)
            return false;
    }
    return true;
}
} // namespace EndfieldM27Substitution
