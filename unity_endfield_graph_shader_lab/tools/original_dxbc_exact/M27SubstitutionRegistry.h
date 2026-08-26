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

// The Unity-compiled shell hashes have not yet been observed and independently
// pinned. These entries deliberately cannot match until those exact hashes are
// placed here. Stage-only, size-only, keyword-only, and first-seen matching are
// forbidden because the compiler callback carries no shader/pass identity.
inline constexpr Entry kEntries[] = {
    {
        Stage::Vertex,
        false,
        {},
        g_EndfieldM27VertexDxbc,
        g_EndfieldM27VertexDxbcSize,
        g_EndfieldM27VertexDxbcSha256,
    },
    {
        Stage::Pixel,
        false,
        {},
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
