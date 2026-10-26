"""Exact stored block-compressed Texture2D mip ranges and PNG projection.

No shader roles, normal reconstruction or colour-space conversion are inferred.
The admitted generic body and its exact archive/inline bytes are the inputs.


Evidence and admission boundary
-------------------------------
Exact supported scope is unstripped single-image block-compressed Texture2D:
every mip's dimensions/block footprint and the full byte census must agree with
stored image size and the exact owner-archive range. Unsupported platform
layouts, stripped mips and other dimensions remain unavailable. Stored UV set,
transform, sampler and colour-space fields do not prove active shader roles,
live sampling or runtime overrides.
"""
import base64
import struct
import zlib

# Intrinsic Unity TextureFormat enum values, not installed-build addresses.
BLOCK_FORMATS={10:('DXT1',8),12:('DXT5',16),25:('BC7',16),26:('BC4',8),27:('BC5',16)}


def read_texture(body,stream=None,*,max_pixels=16_777_216):
    fields=('m_Width','m_Height','m_MipCount','m_MipsStripped','m_ImageCount','m_TextureDimension','m_TextureFormat','m_CompleteImageSize')
    if any(type(body.get(k)) is not int for k in fields):raise ValueError('Texture2D integer descriptor fields differ')
    width,height,count=body['m_Width'],body['m_Height'],body['m_MipCount']
    if width<=0 or height<=0 or width*height>max_pixels or not 1<=count<=max(width,height).bit_length():
        raise ValueError('Texture2D dimensions/mip count exceed bounds')
    if body['m_MipsStripped']!=0 or body['m_ImageCount']!=1 or body['m_TextureDimension']!=2:
        raise ValueError('Texture2D requires unstripped single-image 2D storage')
    if body['m_TextureFormat'] not in BLOCK_FORMATS:raise ValueError('Texture2D block format is unsupported')
    if body.get('m_PlatformBlob'):raise ValueError('Texture2D platform-specific layout is unsupported')
    inline=base64.b64decode(body['image data'],validate=True);descriptor=body['m_StreamData']
    if type(descriptor.get('size')) is not int or descriptor['size']<0:raise ValueError('Texture2D stream size differs')
    if descriptor['size']:
        if inline or stream is None or len(stream)!=descriptor['size']:raise ValueError('Texture2D inline/archive payload selection differs')
        payload=stream
    else:
        if stream is not None:raise ValueError('Texture2D inline payload has unexpected archive bytes')
        payload=inline
    name,block_size=BLOCK_FORMATS[body['m_TextureFormat']];ranges=[];offset=0
    for mip in range(count):
        w,h=max(1,width>>mip),max(1,height>>mip);size=((w+3)//4)*((h+3)//4)*block_size
        ranges.append(dict(mip=mip,width=w,height=h,offset=offset,byteSize=size));offset+=size
    if offset!=len(payload) or body['m_CompleteImageSize']!=len(payload):
        raise ValueError(f'Texture2D complete mip byte census differs: expected={offset}; actual={len(payload)}; declared={body["m_CompleteImageSize"]}')
    if body.get('m_ColorSpace') not in (0,1):raise ValueError('Texture2D stored colour-space enum is unsupported')
    return dict(format=name,formatId=body['m_TextureFormat'],width=width,height=height,mipCount=count,
                mips=ranges,payload=payload,storedColorSpace=body['m_ColorSpace'],sampler=body['m_TextureSettings'])


def png_from_bgra(width,height,pixels):
    """Encode decoder channels verbatim, vertically flipped as Unity exports."""
    if width<=0 or height<=0 or len(pixels)!=width*height*4:raise ValueError('decoded BGRA32 dimensions/length differ')
    rgba=bytearray(pixels);rgba[0::4],rgba[2::4]=pixels[2::4],pixels[0::4]
    stride=width*4;rows=b''.join(b'\0'+rgba[y*stride:(y+1)*stride] for y in range(height-1,-1,-1))
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(rows))+chunk(b'IEND',b'')
