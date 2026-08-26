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

// These Unity-compiled shell hashes were isolated by activating the dedicated
// reserved material variant after arming the compiler extension. The activation
// added exactly one 10/9 VS and one 10/5 PS callback to an otherwise identical
// callback inventory. Stage-only, size-only, keyword-only, and first-seen
// matching remain forbidden because the binary callback carries no shader name.
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
