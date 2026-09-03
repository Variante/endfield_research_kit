"""Strict decoder for Endfield's bit-inverted LZ4 block variant."""

from __future__ import annotations


def decompress_inverted_lz4(source: bytes, expected: int) -> bytes:
    """Decode one block and require exact source and destination consumption."""

    if expected < 0:
        raise ValueError(f"negative inverted-LZ4 output size: {expected}")
    output = bytearray(expected)
    source_pos = output_pos = 0
    while source_pos < len(source) and output_pos < expected:
        token = source[source_pos]
        source_pos += 1
        literal_length = token & 0x33
        match_length = (token & 0xCC) >> 2
        match_length = (match_length & 3) | (match_length >> 2)
        literal_length = (literal_length & 3) | (literal_length >> 2)
        if literal_length == 15:
            while True:
                if source_pos >= len(source):
                    raise ValueError("truncated inverted-LZ4 literal length")
                value = source[source_pos]
                source_pos += 1
                literal_length += value
                if value != 255:
                    break
        if source_pos + literal_length > len(source) or output_pos + literal_length > expected:
            raise ValueError("truncated inverted-LZ4 literal")
        output[output_pos : output_pos + literal_length] = source[
            source_pos : source_pos + literal_length
        ]
        source_pos += literal_length
        output_pos += literal_length
        if source_pos >= len(source):
            break
        if source_pos + 2 > len(source):
            raise ValueError("truncated inverted-LZ4 match offset")
        offset = (source[source_pos] << 8) | source[source_pos + 1]
        source_pos += 2
        if offset <= 0 or offset > output_pos:
            raise ValueError(f"invalid inverted-LZ4 match offset: {offset}")
        if match_length == 15:
            while True:
                if source_pos >= len(source):
                    raise ValueError("truncated inverted-LZ4 match length")
                value = source[source_pos]
                source_pos += 1
                match_length += value
                if value != 255:
                    break
        match_length += 4
        match_pos = output_pos - offset
        if output_pos + match_length > expected:
            raise ValueError("inverted-LZ4 match exceeds output")
        for _ in range(match_length):
            output[output_pos] = output[match_pos]
            output_pos += 1
            match_pos += 1
    if source_pos != len(source) or output_pos != expected:
        raise ValueError(
            f"inverted-LZ4 size mismatch: source={source_pos}/{len(source)}, "
            f"output={output_pos}/{expected}"
        )
    return bytes(output)


__all__ = ["decompress_inverted_lz4"]
