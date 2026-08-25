static const float4 _154[11] = { float4(1.0f, 0.0f, 0.0f, 0.0f), float4(0.0f, 1.0f, 0.0f, 0.0f), float4(0.0f, 0.0f, 1.0f, 0.0f), float4(0.0f, 0.0f, 0.0f, 1.0f), float4(2.8025969286496341418474591665798e-45f, 1.4012984643248170709237295832899e-45f, -1.0f, 1.0f), float4(2.8025969286496341418474591665798e-45f, 1.4012984643248170709237295832899e-45f, 1.0f, 1.0f), float4(0.0f, 2.8025969286496341418474591665798e-45f, 1.0f, -1.0f), float4(0.0f, 2.8025969286496341418474591665798e-45f, 1.0f, 1.0f), float4(0.0f, 1.4012984643248170709237295832899e-45f, 1.0f, 1.0f), float4(0.0f, 1.4012984643248170709237295832899e-45f, -1.0f, 1.0f), 0.0f.xxxx };

ByteAddressBuffer _EndfieldBufferT0 : register(t0);
cbuffer EndfieldCB0 : register(b0) { float4 EndfieldCB0_f_0[45] : packoffset(c0); };
cbuffer EndfieldCB1 : register(b1) { float4 EndfieldCB1_f_0[157] : packoffset(c0); };
cbuffer EndfieldCB2 : register(b2) { float4 EndfieldCB2_f_0[259] : packoffset(c0); };
cbuffer EndfieldCB3 : register(b3) { float4 EndfieldCB3_f_0[3] : packoffset(c0); };
cbuffer EndfieldCB4 : register(b4) { float4 EndfieldCB4_f_0[2054] : packoffset(c0); };
cbuffer EndfieldCB5 : register(b5) { float4 EndfieldCB5_f_0[401] : packoffset(c0); };
cbuffer EndfieldCB6 : register(b6) { float4 EndfieldCB6_f_0[216] : packoffset(c0); };
cbuffer EndfieldCB7 : register(b7) { float4 EndfieldCB7_f_0[15] : packoffset(c0); };
cbuffer EndfieldCB8 : register(b8) { float4 EndfieldCB8_f_0[160] : packoffset(c0); };
cbuffer EndfieldCB9 : register(b9) { float4 EndfieldCB9_f_0[4] : packoffset(c0); };

Texture2D<float4> _EndfieldTextureT1 : register(t1);
Texture2D<float4> _EndfieldTextureT2 : register(t2);
Texture2D<float4> _EndfieldTextureT3 : register(t3);
Texture2D<float4> _EndfieldTextureT4 : register(t4);
Texture2DArray<float4> _EndfieldTextureT5 : register(t5);
Texture2D<float4> _EndfieldTextureT6 : register(t6);
Texture2D<float4> _EndfieldTextureT7 : register(t7);
Texture2D<float4> _EndfieldTextureT8 : register(t8);
Texture2D<float4> _EndfieldTextureT9 : register(t9);
Texture2D<float4> _EndfieldTextureT10 : register(t10);
Texture2DArray<float4> _EndfieldTextureT11 : register(t11);
Texture2DArray<float4> _EndfieldTextureT12 : register(t12);
Texture2D<float4> _EndfieldTextureT13 : register(t13);
Texture2D<float4> _EndfieldTextureT14 : register(t14);
Texture3D<float4> _EndfieldTextureT15 : register(t15);
Texture2D<float4> _EndfieldTextureT16 : register(t16);
Texture2D<float4> _EndfieldTextureT17 : register(t17);
Texture3D<float4> _EndfieldTextureT18 : register(t18);
Texture3D<float4> _EndfieldTextureT19 : register(t19);
Texture3D<float4> _EndfieldTextureT20 : register(t20);
Texture3D<float4> _EndfieldTextureT21 : register(t21);
Texture3D<float4> _EndfieldTextureT22 : register(t22);
Texture3D<float4> _EndfieldTextureT23 : register(t23);
Texture2D<float4> _EndfieldTextureT24 : register(t24);
Texture2D<float4> _EndfieldTextureT25 : register(t25);
Texture2D<float4> _EndfieldTextureT26 : register(t26);
Texture2D<float4> _EndfieldTextureT27 : register(t27);
SamplerState sampler_LinearClamp : register(s0);
SamplerState sampler_LinearRepeat : register(s1);
SamplerState sampler_LinearMirror : register(s2);
SamplerState sampler_LinearMirrorOnce : register(s3);
SamplerComparisonState sampler_PointClamp : register(s4);

static float4 gl_FragCoord;
static float2 TEXCOORD;
static float4 SV_Target;

struct SPIRV_Cross_Input
{
    float2 TEXCOORD : TEXCOORD1;
    float4 gl_FragCoord : SV_Position;
};

struct SPIRV_Cross_Output
{
    float4 SV_Target : SV_Target0;
};

uint spvPackHalf2x16(float2 value)
{
    uint2 Packed = f32tof16(value);
    return Packed.x | (Packed.y << 16);
}

float2 spvUnpackHalf2x16(uint value)
{
    return f16tof32(uint2(value & 0xffff, value >> 16));
}

uint spvBitfieldInsert(uint Base, uint Insert, uint Offset, uint Count)
{
    uint Mask = Count == 32 ? 0xffffffff : (((1u << Count) - 1) << (Offset & 31));
    return (Base & ~Mask) | ((Insert << Offset) & Mask);
}

uint2 spvBitfieldInsert(uint2 Base, uint2 Insert, uint Offset, uint Count)
{
    uint Mask = Count == 32 ? 0xffffffff : (((1u << Count) - 1) << (Offset & 31));
    return (Base & ~Mask) | ((Insert << Offset) & Mask);
}

uint3 spvBitfieldInsert(uint3 Base, uint3 Insert, uint Offset, uint Count)
{
    uint Mask = Count == 32 ? 0xffffffff : (((1u << Count) - 1) << (Offset & 31));
    return (Base & ~Mask) | ((Insert << Offset) & Mask);
}

uint4 spvBitfieldInsert(uint4 Base, uint4 Insert, uint Offset, uint Count)
{
    uint Mask = Count == 32 ? 0xffffffff : (((1u << Count) - 1) << (Offset & 31));
    return (Base & ~Mask) | ((Insert << Offset) & Mask);
}

uint spvBitfieldUExtract(uint Base, uint Offset, uint Count)
{
    uint Mask = Count == 32 ? 0xffffffff : ((1 << Count) - 1);
    return (Base >> Offset) & Mask;
}

uint2 spvBitfieldUExtract(uint2 Base, uint Offset, uint Count)
{
    uint Mask = Count == 32 ? 0xffffffff : ((1 << Count) - 1);
    return (Base >> Offset) & Mask;
}

uint3 spvBitfieldUExtract(uint3 Base, uint Offset, uint Count)
{
    uint Mask = Count == 32 ? 0xffffffff : ((1 << Count) - 1);
    return (Base >> Offset) & Mask;
}

uint4 spvBitfieldUExtract(uint4 Base, uint Offset, uint Count)
{
    uint Mask = Count == 32 ? 0xffffffff : ((1 << Count) - 1);
    return (Base >> Offset) & Mask;
}

int spvBitfieldSExtract(int Base, int Offset, int Count)
{
    int Mask = Count == 32 ? -1 : ((1 << Count) - 1);
    int Masked = (Base >> Offset) & Mask;
    int ExtendShift = (32 - Count) & 31;
    return (Masked << ExtendShift) >> ExtendShift;
}

int2 spvBitfieldSExtract(int2 Base, int Offset, int Count)
{
    int Mask = Count == 32 ? -1 : ((1 << Count) - 1);
    int2 Masked = (Base >> Offset) & Mask;
    int ExtendShift = (32 - Count) & 31;
    return (Masked << ExtendShift) >> ExtendShift;
}

int3 spvBitfieldSExtract(int3 Base, int Offset, int Count)
{
    int Mask = Count == 32 ? -1 : ((1 << Count) - 1);
    int3 Masked = (Base >> Offset) & Mask;
    int ExtendShift = (32 - Count) & 31;
    return (Masked << ExtendShift) >> ExtendShift;
}

int4 spvBitfieldSExtract(int4 Base, int Offset, int Count)
{
    int Mask = Count == 32 ? -1 : ((1 << Count) - 1);
    int4 Masked = (Base >> Offset) & Mask;
    int ExtendShift = (32 - Count) & 31;
    return (Masked << ExtendShift) >> ExtendShift;
}

float _160(float2 _158, float2 _159)
{
    precise float _164 = _158.x * _159.x;
    return mad(_158.y, _159.y, _164);
}

float _173(float3 _171, float3 _172)
{
    precise float _177 = _171.x * _172.x;
    return mad(_171.z, _172.z, mad(_171.y, _172.y, _177));
}

float _186(uint _185)
{
    return float(_185);
}

float _194(float4 _192, float4 _193)
{
    precise float _198 = _192.x * _193.x;
    return mad(_192.w, _193.w, mad(_192.z, _193.z, mad(_192.y, _193.y, _198)));
}

float _209(uint _208)
{
    return float(int(_208));
}

void frag_main()
{
    uint _219 = uint(gl_FragCoord.x);
    uint _220 = uint(gl_FragCoord.y);
    float4 _224 = _EndfieldTextureT25.Load(int3(uint2(_219, _220), 0u));
    float _226 = _224.x;
    float _227 = _224.y;
    float4 _232 = _EndfieldTextureT26.Load(int3(uint2(_219, _220), 0u));
    float _236 = _232.z;
    float4 _240 = _EndfieldTextureT27.Load(int3(uint2(_219, _220), 0u));
    float _242 = _240.x;
    float _243 = _240.y;
    float _244 = _240.z;
    float _245 = _240.w;
    uint _254 = uint(int(mad(round(_224.w * 3.0f), 4.0f, round(_232.w * 3.0f))));
    float _255 = mad(_232.x, 2.0f, -1.0f);
    float _257 = mad(_232.y, 2.0f, -1.0f);
    float _258 = abs(_255);
    float _259 = abs(_257);
    float _263 = 1.0f - _160(float2(_258, _259), 1.0f.xx);
    bool _265 = _263 < 0.0f;
    float _274 = _265 ? (((_255 >= 0.0f) ? 1.0f : (-1.0f)) * (1.0f - _259)) : _255;
    float _275 = _265 ? (((_257 >= 0.0f) ? 1.0f : (-1.0f)) * (1.0f - _258)) : _257;
    float3 _276 = float3(_274, _263, _275);
    float _278 = rsqrt(_173(_276, _276));
    float _279 = _278 * _274;
    float _280 = _278 * _263;
    float _281 = _278 * _275;
    float _282 = _186(_219);
    float _283 = _186(_220);
    uint4 _291 = asuint(EndfieldCB1_f_0[0u]);
    float _294 = asfloat(_291.z);
    float _295 = asfloat(_291.w);
    float _296 = (_282 + 0.5f) * _294;
    float _297 = (_283 + 0.5f) * _295;
    float _298 = gl_FragCoord.x * _294;
    float _299 = gl_FragCoord.y * _295;
    float _300 = mad(_298, 2.0f, -1.0f);
    float4 _307 = _EndfieldTextureT1.SampleLevel(sampler_LinearClamp, float2(_296, _297), 0.0f);
    float _309 = _307.x;
    float _314 = -mad(_299, 2.0f, -1.0f);
    uint4 _318 = asuint(EndfieldCB0_f_0[25u]);
    uint4 _334 = asuint(EndfieldCB0_f_0[24u]);
    uint4 _350 = asuint(EndfieldCB0_f_0[26u]);
    uint4 _366 = asuint(EndfieldCB0_f_0[27u]);
    float _378 = mad(asfloat(_350.w), _309, mad(asfloat(_334.w), _300, _314 * asfloat(_318.w))) + asfloat(_366.w);
    float _379 = (mad(asfloat(_350.x), _309, mad(asfloat(_334.x), _300, _314 * asfloat(_318.x))) + asfloat(_366.x)) / _378;
    float _380 = (mad(asfloat(_350.y), _309, mad(asfloat(_334.y), _300, _314 * asfloat(_318.y))) + asfloat(_366.y)) / _378;
    float _381 = (mad(asfloat(_350.z), _309, mad(asfloat(_334.z), _300, _314 * asfloat(_318.z))) + asfloat(_366.z)) / _378;
    float _387 = asfloat(asuint(EndfieldCB0_f_0[1u].z));
    float _393 = asfloat(asuint(EndfieldCB0_f_0[0u].z));
    float _399 = asfloat(asuint(EndfieldCB0_f_0[2u].z));
    bool _412 = asfloat(asuint(EndfieldCB1_f_0[4u].w)) == 0.0f;
    uint4 _416 = asuint(EndfieldCB0_f_0[44u]);
    float _426 = _412 ? (asfloat(_416.x) - _379) : _393;
    float _427 = _412 ? (asfloat(_416.y) - _380) : _387;
    float _428 = _412 ? (asfloat(_416.z) - _381) : _399;
    float3 _429 = float3(_426, _427, _428);
    float _430 = _173(_429, _429);
    float _433 = rsqrt(max(_430, 9.9999999392252902907785028219223e-09f));
    float _434 = _426 * _433;
    float _435 = _427 * _433;
    float _436 = _428 * _433;
    float _437 = _430 * _433;
    bool _443 = asfloat(asuint(EndfieldCB1_f_0[156u].x)) > 0.00048828125f;
    float _465 = 0.0f;
    float _466 = 0.0f;
    if (_443)
    {
        float4 _458 = _EndfieldTextureT24.SampleBias(sampler_LinearRepeat, float2(TEXCOORD.x, TEXCOORD.y), asfloat(asuint(EndfieldCB1_f_0[26u].x)));
        _465 = _458.x;
        _466 = _458.y;
    }
    else
    {
        _465 = 1.0f;
        _466 = 1.0f;
    }
    float _467 = min(_466, _465);
    float _472 = clamp((_224.z - 0.0500000007450580596923828125f) * 1.05260002613067626953125f, 0.0f, 1.0f);
    float _477 = _443 ? (1.0f - _472) : 1.0f;
    float _478 = min(_236, _443 ? mad(_472, _466 - 1.0f, 1.0f) : 1.0f);
    float _480 = mad(_467, _236 - _478, _478);
    float _482 = mad(_465, _236 - _480, _480);
    float _484 = mad(_467, 1.0f - _477, _477);
    float _486 = mad(_465, 1.0f - _484, _484);
    float _487 = _486 * _242;
    float _488 = _486 * _243;
    float _489 = _486 * _244;
    float _496 = mad(_242, _486, -(_226 * _487));
    float _497 = mad(_243, _486, -(_226 * _488));
    float _498 = mad(_244, _486, -(_226 * _489));
    float _500 = mad(-_226, 0.039999999105930328369140625f, 0.039999999105930328369140625f);
    float _502 = mad(_487, _226, _500);
    float _503 = mad(_488, _226, _500);
    float _504 = mad(_489, _226, _500);
    float3 _505 = float3(_279, _280, _281);
    float3 _506 = float3(_434, _435, _436);
    float _507 = _173(_505, _506);
    float _508 = max(_507, 0.0f);
    float _509 = _482 * _482;
    float _510 = _508 * _508;
    float _511 = _508 * _510;
    float _512 = _509 * _509;
    float2 _525 = float2(1.0f, _509);
    float3 _545 = float3(1.0f, _509, _509 * _512);
    float _547 = _160(float2(_160(float2(_508, 0.0365463010966777801513671875f), float2(3.3270699977874755859375f, 1.0f)), _160(float2(_508, 9.0631999969482421875f), float2(-9.0475597381591796875f, 1.0f))), _525) / _173(float3(_173(float3(_510, _511, 1.0f), float3(3.596849918365478515625f, -1.36772000789642333984375f, 1.0f)), _173(float3(_510, 9.044010162353515625f, _511), float3(-16.3173999786376953125f, 1.0f, 9.2294902801513671875f)), _173(float3(5.565889835357666015625f, _510, _511), float3(1.0f, 19.788600921630859375f, -20.212299346923828125f))), _545);
    float _579 = _160(float2(_160(float2(_508, 0.99044001102447509765625f), float2(-1.28514003753662109375f, 1.0f)), _160(float2(1.29677999019622802734375f, _508), float2(1.0f, -0.755906999111175537109375f))), _525) / _173(float3(_173(float3(_508, _511, 1.0f), float3(2.9233798980712890625f, 59.41880035400390625f, 1.0f)), _173(float3(20.3225002288818359375f, _508, _511), float3(1.0f, -27.0301990509033203125f, 222.5919952392578125f)), _173(float3(_508, _511, 121.5630035400390625f), float3(626.1300048828125f, 316.62701416015625f, 1.0f))), _545);
    float _580 = mad(_502, _547, _579);
    float _581 = mad(_503, _547, _579);
    float _582 = mad(_504, _547, _579);
    float _583 = _547 + _579;
    float4 _585 = _EndfieldTextureT7.Load(int3(uint2(_219, _220), 0u));
    float _587 = _585.x;
    float _595 = ddy_coarse(0.5f);
    float _596 = ddx_coarse(0.5f);
    float _597 = ddy_coarse(_587);
    float _598 = ddx_coarse(_587);
    float _712 = 0.0f;
    float _714 = 0.0f;
    float _716 = 0.0f;
    if (_587 > 0.001000000047497451305389404296875f)
    {
        float _599 = -_434;
        float _600 = -_435;
        float _601 = -_436;
        float _603 = _173(float3(_599, _600, _601), _505);
        float _605 = -(_603 + _603);
        float _606 = mad(_279, _605, _599);
        float _607 = mad(_280, _605, _600);
        float _608 = mad(_281, _605, _601);
        uint4 _611 = asuint(EndfieldCB4_f_0[0u]);
        float _615 = asfloat(_611.x);
        float _616 = asfloat(_611.y);
        float _617 = asfloat(_611.z);
        float _618 = -_615;
        float _619 = -_616;
        float _620 = -_617;
        float _623 = _173(float3(_618, _619, _620), float3(_606, _607, _608));
        float _624 = mad(_615, _623, _606);
        float _625 = mad(_616, _623, _607);
        float _626 = mad(_617, _623, _608);
        float _631 = asfloat(asuint(EndfieldCB4_f_0[4u].z));
        bool _632 = _623 < _631;
        float3 _633 = float3(_624, _625, _626);
        float _637 = rsqrt(max(_173(_633, _633), 6.103515625e-05f));
        float _645 = asfloat(asuint(EndfieldCB4_f_0[4u].y));
        float _649 = mad(_618, _631, (_637 * _624) * _645);
        float _650 = mad(_619, _631, (_637 * _625) * _645);
        float _651 = mad(_620, _631, (_637 * _626) * _645);
        float3 _652 = float3(_649, _650, _651);
        float _654 = rsqrt(_173(_652, _652));
        float _658 = _632 ? (_654 * _649) : _606;
        float _659 = _632 ? (_654 * _650) : _607;
        float _660 = _632 ? (_654 * _651) : _608;
        float _661 = mad(_426, _433, _658);
        float _662 = mad(_427, _433, _659);
        float _663 = mad(_428, _433, _660);
        float3 _664 = float3(_661, _662, _663);
        float _667 = rsqrt(max(_173(_664, _664), 6.103515625e-05f));
        float _672 = _173(float3(_658, _659, _660), _505);
        float _673 = clamp(_672, 0.0f, 1.0f);
        float3 _674 = float3(_667 * _661, _667 * _662, _667 * _663);
        float _676 = clamp(_173(_505, _674), 0.0f, 1.0f);
        float _677 = clamp(_507, 0.0f, 1.0f);
        float _680 = mad(mad(_676, _512, -_676), _676, 1.0f);
        float _683 = 1.0f - clamp(_173(_506, _674), 0.0f, 1.0f);
        float _684 = _683 * _683;
        float _685 = _684 * _684;
        float _686 = _683 * _685;
        float _687 = 1.0f - _482;
        float _696 = min(mad(_687, mad(_687, mad(_482 - 1.0f, 0.38302600383758544921875f, -0.076194703578948974609375f), 1.04997003078460693359375f), 0.4092549979686737060546875f), 0.999000012874603271484375f);
        float _698 = 1.0f - _696;
        float _702 = mad(1.0f - _502, 0.0476190485060214996337890625f, _502);
        float _704 = mad(1.0f - _503, 0.0476190485060214996337890625f, _503);
        float _705 = mad(1.0f - _504, 0.0476190485060214996337890625f, _504);
        bool _711 = (_245 > 0.0f) && ((_254 > 0u) && (_254 <= 15u));
        float _866 = 0.0f;
        float _867 = 0.0f;
        float _868 = 0.0f;
        if (_711)
        {
            uint _843 = min((_254 - 1u), 14u);
            uint _849 = (_843 * 4u) + 3u;
            float4 _859 = _EndfieldTextureT11.SampleLevel(sampler_LinearRepeat, float3(mad(_672, 0.5f, 0.5f), _245 * EndfieldCB7_f_0[_849 >> 2u][_849 & 3u], _186(_843)), 0.0f);
            _866 = _859.z;
            _867 = _859.y;
            _868 = _859.x;
        }
        else
        {
            _866 = _511;
            _867 = _510;
            _868 = 5.565889835357666015625f;
        }
        float _873 = mad(-_685, _683, 1.0f);
        float _892 = (_512 / (_680 * _680)) * (0.5f / (mad(_677, sqrt(mad(mad(-_673, _512, _673), _673, _512)), _673 * sqrt(mad(mad(-_677, _512, _677), _677, _512))) + 9.9999997473787516355514526367188e-05f));
        float _901 = mad(_482, 0.96875f, 0.015625f);
        float _924 = (_696 * (_EndfieldTextureT10.SampleLevel(sampler_LinearRepeat, float2(mad(_677, 0.96875f, 0.015625f), _901), 0.0f).x * _EndfieldTextureT10.SampleLevel(sampler_LinearRepeat, float2(mad(_673, 0.96875f, 0.015625f), _901), 0.0f).x)) / _698;
        float _946 = asfloat(asuint(EndfieldCB4_f_0[4u].x));
        uint4 _962 = asuint(EndfieldCB4_f_0[1u]);
        float _969 = mad(clamp((((_924 * (_702 * _702)) / mad(-_702, _698, 1.0f)) + min(_892 * mad(_502, _873, _686), 2048.0f)) * _946, 0.0f, 1000.0f), _673, _496 * (_711 ? _868 : _673)) * asfloat(_962.x);
        float _970 = mad(clamp((((_924 * (_704 * _704)) / mad(-_704, _698, 1.0f)) + min(_892 * mad(_503, _873, _686), 2048.0f)) * _946, 0.0f, 1000.0f), _673, _497 * (_711 ? _867 : _673)) * asfloat(_962.y);
        float _971 = mad(clamp((((_924 * (_705 * _705)) / mad(-_705, _698, 1.0f)) + min(_892 * mad(_504, _873, _686), 2048.0f)) * _946, 0.0f, 1000.0f), _673, _498 * (_711 ? _866 : _673)) * asfloat(_962.z);
        float _978 = exp2(asfloat(asuint(EndfieldCB1_f_0[26u].x)));
        float4 _986 = _EndfieldTextureT9.SampleGrad(sampler_LinearRepeat, float2(_587, 0.5f), float2(_598 * _978, _596 * _978), float2(_597 * _978, _595 * _978));
        float _995 = 1.0f - _587;
        float _1014 = min(_EndfieldTextureT13.SampleLevel(sampler_LinearRepeat, float2(_298, _299), 0.0f).x, 1.0f);
        _712 = _1014 * mad(_995, mad(_969, _986.x, -_969), _969);
        _714 = _1014 * mad(_995, mad(_970, _986.y, -_970), _970);
        _716 = _1014 * mad(_995, mad(_971, _986.z, -_971), _971);
    }
    else
    {
        _712 = 0.0f;
        _714 = 0.0f;
        _716 = 0.0f;
    }
    uint _731 = uint(int(mad(floor(_283 * 0.03125f), asfloat(asuint(EndfieldCB3_f_0[1u].y)), floor(_282 * 0.03125f)) * 8.0f));
    float _742 = abs(mad(_399, _381, mad(_393, _379, _380 * _387)) + asfloat(asuint(EndfieldCB0_f_0[3u].z)));
    float _744 = floor(mad(-asfloat(asuint(EndfieldCB1_f_0[3u].y)), asfloat(asuint(EndfieldCB3_f_0[2u].w)), _742));
    float _752 = min(asfloat(asuint(EndfieldCB3_f_0[1u].w)) - 1.0f, max(_744, 0.0f));
    float _760 = asfloat(asuint(EndfieldCB1_f_0[26u].x));
    float4 _762 = _EndfieldTextureT8.SampleBias(sampler_LinearRepeat, float2(_296, _297), _760);
    float4 _768 = float4(_762);
    bool _769 = _752 >= _744;
    uint _776 = uint(int(_752 * 8.0f)) + asuint(EndfieldCB1_f_0[28u].y);
    float _777 = -_434;
    float _778 = -_435;
    float _779 = -_436;
    float3 _780 = float3(_777, _778, _779);
    float _781 = _173(_780, _505);
    float _783 = -(_781 + _781);
    float _784 = mad(_279, _783, _777);
    float _785 = mad(_280, _783, _778);
    float _786 = mad(_281, _783, _779);
    float _787 = clamp(_507, 0.0f, 1.0f);
    float _788 = 1.0f - _482;
    float _793 = min(mad(_788, mad(_788, mad(_482 - 1.0f, 0.38302600383758544921875f, -0.076194703578948974609375f), 1.04997003078460693359375f), 0.4092549979686737060546875f), 0.999000012874603271484375f);
    float _794 = 1.0f - _793;
    float _798 = mad(1.0f - _502, 0.0476190485060214996337890625f, _502);
    float _799 = mad(1.0f - _503, 0.0476190485060214996337890625f, _503);
    float _800 = mad(1.0f - _504, 0.0476190485060214996337890625f, _504);
    bool _805 = (_245 > 0.0f) && ((_254 > 0u) && (_254 <= 15u));
    uint _807 = min((_254 - 1u), 14u);
    uint _813 = (_807 * 4u) + 3u;
    float _816 = _245 * EndfieldCB7_f_0[_813 >> 2u][_813 & 3u];
    float _817 = _186(_807);
    float _821 = mad(_482, 0.96875f, 0.015625f);
    float4 _825 = _EndfieldTextureT10.SampleLevel(sampler_LinearRepeat, float2(mad(_787, 0.96875f, 0.015625f), _821), 0.0f);
    float _827 = _825.x;
    float _835 = mad(-_798, _794, 1.0f);
    float _836 = mad(-_799, _794, 1.0f);
    float _837 = mad(-_800, _794, 1.0f);
    float _838 = _798 * _798;
    float _839 = _799 * _799;
    float _840 = _800 * _800;
    float3 _841 = float3(_784, _785, _786);
    float _1015 = 0.0f;
    float _1017 = 0.0f;
    float _1019 = 0.0f;
    float _1021 = 0.0f;
    _1015 = 0.0f;
    _1017 = 0.0f;
    _1019 = 0.0f;
    _1021 = 1.0f;
    float _1016 = 0.0f;
    float _1018 = 0.0f;
    float _1020 = 0.0f;
    uint _1024 = 0u;
    float _1022 = 0.0f;
    uint _1023 = 0u;
    for (;;)
    {
        if (int(_1023) > int(7u))
        {
            break;
        }
        uint _1036 = _769 ? (_EndfieldBufferT0.Load((_776 + _1023) * 4 + 0) & _EndfieldBufferT0.Load((_731 + _1023) * 4 + 0)) : 0u;
        uint _1037 = _1023 << 5u;
        float _1051 = 0.0f;
        float _1053 = 0.0f;
        float _1055 = 0.0f;
        _1051 = 0.0f;
        _1053 = 0.0f;
        _1055 = 0.0f;
        _1022 = _1021;
        uint _1059 = 0u;
        float _1052 = 0.0f;
        float _1054 = 0.0f;
        float _1056 = 0.0f;
        float _1057 = 0.0f;
        uint _1058 = _1036;
        for (;;)
        {
            if (_1058 == 0u)
            {
                break;
            }
            uint _1217 = firstbitlow(_1058);
            _1059 = (1u << (_1217 & 31u)) ^ _1058;
            uint _1221 = _1037 + _1217;
            uint _1222 = spvBitfieldInsert(1u, _1221, 3u, 29u);
            uint _1224 = spvBitfieldInsert(3u, _1221, 3u, 29u);
            uint _1225 = spvBitfieldInsert(5u, _1221, 3u, 29u);
            uint _1226 = spvBitfieldInsert(6u, _1221, 3u, 29u);
            uint _1227 = spvBitfieldInsert(7u, _1221, 3u, 29u);
            uint _1234 = (((16u * _1225) + 96u) + 12u) >> 2u;
            uint _1239 = uint(asfloat(asuint(EndfieldCB4_f_0[_1234 >> 2u][_1234 & 3u])));
            float _1470 = 0.0f;
            if ((_1239 & 1u) == 1u)
            {
                uint4 _1399 = asuint(EndfieldCB4_f_0[_1222 + 6u]);
                uint4 _1411 = asuint(EndfieldCB4_f_0[_1225 + 6u]);
                uint4 _1418 = asuint(EndfieldCB4_f_0[_1226 + 6u]);
                float4 _1440 = float4(_379 - asfloat(_1399.x), _380 - asfloat(_1399.y), _381 - asfloat(_1399.z), 1.0f);
                uint _1457 = (((16u * _1227) + 96u) + 0u) >> 2u;
                float _1461 = asfloat(asuint(EndfieldCB4_f_0[_1457 >> 2u][_1457 & 3u]));
                float _1468 = 1.0f - clamp((max(abs(_194(_1440, float4(spvUnpackHalf2x16(_1418.y), spvUnpackHalf2x16(_1418.z)))), max(abs(_194(_1440, float4(spvUnpackHalf2x16(_1411.x), spvUnpackHalf2x16(_1411.y)))), abs(_194(_1440, float4(spvUnpackHalf2x16(_1411.z), spvUnpackHalf2x16(_1418.x)))))) - mad(_1461, 0.5f, 0.5f)) / mad(-_1461, 0.5f, 0.5f), 0.0f, 1.0f);
                _1470 = _1468 * _1468;
            }
            else
            {
                _1470 = 1.0f;
            }
            uint _1477 = (((16u * _1224) + 96u) + 8u) >> 2u;
            bool _1482 = asfloat(asuint(EndfieldCB4_f_0[_1477 >> 2u][_1477 & 3u])) > 0.5f;
            if (_1482 || (_1470 < 0.001000000047497451305389404296875f))
            {
                _1057 = _1022;
                _1056 = _1055;
                _1054 = _1053;
                _1052 = _1051;
                _1051 = _1052;
                _1053 = _1054;
                _1055 = _1056;
                _1022 = _1057;
                _1058 = _1059;
                continue;
            }
            uint _1768 = _1221 << 3u;
            uint _1769 = spvBitfieldInsert(2u, _1221, 3u, 29u);
            uint _1775 = (((16u * _1768) + 96u) + 12u) >> 2u;
            float _1779 = asfloat(asuint(EndfieldCB4_f_0[_1775 >> 2u][_1775 & 3u]));
            float _1928 = 0.0f;
            float _2449 = 0.0f;
            float _2451 = 0.0f;
            float _2453 = 0.0f;
            if (_1779 < 1.5f)
            {
                uint _1937 = (((16u * _1769) + 96u) + 4u) >> 2u;
                float _1941 = asfloat(asuint(EndfieldCB4_f_0[_1937 >> 2u][_1937 & 3u]));
                float _1942 = mad(_1941, 0.5f, 0.5f);
                uint _1947 = (((16u * _1769) + 96u) + 0u) >> 2u;
                float _1951 = asfloat(asuint(EndfieldCB4_f_0[_1947 >> 2u][_1947 & 3u]));
                float _1952 = abs(_1951);
                float _1953 = _1942 - _1952;
                float _1955 = (_1952 - _1942) + _1941;
                float _1960 = max((1.0f - abs(_1953)) - abs(_1955), 0.00048828125f);
                float _1963 = (_1951 >= 0.0f) ? _1960 : (-_1960);
                float3 _1964 = float3(_1953, _1955, _1963);
                float _1966 = rsqrt(_173(_1964, _1964));
                float _1967 = _1966 * _1953;
                float _1968 = _1966 * _1955;
                float _1969 = _1966 * _1963;
                uint4 _1973 = asuint(EndfieldCB4_f_0[_1222 + 6u]);
                float _1977 = asfloat(_1973.x);
                float _1978 = asfloat(_1973.y);
                float _1979 = asfloat(_1973.z);
                float _1980 = _1977 - _379;
                float _1981 = _1978 - _380;
                float _1982 = _1979 - _381;
                float3 _1983 = float3(_1980, _1981, _1982);
                float _1984 = _173(_1983, _1983);
                float _1985 = rsqrt(_1984);
                float _1986 = _1985 * _1980;
                float _1987 = _1985 * _1981;
                float _1988 = _1985 * _1982;
                uint _1994 = (((16u * _1227) + 96u) + 12u) >> 2u;
                uint _1999 = uint(int(asfloat(asuint(EndfieldCB4_f_0[_1994 >> 2u][_1994 & 3u]))));
                uint _2005 = (((16u * _1769) + 96u) + 8u) >> 2u;
                float _2009 = asfloat(asuint(EndfieldCB4_f_0[_2005 >> 2u][_2005 & 3u]));
                float _2010 = _1967 * _2009;
                float _2011 = _1968 * _2009;
                float _2012 = _1969 * _2009;
                float _2013 = -_2010;
                float _2014 = -_2011;
                float _2015 = -_2012;
                float _2016 = mad(_2013, 0.5f, _1980);
                float _2017 = mad(_2014, 0.5f, _1981);
                float _2018 = mad(_2015, 0.5f, _1982);
                uint _2023 = uint(_1779) & 1u;
                bool _2024 = _2023 == 0u;
                bool _2027 = (!_2024) && (_2009 > 0.0f);
                float3 _2028 = float3(_2016, _2017, _2018);
                float _2030 = sqrt(_173(_2028, _2028));
                float3 _2031 = float3(mad(_2010, 0.5f, _1980), mad(_2011, 0.5f, _1981), mad(_2012, 0.5f, _1982));
                float _2033 = sqrt(_173(_2031, _2031));
                float3 _2045 = float3(_1986, _1987, _1988);
                float _2049 = _2027 ? clamp(((_173(_505, _2031) / _2033) + (_173(_505, _2028) / _2030)) * 0.5f, 0.0f, 1.0f) : clamp(_173(_505, _2045), 0.0f, 1.0f);
                float _2050 = _2027 ? (1.0f / mad(mad(_2030, _2033, _173(_2028, _2031)), 0.5f, 1.0f)) : 1.0f;
                uint _2056 = (((16u * _1226) + 96u) + 12u) >> 2u;
                float _2060 = asfloat(asuint(EndfieldCB4_f_0[_2056 >> 2u][_2056 & 3u]));
                float _2386 = 0.0f;
                if (_2060 < 0.0f)
                {
                    uint _2195 = (((16u * _1222) + 96u) + 12u) >> 2u;
                    float _2199 = asfloat(asuint(EndfieldCB4_f_0[_2195 >> 2u][_2195 & 3u]));
                    float _2201 = (_2199 * _2199) * _1984;
                    float _2204 = max(mad(-_2201, _2201, 1.0f), 0.0f);
                    float _2206 = 1.0f / (_1984 + 1.0f);
                    _2386 = (_2204 * _2204) * (_2027 ? ((_2050 - _2206) + _2206) : _2206);
                }
                else
                {
                    uint _2215 = (((16u * _1222) + 96u) + 12u) >> 2u;
                    float _2219 = asfloat(asuint(EndfieldCB4_f_0[_2215 >> 2u][_2215 & 3u]));
                    float3 _2223 = float3(_1980 * _2219, _1981 * _2219, _1982 * _2219);
                    _2386 = _2050 * exp2(log2(1.0f - min(_173(_2223, _2223), 1.0f)) * _2060);
                }
                uint _2397 = (((16u * _1769) + 96u) + 12u) >> 2u;
                uint _2400 = asuint(EndfieldCB4_f_0[_2397 >> 2u][_2397 & 3u]);
                float _2403 = clamp((_173(_2045, float3(-_1967, -_1968, -_1969)) - _2009) * asfloat(_2400), 0.0f, 1.0f);
                float _2407 = _2386 * ((_2023 != 0u) ? 1.0f : (_2403 * _2403));
                float _2495 = 0.0f;
                float _2497 = 0.0f;
                float _2499 = 0.0f;
                float _2501 = 0.0f;
                if ((!_2027) && (int(_1999) >= int(0u)))
                {
                    float _2496 = 0.0f;
                    float _2498 = 0.0f;
                    float _2500 = 0.0f;
                    float _3262 = 0.0f;
                    float _3263 = 0.0f;
                    if (_2024)
                    {
                        uint _2873 = _1999 << 2u;
                        uint _2874 = _2873 + 33u;
                        uint _2885 = (((16u * _2873) + 528u) + 12u) >> 2u;
                        uint _2891 = _2873 + 32u;
                        uint _2902 = (((16u * _2873) + 512u) + 12u) >> 2u;
                        uint _2908 = _2873 + 34u;
                        uint _2919 = (((16u * _2873) + 544u) + 12u) >> 2u;
                        uint _2925 = _2873 + 35u;
                        uint _2936 = (((16u * _2873) + 560u) + 12u) >> 2u;
                        float _2941 = mad(EndfieldCB8_f_0[_2919 >> 2u][_2919 & 3u], _381, mad(EndfieldCB8_f_0[_2902 >> 2u][_2902 & 3u], _379, _380 * EndfieldCB8_f_0[_2885 >> 2u][_2885 & 3u])) + EndfieldCB8_f_0[_2936 >> 2u][_2936 & 3u];
                        _2496 = _2941;
                        _2498 = _1981;
                        _2500 = _1982;
                        _3262 = mad(clamp((mad(EndfieldCB8_f_0[_2908].y, _381, mad(EndfieldCB8_f_0[_2891].y, _379, _380 * EndfieldCB8_f_0[_2874].y)) + EndfieldCB8_f_0[_2925].y) / _2941, 0.0f, 1.0f), EndfieldCB8_f_0[_1999].w, EndfieldCB8_f_0[_1999].y);
                        _3263 = mad(clamp((mad(EndfieldCB8_f_0[_2908].x, _381, mad(EndfieldCB8_f_0[_2891].x, _379, _380 * EndfieldCB8_f_0[_2874].x)) + EndfieldCB8_f_0[_2925].x) / _2941, 0.0f, 1.0f), EndfieldCB8_f_0[_1999].z, EndfieldCB8_f_0[_1999].x);
                    }
                    else
                    {
                        uint _2954 = _1999 << 2u;
                        float3 _2958 = float3(_379 - _1977, _380 - _1978, _381 - _1979);
                        float _2966 = _173(_2958, float3(EndfieldCB8_f_0[_2954 + 32u].xyz));
                        float _2974 = _173(_2958, float3(EndfieldCB8_f_0[_2954 + 33u].xyz));
                        float _2982 = _173(_2958, float3(EndfieldCB8_f_0[_2954 + 34u].xyz));
                        float _2983 = abs(_2966);
                        float _2984 = abs(_2974);
                        uint _2986 = uint(_2983 < _2984);
                        uint _2999 = (_160(float2(_2983, _2984), float2(_154[_2986].x, _154[_2986].y)) < abs(_2982)) ? 2u : _2986;
                        float3 _3000 = float3(_2966, _2974, _2982);
                        uint _3001 = min(_2999, 10u);
                        uint _3015 = spvBitfieldInsert((_173(_3000, float3(_154[_3001].x, _154[_3001].y, _154[_3001].z)) < 0.0f) ? 4294967295u : 0u, _2999, 1u, 31u);
                        uint _3017 = min((_3015 >> 1u), 10u);
                        uint _3033 = (_1999 * 4u) + 3u;
                        float _3038 = 0.5f - (0.000244140625f / EndfieldCB8_f_0[_3033 >> 2u][_3033 & 3u]);
                        uint _3041 = (_3015 < 2u) ? 2u : 0u;
                        uint _3052 = min((_3015 + 4u), 10u);
                        float _3057 = abs(_173(_3000, float3(_154[_3017].x, _154[_3017].y, _154[_3017].z)));
                        uint _3070 = min((asuint(_154[_3052].y) - 1u), 10u);
                        float _3078 = _160(float2(_2974, _2982), float2(_154[_3070].x, _154[_3070].y));
                        float _3086 = clamp(mad(-((_3078 * _154[_3052].w) / _3057), _3038, 0.5f), 0.0f, 1.0f);
                        _2496 = _3038;
                        _2498 = _3086;
                        _2500 = _3078;
                        _3262 = mad(_3086, EndfieldCB8_f_0[_1999].w, EndfieldCB8_f_0[_1999].y);
                        _3263 = mad(clamp((mad((_160(float2(_2966, _2982), float2(_154[_3041].x, _154[_3041].z)) * _154[_3052].z) / _3057, _3038, _186(_3015)) + 0.5f) * 0.16666667163372039794921875f, 0.0f, 1.0f), EndfieldCB8_f_0[_1999].z, EndfieldCB8_f_0[_1999].x);
                    }
                    _2495 = _2496;
                    _2497 = _2498;
                    _2499 = _2500;
                    _2501 = _2407 * _EndfieldTextureT14.SampleLevel(sampler_LinearRepeat, float2(_3263, _3262), 0.0f).x;
                }
                else
                {
                    _2495 = _1969;
                    _2497 = _1981;
                    _2499 = _1982;
                    _2501 = _2407;
                }
                bool _2503 = _2501 > 0.0f;
                float _3098 = 0.0f;
                float _3100 = 0.0f;
                float _3102 = 0.0f;
                float _3104 = 0.0f;
                if (_2503)
                {
                    bool _3097 = _2024 || ((_1239 & 2u) != 0u);
                    float _4033 = 0.0f;
                    float _4034 = 0.0f;
                    float _4035 = 0.0f;
                    uint _4036 = 0u;
                    uint _4037 = 0u;
                    if (_3097)
                    {
                        uint _3277 = (((16u * _1224) + 96u) + 0u) >> 2u;
                        _4033 = _2495;
                        _4034 = _2497;
                        _4035 = _2499;
                        _4036 = _1999;
                        _4037 = uint(int(asfloat(asuint(EndfieldCB4_f_0[_3277 >> 2u][_3277 & 3u]))));
                    }
                    else
                    {
                        float _3283 = _379 - _1977;
                        float _3284 = _380 - _1978;
                        float _3285 = _381 - _1979;
                        float _3286 = abs(_3284);
                        float _3287 = abs(_3285);
                        float _3288 = abs(_3283);
                        bool _3291 = _3287 < _3286;
                        bool _3292 = (_3286 < _3288) && (_3287 < _3288);
                        bool _3295 = _3285 > 0.0f;
                        uint _3300 = (_3283 > 0.0f) ? (_2400 >> 24u) : spvBitfieldUExtract(_2400, 16u, 8u);
                        uint _3303 = (_3284 > 0.0f) ? spvBitfieldUExtract(_2400, 8u, 8u) : (_2400 & 255u);
                        uint _3307 = (((16u * _1224) + 96u) + 0u) >> 2u;
                        uint _3310 = asuint(EndfieldCB4_f_0[_3307 >> 2u][_3307 & 3u]);
                        uint _3312 = _3310 & 255u;
                        uint _3313 = _3295 ? spvBitfieldUExtract(_3310, 8u, 8u) : _3312;
                        bool _3327 = (((_3291 && (int(_3303) < int(80u))) || ((int(_3313) < int(80u)) && (!_3291))) && (!_3292)) || (_3292 && (int(_3300) < int(80u)));
                        _4033 = _3327 ? asfloat(0xffffffffu /* nan */) : 0.0f;
                        _4034 = asfloat(_3313);
                        _4035 = _3295 ? asfloat(0xffffffffu /* nan */) : 0.0f;
                        _4036 = _3312;
                        _4037 = _3327 ? (_3292 ? _3300 : (_3291 ? _3303 : _3313)) : 4294967295u;
                    }
                    uint _4045 = (((16u * _4037) + 2560u) + 4u) >> 2u;
                    uint _4048 = asuint(EndfieldCB6_f_0[_4045 >> 2u][_4045 & 3u]);
                    bool _4049 = _4048 != 0u;
                    float _4256 = 0.0f;
                    if (_4049)
                    {
                        float _4257 = 0.0f;
                        if (_4049)
                        {
                            uint _4430 = min((_4048 - 1u), 10u);
                            _4257 = _194(_768, float4(_154[_4430].x, _154[_4430].y, _154[_4430].z, _154[_4430].w));
                        }
                        else
                        {
                            _4257 = 1.0f;
                        }
                        _4256 = _4257;
                    }
                    else
                    {
                        _4256 = _4033;
                    }
                    float _3099 = 0.0f;
                    float _3101 = 0.0f;
                    float _3103 = 0.0f;
                    float _4741 = 0.0f;
                    if (_4048 <= 0u)
                    {
                        uint _4445 = _4037 << 2u;
                        uint _4453 = (((16u * _4037) + 4608u) + 0u) >> 2u;
                        uint _5225 = _4453 >> 2u;
                        uint _5226 = _4453 & 3u;
                        uint _4463 = (((16u * _4037) + 4608u) + 4u) >> 2u;
                        float _4466 = EndfieldCB5_f_0[_4463 >> 2u][_4463 & 3u] * 5.0f;
                        float _4468 = mad(_279, _4466, mad(_1986, EndfieldCB5_f_0[_5225][_5226], _379));
                        float _4469 = mad(_280, _4466, mad(_1987, EndfieldCB5_f_0[_5225][_5226], _380));
                        float _4470 = mad(_281, _4466, mad(_1988, EndfieldCB5_f_0[_5225][_5226], _381));
                        uint _4471 = _4445 + 65u;
                        uint _4483 = _4445 + 64u;
                        uint _4495 = _4445 + 66u;
                        uint _4507 = _4445 + 67u;
                        float _4518 = mad(EndfieldCB5_f_0[_4495].w, _4470, mad(EndfieldCB5_f_0[_4483].w, _4468, _4469 * EndfieldCB5_f_0[_4471].w)) + EndfieldCB5_f_0[_4507].w;
                        float _4519 = (mad(EndfieldCB5_f_0[_4495].x, _4470, mad(EndfieldCB5_f_0[_4483].x, _4468, _4469 * EndfieldCB5_f_0[_4471].x)) + EndfieldCB5_f_0[_4507].x) / _4518;
                        float _4520 = (mad(EndfieldCB5_f_0[_4495].y, _4470, mad(EndfieldCB5_f_0[_4483].y, _4468, _4469 * EndfieldCB5_f_0[_4471].y)) + EndfieldCB5_f_0[_4507].y) / _4518;
                        float _4521 = (mad(EndfieldCB5_f_0[_4495].z, _4470, mad(EndfieldCB5_f_0[_4483].z, _4468, _4469 * EndfieldCB5_f_0[_4471].z)) + EndfieldCB5_f_0[_4507].z) / _4518;
                        uint _4528 = _4037 + 344u;
                        float _4538 = mad(_4519, EndfieldCB5_f_0[_4528].z - EndfieldCB5_f_0[_4528].x, EndfieldCB5_f_0[_4528].x);
                        float _4539 = mad(_4520, EndfieldCB5_f_0[_4528].w - EndfieldCB5_f_0[_4528].y, EndfieldCB5_f_0[_4528].y);
                        float _4547 = floor(mad(_4538, EndfieldCB5_f_0[400u].z, 0.5f));
                        float _4548 = floor(mad(_4539, EndfieldCB5_f_0[400u].w, 0.5f));
                        float _4551 = mad(_4538, EndfieldCB5_f_0[400u].z, -_4547);
                        float _4552 = mad(_4539, EndfieldCB5_f_0[400u].w, -_4548);
                        float _4553 = _4551 + 0.5f;
                        float _4554 = _4551 + 1.0f;
                        float _4555 = _4552 + 0.5f;
                        float _4556 = _4552 + 1.0f;
                        float _4557 = _4553 * _4553;
                        float _4558 = _4555 * _4555;
                        float _4561 = 1.0f - _4551;
                        float _4562 = 1.0f - _4552;
                        float _4563 = min(_4551, 0.0f);
                        float _4564 = min(_4552, 0.0f);
                        float _4565 = max(_4551, 0.0f);
                        float _4566 = max(_4552, 0.0f);
                        float _4567 = _4561 * 0.1599999964237213134765625f;
                        float _4569 = _4562 * 0.1599999964237213134765625f;
                        float _4576 = (mad(-_4565, _4565, _4554) + 1.0f) * 0.1599999964237213134765625f;
                        float _4577 = (mad(-_4566, _4566, _4556) + 1.0f) * 0.1599999964237213134765625f;
                        float _4578 = _4557 * 0.07999999821186065673828125f;
                        float _4580 = _4558 * 0.07999999821186065673828125f;
                        float _4590 = _4576 + ((mad(-_4563, _4563, _4561) + 1.0f) * 0.1599999964237213134765625f);
                        float _4591 = mad(_4554, 0.1599999964237213134765625f, _4578);
                        float _4592 = mad(mad(_4557, 0.5f, -_4551), 0.1599999964237213134765625f, _4567);
                        float _4593 = mad(mad(_4558, 0.5f, -_4552), 0.1599999964237213134765625f, _4569);
                        float _4594 = mad(mad(-_4564, _4564, _4562) + 1.0f, 0.1599999964237213134765625f, _4577);
                        float _4595 = mad(_4556, 0.1599999964237213134765625f, _4580);
                        float _4623 = mad(_4547, EndfieldCB5_f_0[400u].x, ((_4567 / _4592) - 2.5f) * EndfieldCB5_f_0[400u].x);
                        float _4624 = mad(_4548, EndfieldCB5_f_0[400u].y, ((_4569 / _4593) - 2.5f) * EndfieldCB5_f_0[400u].y);
                        float _4625 = mad(_4547, EndfieldCB5_f_0[400u].x, ((_4576 / _4590) - 0.5f) * EndfieldCB5_f_0[400u].x);
                        float _4626 = mad(_4547, EndfieldCB5_f_0[400u].x, ((_4578 / _4591) + 1.5f) * EndfieldCB5_f_0[400u].x);
                        float _4627 = mad(_4548, EndfieldCB5_f_0[400u].y, ((_4577 / _4594) - 0.5f) * EndfieldCB5_f_0[400u].y);
                        float _4628 = mad(_4548, EndfieldCB5_f_0[400u].y, ((_4580 / _4595) + 1.5f) * EndfieldCB5_f_0[400u].y);
                        uint _4716 = (((16u * _4037) + 4608u) + 8u) >> 2u;
                        float _4720 = (EndfieldCB5_f_0[_4716 >> 2u][_4716 & 3u] - _4518) * 0.25f;
                        float _4725 = clamp(min(min(min(_4520, 1.0f - _4520), min(_4519, 1.0f - _4519)), _4720) * 20.0f, 0.0f, 1.0f);
                        float _4726 = mad(_4725, -2.0f, 3.0f);
                        uint _4733 = (((16u * _4037) + 4608u) + 12u) >> 2u;
                        uint _5231 = _4733 >> 2u;
                        uint _5232 = _4733 & 3u;
                        float _4738 = mad(_4591 * _4595, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4626, _4628), _4521).xxxx.x, mad(_4590 * _4595, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4625, _4628), _4521).xxxx.x, mad(_4592 * _4595, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4623, _4628), _4521).xxxx.x, mad(_4591 * _4594, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4626, _4627), _4521).xxxx.x, mad(_4590 * _4594, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4625, _4627), _4521).xxxx.x, mad(_4592 * _4594, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4623, _4627), _4521).xxxx.x, mad(_4591 * _4593, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4626, _4624), _4521).xxxx.x, mad(_4592 * _4593, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4623, _4624), _4521).xxxx.x, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4625, _4624), _4521).xxxx.x * (_4590 * _4593))))))))) - 1.0f;
                        _3099 = _4726;
                        _3101 = _4720;
                        _3103 = _4518;
                        _4741 = (((asuint(_4521) & 2147483647u) > 2139095040u) || ((((_4519 <= 0.0f) || (_4519 >= 1.0f)) || ((_4520 >= 1.0f) || (_4520 <= 0.0f))) || ((_4521 <= 0.0f) || (_4521 >= 1.0f)))) ? 1.0f : mad(_3097 ? min((_4725 * _4725) * _4726, EndfieldCB5_f_0[_5231][_5232]) : EndfieldCB5_f_0[_5231][_5232], _4738, 1.0f);
                    }
                    else
                    {
                        _3099 = _4034;
                        _3101 = _4035;
                        _3103 = asfloat(_4036);
                        _4741 = _4256;
                    }
                    _3098 = _3099;
                    _3100 = _3101;
                    _3102 = _3103;
                    _3104 = (int(_4037) >= int(0u)) ? _4741 : 1.0f;
                }
                else
                {
                    _3098 = _2497;
                    _3100 = _2499;
                    _3102 = asfloat(_1999);
                    _3104 = 1.0f;
                }
                float _3356 = 0.0f;
                float _3357 = 0.0f;
                float _3358 = 0.0f;
                float _3359 = 0.0f;
                float _3360 = 0.0f;
                float _3361 = 0.0f;
                if (_2027)
                {
                    float _3331 = _173(_841, float3(_2010, _2011, _2012));
                    float _3346 = clamp(_173(_2028, float3(mad(_784, _3331, _2013), mad(_785, _3331, _2014), mad(_786, _3331, _2015))) / mad(_2009, _2009, -(_3331 * _3331)), 0.0f, 1.0f);
                    float _3347 = mad(_2010, _3346, _2016);
                    float _3348 = mad(_2011, _3346, _2017);
                    float _3349 = mad(_2012, _3346, _2018);
                    float3 _3350 = float3(_3347, _3348, _3349);
                    float _3352 = rsqrt(_173(_3350, _3350));
                    _3356 = _3348;
                    _3357 = _3349;
                    _3358 = _509 / min(mad(clamp(_1985 * _2009, 0.0f, 1.0f), 0.5f, _509), 1.0f);
                    _3359 = _3352 * _3349;
                    _3360 = _3352 * _3348;
                    _3361 = _3352 * _3347;
                }
                else
                {
                    _3356 = _3098;
                    _3357 = _3100;
                    _3358 = 1.0f;
                    _3359 = _1988;
                    _3360 = _1987;
                    _3361 = _1986;
                }
                float _2450 = 0.0f;
                float _2452 = 0.0f;
                float _2454 = 0.0f;
                if (_2503)
                {
                    uint _4054 = (((16u * _1227) + 96u) + 4u) >> 2u;
                    float _4060 = clamp(_1985 * asfloat(asuint(EndfieldCB4_f_0[_4054 >> 2u][_4054 & 3u])), 0.0f, 1.0f);
                    float _4061 = mad(_426, _433, _3361);
                    float _4062 = mad(_427, _433, _3360);
                    float _4063 = mad(_428, _433, _3359);
                    float3 _4064 = float3(_4061, _4062, _4063);
                    float _4067 = rsqrt(max(_173(_4064, _4064), 6.103515625e-05f));
                    float3 _4071 = float3(_4061 * _4067, _4062 * _4067, _4063 * _4067);
                    float _4073 = clamp(_173(_505, _4071), 0.0f, 1.0f);
                    float _4075 = clamp(_173(_506, _4071), 0.0f, 1.0f);
                    float _4084 = (_4060 > 0.0f) ? min(mad(_482, _482, (_4060 * _4060) / mad(_4075, 3.599999904632568359375f, 0.4000000059604644775390625f)), 1.0f) : _509;
                    float _4085 = _4084 * _4084;
                    float _4088 = mad(mad(_4073, _4085, -_4073), _4073, 1.0f);
                    float _4089 = 1.0f - _4075;
                    float _4090 = _4089 * _4089;
                    float _4091 = _4090 * _4090;
                    float _4092 = _4089 * _4091;
                    float _4272 = 0.0f;
                    float _4273 = 0.0f;
                    float _4274 = 0.0f;
                    if (_805)
                    {
                        float4 _4265 = _EndfieldTextureT11.SampleLevel(sampler_LinearRepeat, float3(mad(_173(_505, float3(_3361, _3360, _3359)), 0.5f, 0.5f), _816, _817), 0.0f);
                        _4272 = _4265.z;
                        _4273 = _4265.y;
                        _4274 = _4265.x;
                    }
                    else
                    {
                        _4272 = _3102;
                        _4273 = _3357;
                        _4274 = _3356;
                    }
                    float _4279 = mad(-_4091, _4089, 1.0f);
                    float _4298 = (_3358 * (_4085 / (_4088 * _4088))) * (0.5f / (mad(_2049, sqrt(mad(mad(-_787, _4085, _787), _787, _4085)), _787 * sqrt(mad(mad(-_2049, _4085, _2049), _2049, _4085))) + 9.9999997473787516355514526367188e-05f));
                    float _4317 = (_793 * (_827 * _EndfieldTextureT10.SampleLevel(sampler_LinearRepeat, float2(mad(_2049, 0.96875f, 0.015625f), _821), 0.0f).x)) / _794;
                    uint _4331 = (((16u * _1227) + 96u) + 8u) >> 2u;
                    float _4335 = asfloat(asuint(EndfieldCB4_f_0[_4331 >> 2u][_4331 & 3u]));
                    uint4 _4350 = asuint(EndfieldCB4_f_0[_1768 + 6u]);
                    _2454 = mad(clamp((min(_4298 * mad(_502, _4279, _4092), 2048.0f) + ((_838 * _4317) / _835)) * _4335, 0.0f, 1000.0f), _2049, _496 * (_805 ? _4274 : _2049)) * (_1470 * (_3104 * (_2501 * asfloat(_4350.x))));
                    _2452 = mad(clamp((min(_4298 * mad(_503, _4279, _4092), 2048.0f) + ((_839 * _4317) / _836)) * _4335, 0.0f, 1000.0f), _2049, _497 * (_805 ? _4273 : _2049)) * (_1470 * (_3104 * (_2501 * asfloat(_4350.y))));
                    _2450 = mad(clamp((min(_4298 * mad(_504, _4279, _4092), 2048.0f) + ((_840 * _4317) / _837)) * _4335, 0.0f, 1000.0f), _2049, _498 * (_805 ? _4272 : _2049)) * (_1470 * (_3104 * (_2501 * asfloat(_4350.z))));
                }
                else
                {
                    _2454 = 0.0f;
                    _2452 = 0.0f;
                    _2450 = 0.0f;
                }
                _1928 = _1022;
                _2449 = _2450;
                _2451 = _2452;
                _2453 = _2454;
            }
            else
            {
                float _2350 = 0.0f;
                if (!_1482)
                {
                    uint _2236 = (((16u * _1769) + 96u) + 4u) >> 2u;
                    float _2240 = asfloat(asuint(EndfieldCB4_f_0[_2236 >> 2u][_2236 & 3u]));
                    float _2241 = mad(_2240, 0.5f, 0.5f);
                    uint _2246 = (((16u * _1769) + 96u) + 0u) >> 2u;
                    float _2250 = asfloat(asuint(EndfieldCB4_f_0[_2246 >> 2u][_2246 & 3u]));
                    float _2251 = abs(_2250);
                    float _2252 = _2241 - _2251;
                    float _2254 = (_2251 - _2241) + _2240;
                    float _2259 = max((1.0f - abs(_2252)) - abs(_2254), 0.00048828125f);
                    float _2262 = (_2250 >= 0.0f) ? _2259 : (-_2259);
                    float3 _2263 = float3(_2252, _2254, _2262);
                    float _2265 = rsqrt(_173(_2263, _2263));
                    float _2266 = _2265 * _2252;
                    float _2267 = _2265 * _2254;
                    float _2268 = _2265 * _2262;
                    uint4 _2272 = asuint(EndfieldCB4_f_0[_1222 + 6u]);
                    float _2276 = asfloat(_2272.x);
                    float _2277 = asfloat(_2272.y);
                    float _2278 = asfloat(_2272.z);
                    float _2279 = _2276 - _379;
                    float _2280 = _2277 - _380;
                    float _2281 = _2278 - _381;
                    float3 _2282 = float3(_2279, _2280, _2281);
                    float _2283 = _173(_2282, _2282);
                    float _2284 = rsqrt(_2283);
                    float _2285 = _2284 * _2279;
                    float _2286 = _2284 * _2280;
                    float _2287 = _2284 * _2281;
                    uint _2293 = (((16u * _1227) + 96u) + 12u) >> 2u;
                    uint _2298 = uint(int(asfloat(asuint(EndfieldCB4_f_0[_2293 >> 2u][_2293 & 3u]))));
                    uint _2303 = (((16u * _1769) + 96u) + 8u) >> 2u;
                    float _2307 = asfloat(asuint(EndfieldCB4_f_0[_2303 >> 2u][_2303 & 3u]));
                    float _2308 = _2266 * _2307;
                    float _2309 = _2267 * _2307;
                    float _2310 = _2268 * _2307;
                    uint _2321 = uint(_1779) & 1u;
                    bool _2322 = _2321 == 0u;
                    bool _2325 = (!_2322) && (_2307 > 0.0f);
                    float3 _2326 = float3(mad(-_2308, 0.5f, _2279), mad(-_2309, 0.5f, _2280), mad(-_2310, 0.5f, _2281));
                    float3 _2328 = float3(mad(_2308, 0.5f, _2279), mad(_2309, 0.5f, _2280), mad(_2310, 0.5f, _2281));
                    float _2337 = _2325 ? (1.0f / mad(mad(sqrt(_173(_2326, _2326)), sqrt(_173(_2328, _2328)), _173(_2326, _2328)), 0.5f, 1.0f)) : 1.0f;
                    uint _2343 = (((16u * _1226) + 96u) + 12u) >> 2u;
                    float _2347 = asfloat(asuint(EndfieldCB4_f_0[_2343 >> 2u][_2343 & 3u]));
                    float _2504 = 0.0f;
                    if (_2347 < 0.0f)
                    {
                        uint _2413 = (((16u * _1222) + 96u) + 12u) >> 2u;
                        float _2417 = asfloat(asuint(EndfieldCB4_f_0[_2413 >> 2u][_2413 & 3u]));
                        float _2419 = _2283 * (_2417 * _2417);
                        float _2422 = max(mad(-_2419, _2419, 1.0f), 0.0f);
                        float _2424 = 1.0f / (_2283 + 1.0f);
                        _2504 = (_2325 ? ((_2337 - _2424) + _2424) : _2424) * (_2422 * _2422);
                    }
                    else
                    {
                        uint _2433 = (((16u * _1222) + 96u) + 12u) >> 2u;
                        float _2437 = asfloat(asuint(EndfieldCB4_f_0[_2433 >> 2u][_2433 & 3u]));
                        float3 _2441 = float3(_2279 * _2437, _2280 * _2437, _2281 * _2437);
                        _2504 = exp2(log2(1.0f - min(_173(_2441, _2441), 1.0f)) * _2347) * _2337;
                    }
                    uint _2516 = (((16u * _1769) + 96u) + 12u) >> 2u;
                    uint _2519 = asuint(EndfieldCB4_f_0[_2516 >> 2u][_2516 & 3u]);
                    float _2522 = clamp((_173(float3(_2285, _2286, _2287), float3(-_2266, -_2267, -_2268)) - _2307) * asfloat(_2519), 0.0f, 1.0f);
                    float _2526 = _2504 * ((_2321 != 0u) ? 1.0f : (_2522 * _2522));
                    float _3106 = 0.0f;
                    if ((!_2325) && (int(_2298) >= int(0u)))
                    {
                        float _4096 = 0.0f;
                        float _4097 = 0.0f;
                        if (_2322)
                        {
                            uint _3362 = _2298 << 2u;
                            uint _3363 = _3362 + 33u;
                            uint _3372 = (((16u * _3362) + 528u) + 12u) >> 2u;
                            uint _3378 = _3362 + 32u;
                            uint _3387 = (((16u * _3362) + 512u) + 12u) >> 2u;
                            uint _3393 = _3362 + 34u;
                            uint _3402 = (((16u * _3362) + 544u) + 12u) >> 2u;
                            uint _3408 = _3362 + 35u;
                            uint _3417 = (((16u * _3362) + 560u) + 12u) >> 2u;
                            float _3422 = mad(EndfieldCB8_f_0[_3402 >> 2u][_3402 & 3u], _381, mad(EndfieldCB8_f_0[_3387 >> 2u][_3387 & 3u], _379, _380 * EndfieldCB8_f_0[_3372 >> 2u][_3372 & 3u])) + EndfieldCB8_f_0[_3417 >> 2u][_3417 & 3u];
                            _4096 = mad(clamp((mad(EndfieldCB8_f_0[_3393].y, _381, mad(EndfieldCB8_f_0[_3378].y, _379, _380 * EndfieldCB8_f_0[_3363].y)) + EndfieldCB8_f_0[_3408].y) / _3422, 0.0f, 1.0f), EndfieldCB8_f_0[_2298].w, EndfieldCB8_f_0[_2298].y);
                            _4097 = mad(clamp((mad(EndfieldCB8_f_0[_3393].x, _381, mad(EndfieldCB8_f_0[_3378].x, _379, _380 * EndfieldCB8_f_0[_3363].x)) + EndfieldCB8_f_0[_3408].x) / _3422, 0.0f, 1.0f), EndfieldCB8_f_0[_2298].z, EndfieldCB8_f_0[_2298].x);
                        }
                        else
                        {
                            uint _3435 = _2298 << 2u;
                            float3 _3439 = float3(_379 - _2276, _380 - _2277, _381 - _2278);
                            float _3447 = _173(_3439, float3(EndfieldCB8_f_0[_3435 + 32u].xyz));
                            float _3455 = _173(_3439, float3(EndfieldCB8_f_0[_3435 + 33u].xyz));
                            float _3463 = _173(_3439, float3(EndfieldCB8_f_0[_3435 + 34u].xyz));
                            float _3464 = abs(_3447);
                            float _3465 = abs(_3455);
                            uint _3467 = uint(_3464 < _3465);
                            uint _3479 = (_160(float2(_3464, _3465), float2(_154[_3467].x, _154[_3467].y)) < abs(_3463)) ? 2u : _3467;
                            float3 _3480 = float3(_3447, _3455, _3463);
                            uint _3481 = min(_3479, 10u);
                            uint _3495 = spvBitfieldInsert((_173(_3480, float3(_154[_3481].x, _154[_3481].y, _154[_3481].z)) < 0.0f) ? 4294967295u : 0u, _3479, 1u, 31u);
                            uint _3497 = min((_3495 >> 1u), 10u);
                            uint _3513 = (_2298 * 4u) + 3u;
                            float _3517 = 0.5f - (0.000244140625f / EndfieldCB8_f_0[_3513 >> 2u][_3513 & 3u]);
                            uint _3520 = (_3495 < 2u) ? 2u : 0u;
                            uint _3531 = min((_3495 + 4u), 10u);
                            float _3536 = abs(_173(_3480, float3(_154[_3497].x, _154[_3497].y, _154[_3497].z)));
                            uint _3548 = min((asuint(_154[_3531].y) - 1u), 10u);
                            _4096 = mad(clamp(mad(-((_160(float2(_3455, _3463), float2(_154[_3548].x, _154[_3548].y)) * _154[_3531].w) / _3536), _3517, 0.5f), 0.0f, 1.0f), EndfieldCB8_f_0[_2298].w, EndfieldCB8_f_0[_2298].y);
                            _4097 = mad(clamp((mad((_160(float2(_3447, _3463), float2(_154[_3520].x, _154[_3520].z)) * _154[_3531].z) / _3536, _3517, _186(_3495)) + 0.5f) * 0.16666667163372039794921875f, 0.0f, 1.0f), EndfieldCB8_f_0[_2298].z, EndfieldCB8_f_0[_2298].x);
                        }
                        _3106 = _2526 * _EndfieldTextureT14.SampleLevel(sampler_LinearRepeat, float2(_4097, _4096), 0.0f).x;
                    }
                    else
                    {
                        _3106 = _2526;
                    }
                    float _2351 = 0.0f;
                    if (_3106 > 0.0f)
                    {
                        bool _3575 = _2322 || ((_1239 & 2u) != 0u);
                        bool _4366 = false;
                        uint _4367 = 0u;
                        if (_3575)
                        {
                            uint _4111 = (((16u * _1224) + 96u) + 0u) >> 2u;
                            _4366 = _2322;
                            _4367 = uint(int(asfloat(asuint(EndfieldCB4_f_0[_4111 >> 2u][_4111 & 3u]))));
                        }
                        else
                        {
                            float _4117 = _379 - _2276;
                            float _4118 = _380 - _2277;
                            float _4119 = _381 - _2278;
                            float _4120 = abs(_4118);
                            float _4121 = abs(_4119);
                            float _4122 = abs(_4117);
                            bool _4125 = _4121 < _4120;
                            bool _4126 = (_4120 < _4122) && (_4121 < _4122);
                            uint _4133 = (_4117 > 0.0f) ? (_2519 >> 24u) : spvBitfieldUExtract(_2519, 16u, 8u);
                            uint _4135 = (_4118 > 0.0f) ? spvBitfieldUExtract(_2519, 8u, 8u) : (_2519 & 255u);
                            uint _4139 = (((16u * _1224) + 96u) + 0u) >> 2u;
                            uint _4142 = asuint(EndfieldCB4_f_0[_4139 >> 2u][_4139 & 3u]);
                            uint _4145 = (_4119 > 0.0f) ? spvBitfieldUExtract(_4142, 8u, 8u) : (_4142 & 255u);
                            bool _4158 = ((((!_4125) && (int(_4145) < int(80u))) || ((int(_4135) < int(80u)) && _4125)) && (!_4126)) || (_4126 && (int(_4133) < int(80u)));
                            _4366 = _4158;
                            _4367 = _4158 ? (_4126 ? _4133 : (_4125 ? _4135 : _4145)) : 4294967295u;
                        }
                        uint _4374 = (((16u * _4367) + 2560u) + 4u) >> 2u;
                        uint _4377 = asuint(EndfieldCB6_f_0[_4374 >> 2u][_4374 & 3u]);
                        bool _4378 = _4377 != 0u;
                        float _4743 = 0.0f;
                        if (_4378)
                        {
                            float _4744 = 0.0f;
                            if (_4378)
                            {
                                uint _4747 = min((_4377 - 1u), 10u);
                                _4744 = _194(_768, float4(_154[_4747].x, _154[_4747].y, _154[_4747].z, _154[_4747].w));
                            }
                            else
                            {
                                _4744 = 1.0f;
                            }
                            _4743 = _4744;
                        }
                        else
                        {
                            _4743 = _4366 ? asfloat(0xffffffffu /* nan */) : 0.0f;
                        }
                        float _5039 = 0.0f;
                        if (_4377 <= 0u)
                        {
                            uint _4762 = _4367 << 2u;
                            uint _4768 = (((16u * _4367) + 4608u) + 0u) >> 2u;
                            uint _5269 = _4768 >> 2u;
                            uint _5270 = _4768 & 3u;
                            uint _4778 = (((16u * _4367) + 4608u) + 4u) >> 2u;
                            float _4781 = EndfieldCB5_f_0[_4778 >> 2u][_4778 & 3u] * 5.0f;
                            float _4782 = mad(_279, _4781, mad(_2285, EndfieldCB5_f_0[_5269][_5270], _379));
                            float _4783 = mad(_280, _4781, mad(_2286, EndfieldCB5_f_0[_5269][_5270], _380));
                            float _4784 = mad(_281, _4781, mad(_2287, EndfieldCB5_f_0[_5269][_5270], _381));
                            uint _4785 = _4762 + 65u;
                            uint _4796 = _4762 + 64u;
                            uint _4807 = _4762 + 66u;
                            uint _4818 = _4762 + 67u;
                            float _4828 = mad(EndfieldCB5_f_0[_4807].w, _4784, mad(EndfieldCB5_f_0[_4796].w, _4782, _4783 * EndfieldCB5_f_0[_4785].w)) + EndfieldCB5_f_0[_4818].w;
                            float _4829 = (mad(EndfieldCB5_f_0[_4807].x, _4784, mad(EndfieldCB5_f_0[_4796].x, _4782, _4783 * EndfieldCB5_f_0[_4785].x)) + EndfieldCB5_f_0[_4818].x) / _4828;
                            float _4830 = (mad(EndfieldCB5_f_0[_4807].y, _4784, mad(EndfieldCB5_f_0[_4796].y, _4782, _4783 * EndfieldCB5_f_0[_4785].y)) + EndfieldCB5_f_0[_4818].y) / _4828;
                            float _4831 = (mad(EndfieldCB5_f_0[_4807].z, _4784, mad(EndfieldCB5_f_0[_4796].z, _4782, _4783 * EndfieldCB5_f_0[_4785].z)) + EndfieldCB5_f_0[_4818].z) / _4828;
                            uint _4838 = _4367 + 344u;
                            float _4847 = mad(_4829, EndfieldCB5_f_0[_4838].z - EndfieldCB5_f_0[_4838].x, EndfieldCB5_f_0[_4838].x);
                            float _4848 = mad(_4830, EndfieldCB5_f_0[_4838].w - EndfieldCB5_f_0[_4838].y, EndfieldCB5_f_0[_4838].y);
                            float _4855 = floor(mad(_4847, EndfieldCB5_f_0[400u].z, 0.5f));
                            float _4856 = floor(mad(_4848, EndfieldCB5_f_0[400u].w, 0.5f));
                            float _4859 = mad(_4847, EndfieldCB5_f_0[400u].z, -_4855);
                            float _4860 = mad(_4848, EndfieldCB5_f_0[400u].w, -_4856);
                            float _4861 = _4859 + 0.5f;
                            float _4862 = _4859 + 1.0f;
                            float _4863 = _4860 + 0.5f;
                            float _4864 = _4860 + 1.0f;
                            float _4865 = _4861 * _4861;
                            float _4866 = _4863 * _4863;
                            float _4869 = 1.0f - _4859;
                            float _4870 = 1.0f - _4860;
                            float _4871 = min(_4859, 0.0f);
                            float _4872 = min(_4860, 0.0f);
                            float _4873 = max(_4859, 0.0f);
                            float _4874 = max(_4860, 0.0f);
                            float _4875 = _4869 * 0.1599999964237213134765625f;
                            float _4876 = _4870 * 0.1599999964237213134765625f;
                            float _4883 = (mad(-_4873, _4873, _4862) + 1.0f) * 0.1599999964237213134765625f;
                            float _4884 = (mad(-_4874, _4874, _4864) + 1.0f) * 0.1599999964237213134765625f;
                            float _4885 = _4865 * 0.07999999821186065673828125f;
                            float _4886 = _4866 * 0.07999999821186065673828125f;
                            float _4896 = _4883 + ((mad(-_4871, _4871, _4869) + 1.0f) * 0.1599999964237213134765625f);
                            float _4897 = mad(_4862, 0.1599999964237213134765625f, _4885);
                            float _4898 = mad(mad(_4865, 0.5f, -_4859), 0.1599999964237213134765625f, _4875);
                            float _4899 = mad(mad(_4866, 0.5f, -_4860), 0.1599999964237213134765625f, _4876);
                            float _4900 = mad(mad(-_4872, _4872, _4870) + 1.0f, 0.1599999964237213134765625f, _4884);
                            float _4901 = mad(_4864, 0.1599999964237213134765625f, _4886);
                            float _4926 = mad(_4855, EndfieldCB5_f_0[400u].x, ((_4875 / _4898) - 2.5f) * EndfieldCB5_f_0[400u].x);
                            float _4927 = mad(_4856, EndfieldCB5_f_0[400u].y, ((_4876 / _4899) - 2.5f) * EndfieldCB5_f_0[400u].y);
                            float _4928 = mad(_4855, EndfieldCB5_f_0[400u].x, ((_4883 / _4896) - 0.5f) * EndfieldCB5_f_0[400u].x);
                            float _4929 = mad(_4855, EndfieldCB5_f_0[400u].x, ((_4885 / _4897) + 1.5f) * EndfieldCB5_f_0[400u].x);
                            float _4930 = mad(_4856, EndfieldCB5_f_0[400u].y, ((_4884 / _4900) - 0.5f) * EndfieldCB5_f_0[400u].y);
                            float _4931 = mad(_4856, EndfieldCB5_f_0[400u].y, ((_4886 / _4901) + 1.5f) * EndfieldCB5_f_0[400u].y);
                            uint _5015 = (((16u * _4367) + 4608u) + 8u) >> 2u;
                            float _5023 = clamp(min(min(min(1.0f - _4830, _4830), min(1.0f - _4829, _4829)), (EndfieldCB5_f_0[_5015 >> 2u][_5015 & 3u] - _4828) * 0.25f) * 20.0f, 0.0f, 1.0f);
                            uint _5031 = (((16u * _4367) + 4608u) + 12u) >> 2u;
                            uint _5275 = _5031 >> 2u;
                            uint _5276 = _5031 & 3u;
                            float _5036 = mad(_4897 * _4901, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4929, _4931), _4831).xxxx.x, mad(_4896 * _4901, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4928, _4931), _4831).xxxx.x, mad(_4898 * _4901, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4926, _4931), _4831).xxxx.x, mad(_4897 * _4900, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4929, _4930), _4831).xxxx.x, mad(_4896 * _4900, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4928, _4930), _4831).xxxx.x, mad(_4898 * _4900, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4926, _4930), _4831).xxxx.x, mad(_4897 * _4899, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4929, _4927), _4831).xxxx.x, mad(_4898 * _4899, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4926, _4927), _4831).xxxx.x, _EndfieldTextureT6.SampleCmpLevelZero(sampler_PointClamp, float2(_4928, _4927), _4831).xxxx.x * (_4896 * _4899))))))))) - 1.0f;
                            _5039 = (((((_4829 <= 0.0f) || (_4829 >= 1.0f)) || ((_4830 <= 0.0f) || (_4830 >= 1.0f))) || ((_4831 <= 0.0f) || (_4831 >= 1.0f))) || ((asuint(_4831) & 2147483647u) > 2139095040u)) ? 1.0f : mad(_3575 ? min((_5023 * _5023) * mad(_5023, -2.0f, 3.0f), EndfieldCB5_f_0[_5275][_5276]) : EndfieldCB5_f_0[_5275][_5276], _5036, 1.0f);
                        }
                        else
                        {
                            _5039 = _4743;
                        }
                        _2351 = (int(_4367) >= int(0u)) ? _5039 : 1.0f;
                    }
                    else
                    {
                        _2351 = 1.0f;
                    }
                    _2350 = _2351;
                }
                else
                {
                    _2350 = 1.0f;
                }
                _1928 = _2350 * _1022;
                _2449 = 0.0f;
                _2451 = 0.0f;
                _2453 = 0.0f;
            }
            _1057 = _1928;
            _1056 = _1055 + _2453;
            _1054 = _1053 + _2451;
            _1052 = _1051 + _2449;
            _1051 = _1052;
            _1053 = _1054;
            _1055 = _1056;
            _1022 = _1057;
            _1058 = _1059;
            continue;
        }
        _1020 = _1019 + _1055;
        _1018 = _1017 + _1053;
        _1016 = _1015 + _1051;
        _1024 = _1023 + 1u;
        _1015 = _1016;
        _1017 = _1018;
        _1019 = _1020;
        _1021 = _1022;
        _1023 = _1024;
        continue;
    }
    uint4 _1044 = asuint(EndfieldCB1_f_0[30u]);
    float _1114 = 0.0f;
    float _1115 = 0.0f;
    float _1116 = 0.0f;
    float _1117 = 0.0f;
    float _1118 = 0.0f;
    if (asfloat(_1044.x) != 0.0f)
    {
        float _1069 = min(_227, _EndfieldTextureT4.SampleBias(sampler_LinearClamp, float2(TEXCOORD.x, TEXCOORD.y), _760).x);
        float _1079 = (_1069 + exp2(log2(abs(_1069 + _508)) * exp2(mad(_482, -16.0f, -1.0f)))) - 1.0f;
        _1114 = _1079;
        _1115 = clamp(_1079, 0.0f, 1.0f);
        _1116 = max(_1069, _1069 * (mad(_496, 2.755199909210205078125f, _1069 * (mad(_496, -4.79510021209716796875f, _1069 * mad(_496, 2.040400028228759765625f, -0.3323999941349029541015625f)) + 0.6417000293731689453125f)) + 0.69029998779296875f));
        _1117 = max(_1069, _1069 * (mad(_497, 2.755199909210205078125f, _1069 * (mad(_497, -4.79510021209716796875f, _1069 * mad(_497, 2.040400028228759765625f, -0.3323999941349029541015625f)) + 0.6417000293731689453125f)) + 0.69029998779296875f));
        _1118 = max(_1069, _1069 * (mad(_498, 2.755199909210205078125f, _1069 * (mad(_498, -4.79510021209716796875f, _1069 * mad(_498, 2.040400028228759765625f, -0.3323999941349029541015625f)) + 0.6417000293731689453125f)) + 0.69029998779296875f));
    }
    else
    {
        _1114 = _769 ? asfloat(0xffffffffu /* nan */) : 0.0f;
        _1115 = _227;
        _1116 = _227;
        _1117 = _227;
        _1118 = _227;
    }
    float _1131 = 0.0f;
    float _1132 = 0.0f;
    float _1133 = 0.0f;
    if (_805)
    {
        float4 _1124 = _EndfieldTextureT12.SampleLevel(sampler_LinearRepeat, float3(_816, 0.5f, _817), 0.0f);
        _1131 = _1124.z;
        _1132 = _1124.y;
        _1133 = _1124.x;
    }
    else
    {
        _1131 = asfloat(_254);
        _1132 = _227;
        _1133 = _1114;
    }
    float _1134 = _805 ? _1133 : 1.0f;
    float _1135 = _805 ? _1132 : 1.0f;
    float _1136 = _805 ? _1131 : 1.0f;
    float _1146 = trunc(asfloat(asuint(EndfieldCB1_f_0[134u].x)));
    float _1160 = mad(frac(frac(_160(float2(mad(_1146, 2.0829999446868896484375f, _282), mad(_1146, 4.867000102996826171875f, _283)), float2(0.067110560834407806396484375f, 0.005837149918079376220703125f))) * 52.98291778564453125f), 2.0f, -1.0f);
    float _1161 = mad(_1160, 0.20000000298023223876953125f, mad(_279, 0.25f, _379));
    float _1163 = mad(_1160, 0.20000000298023223876953125f, mad(_280, 0.25f, _380));
    float _1164 = mad(_1160, 0.20000000298023223876953125f, mad(_281, 0.25f, _381));
    uint4 _1167 = asuint(EndfieldCB0_f_0[6u]);
    float _1171 = asfloat(_1167.x);
    float _1172 = asfloat(_1167.y);
    float _1173 = asfloat(_1167.z);
    float _1179 = -asfloat(asuint(EndfieldCB1_f_0[134u].w));
    uint4 _1183 = asuint(EndfieldCB1_f_0[132u]);
    float _1187 = asfloat(_1183.x);
    float _1188 = asfloat(_1183.y);
    float _1189 = asfloat(_1183.z);
    float _1208 = max(clamp((max(abs(_1164 - mad(_1173, _1179, _1189)), abs(_1161 - mad(_1171, _1179, _1187))) - 464.0f) * 0.03125f, 0.0f, 1.0f), clamp((abs(_1163 - mad(_1172, _1179, _1188)) - 208.0f) * 0.03125f, 0.0f, 1.0f));
    float _1268 = 0.0f;
    float _1270 = 0.0f;
    float _1272 = 0.0f;
    float _1274 = 0.0f;
    float _1276 = 0.0f;
    float _1278 = 0.0f;
    float _1280 = 0.0f;
    float _1282 = 0.0f;
    float _1284 = 0.0f;
    float _1286 = 0.0f;
    float _1288 = 0.0f;
    float _1290 = 0.0f;
    float _1292 = 0.0f;
    float _1294 = 0.0f;
    if ((asfloat(asuint(EndfieldCB1_f_0[132u].w)) != 0.0f) && (_1208 < 1.0f))
    {
        float _1247 = -asfloat(asuint(EndfieldCB1_f_0[134u].y));
        float _1266 = max(clamp((max(abs(_1164 - mad(_1173, _1247, _1189)), abs(_1161 - mad(_1171, _1247, _1187))) - 29.0f) * 0.5f, 0.0f, 1.0f), clamp((abs(_1163 - mad(_1172, _1247, _1188)) - 13.0f) * 0.5f, 0.0f, 1.0f));
        float _1596 = 0.0f;
        float _1597 = 0.0f;
        float _1598 = 0.0f;
        float _1599 = 0.0f;
        float _1600 = 0.0f;
        float _1601 = 0.0f;
        float _1602 = 0.0f;
        float _1603 = 0.0f;
        float _1604 = 0.0f;
        float _1605 = 0.0f;
        float _1606 = 0.0f;
        float _1607 = 0.0f;
        float _1608 = 0.0f;
        if (_1266 < 1.0f)
        {
            float _1485 = mad(_1161, 2.0f, 0.5f);
            float _1486 = mad(_1163, 2.0f, 0.5f);
            float _1487 = mad(_1164, 2.0f, 0.5f);
            uint4 _1491 = asuint(EndfieldCB1_f_0[133u]);
            float _1495 = asfloat(_1491.x);
            float _1496 = asfloat(_1491.y);
            float _1497 = asfloat(_1491.z);
            float _1507 = mad(_1485, _1495, -floor(_1485 * _1495));
            float _1508 = mad(_1486, _1496, -floor(_1486 * _1496));
            float _1509 = mad(_1487, _1497, -floor(_1487 * _1497));
            float4 _1515 = _EndfieldTextureT18.SampleLevel(sampler_LinearMirror, float3(_1507, _1508, _1509), 0.0f);
            float _1517 = _1515.x;
            float _1518 = _1515.y;
            float _1519 = _1515.z;
            float _1522 = 1.0f - _1266;
            float _1527 = asfloat(asuint(EndfieldCB1_f_0[133u].y));
            float _1533 = min(mad(-_1527, 0.5f, 1.0f), max(_1527 * 0.5f, _1508)) * 0.3333333432674407958984375f;
            float4 _1538 = _EndfieldTextureT19.SampleLevel(sampler_LinearRepeat, float3(_1507, _1533, _1509), 0.0f);
            float4 _1549 = _EndfieldTextureT19.SampleLevel(sampler_LinearRepeat, float3(_1507, _1533 + 0.666666686534881591796875f, _1509), 0.0f);
            float4 _1569 = _EndfieldTextureT19.SampleLevel(sampler_LinearRepeat, float3(_1507, _1533 + 0.3333333432674407958984375f, _1509), 0.0f);
            _1596 = _1522 * _1517;
            _1597 = _1522 * (_1517 * mad(_1538.z, 4.0f, -2.0f));
            _1598 = _1522 * (_1517 * mad(_1538.y, 4.0f, -2.0f));
            _1599 = _1522 * (_1517 * mad(_1538.x, 4.0f, -2.0f));
            _1600 = _1522 * _1518;
            _1601 = _1522 * (_1518 * mad(_1569.z, 4.0f, -2.0f));
            _1602 = _1522 * (_1518 * mad(_1569.y, 4.0f, -2.0f));
            _1603 = _1522 * (_1518 * mad(_1569.x, 4.0f, -2.0f));
            _1604 = _1522 * _1519;
            _1605 = _1522 * (_1519 * mad(_1549.z, 4.0f, -2.0f));
            _1606 = _1522 * (_1519 * mad(_1549.y, 4.0f, -2.0f));
            _1607 = _1522 * (_1519 * mad(_1549.x, 4.0f, -2.0f));
            _1608 = mad(_1538.w, _1522, _1208);
        }
        else
        {
            _1596 = 0.0f;
            _1597 = 0.0f;
            _1598 = 0.0f;
            _1599 = 0.0f;
            _1600 = 0.0f;
            _1601 = 0.0f;
            _1602 = 0.0f;
            _1603 = 0.0f;
            _1604 = 0.0f;
            _1605 = 0.0f;
            _1606 = 0.0f;
            _1607 = 0.0f;
            _1608 = _1208;
        }
        float _1614 = -asfloat(asuint(EndfieldCB1_f_0[134u].z));
        float _1634 = max(clamp((max(abs(_1164 - mad(_1173, _1614, _1189)), abs(_1161 - mad(_1171, _1614, _1187))) - 116.0f) * 0.125f, 0.0f, 1.0f), clamp((abs(_1163 - mad(_1172, _1614, _1188)) - 52.0f) * 0.125f, 0.0f, 1.0f));
        float _1889 = 0.0f;
        float _1890 = 0.0f;
        float _1891 = 0.0f;
        float _1892 = 0.0f;
        float _1893 = 0.0f;
        float _1894 = 0.0f;
        float _1895 = 0.0f;
        float _1896 = 0.0f;
        float _1897 = 0.0f;
        float _1898 = 0.0f;
        float _1899 = 0.0f;
        float _1900 = 0.0f;
        float _1901 = 0.0f;
        if (_1634 < 1.0f)
        {
            float _1783 = mad(_1161, 0.5f, 0.5f);
            float _1784 = mad(_1163, 0.5f, 0.5f);
            float _1785 = mad(_1164, 0.5f, 0.5f);
            uint4 _1788 = asuint(EndfieldCB1_f_0[133u]);
            float _1792 = asfloat(_1788.x);
            float _1793 = asfloat(_1788.y);
            float _1794 = asfloat(_1788.z);
            float _1804 = mad(_1783, _1792, -floor(_1783 * _1792));
            float _1805 = mad(_1784, _1793, -floor(_1784 * _1793));
            float _1806 = mad(_1785, _1794, -floor(_1785 * _1794));
            float4 _1811 = _EndfieldTextureT20.SampleLevel(sampler_LinearMirror, float3(_1804, _1805, _1806), 0.0f);
            float _1813 = _1811.x;
            float _1814 = _1811.y;
            float _1815 = _1811.z;
            float _1819 = _1266 * (1.0f - _1634);
            float _1823 = asfloat(asuint(EndfieldCB1_f_0[133u].y));
            float _1829 = min(mad(-_1823, 0.5f, 1.0f), max(_1823 * 0.5f, _1805)) * 0.3333333432674407958984375f;
            float4 _1833 = _EndfieldTextureT21.SampleLevel(sampler_LinearRepeat, float3(_1804, _1829, _1806), 0.0f);
            float4 _1843 = _EndfieldTextureT21.SampleLevel(sampler_LinearRepeat, float3(_1804, _1829 + 0.666666686534881591796875f, _1806), 0.0f);
            float4 _1862 = _EndfieldTextureT21.SampleLevel(sampler_LinearRepeat, float3(_1804, _1829 + 0.3333333432674407958984375f, _1806), 0.0f);
            _1889 = mad(_1833.w, _1819, _1608);
            _1890 = mad(_1813, _1819, _1596);
            _1891 = mad(_1813 * mad(_1833.z, 4.0f, -2.0f), _1819, _1597);
            _1892 = mad(_1813 * mad(_1833.y, 4.0f, -2.0f), _1819, _1598);
            _1893 = mad(_1813 * mad(_1833.x, 4.0f, -2.0f), _1819, _1599);
            _1894 = mad(_1814, _1819, _1600);
            _1895 = mad(_1814 * mad(_1862.z, 4.0f, -2.0f), _1819, _1601);
            _1896 = mad(_1814 * mad(_1862.y, 4.0f, -2.0f), _1819, _1602);
            _1897 = mad(_1814 * mad(_1862.x, 4.0f, -2.0f), _1819, _1603);
            _1898 = mad(_1815, _1819, _1604);
            _1899 = mad(_1815 * mad(_1843.z, 4.0f, -2.0f), _1819, _1605);
            _1900 = mad(_1815 * mad(_1843.y, 4.0f, -2.0f), _1819, _1606);
            _1901 = mad(_1815 * mad(_1843.x, 4.0f, -2.0f), _1819, _1607);
        }
        else
        {
            _1889 = _1608;
            _1890 = _1596;
            _1891 = _1597;
            _1892 = _1598;
            _1893 = _1599;
            _1894 = _1600;
            _1895 = _1601;
            _1896 = _1602;
            _1897 = _1603;
            _1898 = _1604;
            _1899 = _1605;
            _1900 = _1606;
            _1901 = _1607;
        }
        float _1269 = 0.0f;
        float _1271 = 0.0f;
        float _1273 = 0.0f;
        float _1275 = 0.0f;
        float _1277 = 0.0f;
        float _1279 = 0.0f;
        float _1281 = 0.0f;
        float _1283 = 0.0f;
        float _1285 = 0.0f;
        float _1287 = 0.0f;
        float _1289 = 0.0f;
        float _1291 = 0.0f;
        float _2178 = 0.0f;
        if (_1634 > 0.0f)
        {
            float _2064 = mad(_1161, 0.125f, 0.5f);
            float _2065 = mad(_1163, 0.125f, 0.5f);
            float _2066 = mad(_1164, 0.125f, 0.5f);
            uint4 _2069 = asuint(EndfieldCB1_f_0[133u]);
            float _2073 = asfloat(_2069.x);
            float _2074 = asfloat(_2069.y);
            float _2075 = asfloat(_2069.z);
            float _2080 = _2074 * 0.5f;
            float _2095 = mad(-_2074, 0.5f, 1.0f);
            float _2100 = min(mad(-_2073, 0.5f, 1.0f), max(_2073 * 0.5f, mad(_2064, _2073, -floor(_2064 * _2073))));
            float _2101 = min(_2095, max(_2080, mad(_2065, _2074, -floor(_2065 * _2074))));
            float _2102 = min(mad(-_2075, 0.5f, 1.0f), max(_2075 * 0.5f, mad(_2066, _2075, -floor(_2066 * _2075))));
            float4 _2107 = _EndfieldTextureT22.SampleLevel(sampler_LinearMirror, float3(_2100, _2101, _2102), 0.0f);
            float _2109 = _2107.x;
            float _2110 = _2107.y;
            float _2111 = _2107.z;
            float _2115 = (1.0f - _1208) * _1634;
            float _2118 = min(_2095, max(_2080, _2101)) * 0.3333333432674407958984375f;
            float4 _2122 = _EndfieldTextureT23.SampleLevel(sampler_LinearRepeat, float3(_2100, _2118, _2102), 0.0f);
            float4 _2131 = _EndfieldTextureT23.SampleLevel(sampler_LinearRepeat, float3(_2100, _2118 + 0.666666686534881591796875f, _2102), 0.0f);
            float4 _2150 = _EndfieldTextureT23.SampleLevel(sampler_LinearRepeat, float3(_2100, _2118 + 0.3333333432674407958984375f, _2102), 0.0f);
            _1291 = mad(_2109 * mad(_2122.x, 4.0f, -2.0f), _2115, _1893);
            _1289 = mad(_2109 * mad(_2122.y, 4.0f, -2.0f), _2115, _1892);
            _1287 = mad(_2109 * mad(_2122.z, 4.0f, -2.0f), _2115, _1891);
            _1285 = mad(_2109, _2115, _1890);
            _1283 = mad(_2110 * mad(_2150.x, 4.0f, -2.0f), _2115, _1897);
            _1281 = mad(_2110 * mad(_2150.y, 4.0f, -2.0f), _2115, _1896);
            _1279 = mad(_2110 * mad(_2150.z, 4.0f, -2.0f), _2115, _1895);
            _1277 = mad(_2110, _2115, _1894);
            _1275 = mad(_2111 * mad(_2131.x, 4.0f, -2.0f), _2115, _1901);
            _1273 = mad(_2111 * mad(_2131.y, 4.0f, -2.0f), _2115, _1900);
            _1271 = mad(_2111 * mad(_2131.z, 4.0f, -2.0f), _2115, _1899);
            _1269 = mad(_2111, _2115, _1898);
            _2178 = mad(_2122.w, _2115, _1889);
        }
        else
        {
            _1291 = _1893;
            _1289 = _1892;
            _1287 = _1891;
            _1285 = _1890;
            _1283 = _1897;
            _1281 = _1896;
            _1279 = _1895;
            _1277 = _1894;
            _1275 = _1901;
            _1273 = _1900;
            _1271 = _1899;
            _1269 = _1898;
            _2178 = _1889;
        }
        float _2180 = clamp(mad(_2178, 2.0f, -1.0f), 0.0f, 1.0f);
        _1268 = _1269;
        _1270 = _1271;
        _1272 = _1273;
        _1274 = _1275;
        _1276 = _1277;
        _1278 = _1279;
        _1280 = _1281;
        _1282 = _1283;
        _1284 = _1285;
        _1286 = _1287;
        _1288 = _1289;
        _1290 = _1291;
        _1292 = (_1208 + _2180) * 0.5f;
        _1294 = _2180 - _1208;
    }
    else
    {
        _1268 = 0.0f;
        _1270 = 0.0f;
        _1272 = 0.0f;
        _1274 = 0.0f;
        _1276 = 0.0f;
        _1278 = 0.0f;
        _1280 = 0.0f;
        _1282 = 0.0f;
        _1284 = 0.0f;
        _1286 = 0.0f;
        _1288 = 0.0f;
        _1290 = 0.0f;
        _1292 = 1.0f;
        _1294 = 0.0f;
    }
    uint4 _1299 = asuint(EndfieldCB1_f_0[135u]);
    float _1325 = mad(_1292, asfloat(_1299.x), _1290);
    float _1326 = _1288 + mad(_1294 * asfloat(_1299.w), 0.5f, _1292 * asfloat(_1299.y));
    float _1327 = mad(_1292, asfloat(_1299.z), _1286);
    float _1328 = _1284 + mad(_1294 * asfloat(asuint(EndfieldCB1_f_0[135u].y)), 0.375f, _1292 * asfloat(asuint(EndfieldCB1_f_0[135u].w)));
    uint4 _1332 = asuint(EndfieldCB1_f_0[136u]);
    float _1357 = mad(_1292, asfloat(_1332.x), _1282);
    float _1358 = _1280 + mad(_1294 * asfloat(_1332.w), 0.5f, _1292 * asfloat(_1332.y));
    float _1359 = mad(_1292, asfloat(_1332.z), _1278);
    float _1360 = _1276 + mad(_1294 * asfloat(asuint(EndfieldCB1_f_0[136u].y)), 0.375f, _1292 * asfloat(asuint(EndfieldCB1_f_0[136u].w)));
    uint4 _1364 = asuint(EndfieldCB1_f_0[137u]);
    float _1389 = mad(_1292, asfloat(_1364.x), _1274);
    float _1390 = mad(_1294 * asfloat(_1364.w), 0.5f, _1292 * asfloat(_1364.y)) + _1272;
    float _1391 = mad(_1292, asfloat(_1364.z), _1270);
    float _1392 = mad(_1294 * asfloat(asuint(EndfieldCB1_f_0[137u].y)), 0.375f, _1292 * asfloat(asuint(EndfieldCB1_f_0[137u].w))) + _1268;
    float _1656 = 0.0f;
    float _1658 = 0.0f;
    float _1660 = 0.0f;
    float _1662 = 0.0f;
    float _1664 = 0.0f;
    float _1666 = 0.0f;
    float _1668 = 0.0f;
    float _1670 = 0.0f;
    float _1672 = 0.0f;
    float _1674 = 0.0f;
    float _1676 = 0.0f;
    float _1678 = 0.0f;
    if ((_298 >= 0.0f) && (_299 >= 0.0f))
    {
        float4 _1638 = _EndfieldTextureT17.SampleLevel(sampler_LinearRepeat, float2(_298, _299), 0.0f);
        float _1640 = _1638.x;
        float _1641 = _1638.y;
        float _1642 = _1638.z;
        float _1643 = _1638.w;
        float _1657 = 0.0f;
        float _1659 = 0.0f;
        float _1661 = 0.0f;
        float _1663 = 0.0f;
        float _1665 = 0.0f;
        float _1667 = 0.0f;
        float _1669 = 0.0f;
        float _1671 = 0.0f;
        float _1673 = 0.0f;
        float _1675 = 0.0f;
        float _1677 = 0.0f;
        float _1679 = 0.0f;
        if (((abs(_1641) > 9.9999997473787516355514526367188e-05f) || (abs(_1643) > 9.9999997473787516355514526367188e-05f)) || ((abs(_1640) > 9.9999997473787516355514526367188e-05f) || (abs(_1642) > 9.9999997473787516355514526367188e-05f)))
        {
            float3 _1903 = float3(_1641, _1642, _1643);
            float _1905 = sqrt(_173(_1903, _1903));
            float _2182 = 0.0f;
            uint _2184 = 0u;
            _2182 = 1.0f;
            _2184 = 0u;
            float _2183 = 0.0f;
            uint _2185 = 0u;
            float _2187 = 0.0f;
            float _2186 = _1905;
            for (;;)
            {
                if (_2186 <= 4.599999904632568359375f)
                {
                    break;
                }
                _2185 = _2184 + 1u;
                _2183 = _2182 * 0.5f;
                _2187 = _2186 * 0.5f;
                _2182 = _2183;
                _2184 = _2185;
                _2186 = _2187;
                continue;
            }
            float _2530 = _2182 * _1641;
            float _2531 = _2182 * _1642;
            float _2532 = _2182 * _1643;
            float3 _2533 = float3(_2530, _2531, _2532);
            float4 _2552 = _EndfieldTextureT16.SampleLevel(sampler_LinearRepeat, float2(mad(mad(sqrt(_173(_2533, _2533)), asfloat(asuint(EndfieldCB9_f_0[3u].x)), asfloat(asuint(EndfieldCB9_f_0[3u].y))), 255.0f, 0.5f) * 0.00390625f, 0.5f), 0.0f);
            uint4 _2561 = asuint(EndfieldCB9_f_0[2u]);
            float _2571 = mad(_2552.y, asfloat(_2561.y), asfloat(_2561.w));
            float _2579 = exp2((_2182 * _1640) * 0.4069767296314239501953125f);
            float _3109 = 0.0f;
            float _3111 = 0.0f;
            float _3113 = 0.0f;
            float _3115 = 0.0f;
            _3109 = _2579 * (_2571 * _2532);
            _3111 = _2579 * (_2571 * _2531);
            _3113 = _2579 * (_2571 * _2530);
            _3115 = _2579 * (mad(_2552.x, asfloat(_2561.x), asfloat(_2561.z)) * 3.5449078083038330078125f);
            float _3110 = 0.0f;
            float _3112 = 0.0f;
            float _3114 = 0.0f;
            float _3116 = 0.0f;
            uint _3118 = 0u;
            uint _3117 = 0u;
            for (;;)
            {
                if (_2184 <= _3117)
                {
                    break;
                }
                float _4160 = _3115 * 0.282094776630401611328125f;
                float _4162 = _3113 * 0.282094776630401611328125f;
                float _4163 = _3111 * 0.282094776630401611328125f;
                float _4164 = _3109 * 0.282094776630401611328125f;
                _3116 = _194(float4(_4160, _4162, _4163, _4164), float4(_3115, _3113, _3111, _3109));
                _3114 = _160(float2(_4162, _4160), float2(_3115, _3113));
                _3112 = _160(float2(_4163, _4160), float2(_3115, _3111));
                _3110 = _160(float2(_4164, _4160), float2(_3115, _3109));
                _3118 = _3117 + 1u;
                _3109 = _3110;
                _3111 = _3112;
                _3113 = _3114;
                _3115 = _3116;
                _3117 = _3118;
                continue;
            }
            float _4379 = _3115 * 0.282094776630401611328125f;
            float _4380 = _3113 * 0.282094776630401611328125f;
            float _4381 = _3111 * 0.282094776630401611328125f;
            float _4382 = _3109 * 0.282094776630401611328125f;
            float _4383 = _1328 * 1.1283791065216064453125f;
            float _4385 = _1326 * (-0.977204978466033935546875f);
            float _4387 = _1327 * 0.977204978466033935546875f;
            float _4389 = _1325 * (-0.977204978466033935546875f);
            float4 _4390 = float4(_4379, _4380, _4381, _4382);
            float2 _4393 = float2(_4380, _4379);
            float2 _4396 = float2(_4381, _4379);
            float2 _4399 = float2(_4382, _4379);
            float _4402 = _1360 * 1.1283791065216064453125f;
            float _4403 = _1358 * (-0.977204978466033935546875f);
            float _4404 = _1359 * 0.977204978466033935546875f;
            float _4405 = _1357 * (-0.977204978466033935546875f);
            float _4414 = _1392 * 1.1283791065216064453125f;
            float _4415 = _1390 * (-0.977204978466033935546875f);
            float _4416 = _1391 * 0.977204978466033935546875f;
            float _4417 = _1389 * (-0.977204978466033935546875f);
            _1679 = _160(_4399, float2(_4383, _4389)) * (-1.02332675457000732421875f);
            _1677 = _160(_4393, float2(_4383, _4385)) * (-1.02332675457000732421875f);
            _1675 = _160(_4396, float2(_4383, _4387)) * 1.02332675457000732421875f;
            _1673 = _194(_4390, float4(_4383, _4385, _4387, _4389)) * 0.886226952075958251953125f;
            _1671 = _160(_4399, float2(_4402, _4405)) * (-1.02332675457000732421875f);
            _1669 = _160(_4393, float2(_4402, _4403)) * (-1.02332675457000732421875f);
            _1667 = _160(_4396, float2(_4402, _4404)) * 1.02332675457000732421875f;
            _1665 = _194(_4390, float4(_4402, _4403, _4404, _4405)) * 0.886226952075958251953125f;
            _1663 = _160(_4399, float2(_4414, _4417)) * (-1.02332675457000732421875f);
            _1661 = _160(_4393, float2(_4414, _4415)) * (-1.02332675457000732421875f);
            _1659 = _160(_4396, float2(_4414, _4416)) * 1.02332675457000732421875f;
            _1657 = _194(_4390, float4(_4414, _4415, _4416, _4417)) * 0.886226952075958251953125f;
        }
        else
        {
            _1679 = _1325;
            _1677 = _1326;
            _1675 = _1327;
            _1673 = _1328;
            _1671 = _1357;
            _1669 = _1358;
            _1667 = _1359;
            _1665 = _1360;
            _1663 = _1389;
            _1661 = _1390;
            _1659 = _1391;
            _1657 = _1392;
        }
        _1656 = _1657;
        _1658 = _1659;
        _1660 = _1661;
        _1662 = _1663;
        _1664 = _1665;
        _1666 = _1667;
        _1668 = _1669;
        _1670 = _1671;
        _1672 = _1673;
        _1674 = _1675;
        _1676 = _1677;
        _1678 = _1679;
    }
    else
    {
        _1656 = _1392;
        _1658 = _1391;
        _1660 = _1390;
        _1662 = _1389;
        _1664 = _1360;
        _1666 = _1359;
        _1668 = _1358;
        _1670 = _1357;
        _1672 = _1328;
        _1674 = _1327;
        _1676 = _1326;
        _1678 = _1325;
    }
    float _1686 = max(_1672 + _173(float3(_1134 * _1678, _1134 * _1676, _1134 * _1674), _505), 0.0f);
    float _1693 = max(_1664 + _173(float3(_1135 * _1670, _1135 * _1668, _1135 * _1666), _505), 0.0f);
    float _1700 = max(_1656 + _173(float3(_1136 * _1662, _1136 * _1660, _1136 * _1658), _505), 0.0f);
    float _1712 = (asfloat(asuint(EndfieldCB1_f_0[31u].x)) - 1.0f) - mad(-log2(max(_482, 0.001000000047497451305389404296875f)), 1.2000000476837158203125f, 1.0f);
    float _1723 = floor(_742 - EndfieldCB2_f_0[2u].y);
    float _1728 = min(EndfieldCB2_f_0[1u].x - 1.0f, max(_1723, 0.0f));
    uint _1752 = (_1728 >= _1723) ? (_EndfieldBufferT0.Load((asuint(EndfieldCB1_f_0[28u].w) + uint(int(_1728))) * 4 + 0) & _EndfieldBufferT0.Load((asuint(EndfieldCB1_f_0[28u].z) + uint(int(mad(floor(_283 * EndfieldCB2_f_0[0u].w), EndfieldCB2_f_0[0u].x, floor(_282 * EndfieldCB2_f_0[0u].w))))) * 4 + 0)) : 0u;
    float _1757 = asfloat(asuint(EndfieldCB1_f_0[29u].x));
    float _1762 = _173(float3(_1686 * _1757, _1693 * _1757, _1700 * _1757), float3(0.21267290413379669189453125f, 0.715152204036712646484375f, 0.072175003588199615478515625f));
    float4 _1767 = float4(_279, _280, _281, 1.0f);
    float _1918 = 0.0f;
    float _1920 = 0.0f;
    float _1922 = 0.0f;
    float _1926 = 0.0f;
    _1918 = 0.0f;
    _1920 = 0.0f;
    _1922 = 0.0f;
    _1926 = 1.0f;
    uint _1925 = 0u;
    bool _2188 = false;
    float _1919 = 0.0f;
    float _1921 = 0.0f;
    float _1923 = 0.0f;
    float _1927 = 0.0f;
    uint _1924 = _1752;
    for (;;)
    {
        _2188 = _1926 > 0.00999999977648258209228515625f;
        if (_2188 && (_1924 != 0u))
        {
            uint _2355 = firstbitlow(_1924);
            _1925 = _1924 ^ (1u << (_2355 & 31u));
            uint _2358 = _2355 << 3u;
            uint _2359 = _2358 + 6u;
            float4 _2362 = float4(_379, _380, _381, 1.0f);
            float _2363 = _194(EndfieldCB2_f_0[_2359], _2362);
            uint _2364 = _2358 + 7u;
            float _2367 = _194(EndfieldCB2_f_0[_2364], _2362);
            uint _2368 = _2358 + 8u;
            float _2371 = _194(EndfieldCB2_f_0[_2368], _2362);
            uint _2372 = _2358 + 5u;
            float _2378 = abs(_2363);
            float _2379 = abs(_2367);
            float _2380 = abs(_2371);
            if ((EndfieldCB2_f_0[_2372].z >= _2380) && ((EndfieldCB2_f_0[_2372].y >= _2379) && (EndfieldCB2_f_0[_2372].x >= _2378)))
            {
                uint _2460 = (((16u * _2358) + 80u) + 0u) >> 2u;
                float _2463 = EndfieldCB2_f_0[_2460 >> 2u][_2460 & 3u] * 0.100000001490116119384765625f;
                float _2465 = _2378 * 0.100000001490116119384765625f;
                float _2466 = _2379 * 0.100000001490116119384765625f;
                float _2467 = _2380 * 0.100000001490116119384765625f;
                uint _2472 = _2358 + 9u;
                uint _2487 = (((16u * _2358) + 160u) + 0u) >> 2u;
                float _2631 = 0.0f;
                float _2632 = 0.0f;
                float _2633 = 0.0f;
                if (EndfieldCB2_f_0[_2487 >> 2u][_2487 & 3u] == 1.0f)
                {
                    float _2590 = _173(float3(EndfieldCB2_f_0[_2359].xyz), _841);
                    float _2597 = _173(float3(EndfieldCB2_f_0[_2364].xyz), _841);
                    float _2604 = _173(float3(EndfieldCB2_f_0[_2368].xyz), _841);
                    float _2627 = min((_2604 > 0.0f) ? ((EndfieldCB2_f_0[_2372].z - _2371) / _2604) : ((-(EndfieldCB2_f_0[_2372].z + _2371)) / _2604), min((_2597 > 0.0f) ? ((EndfieldCB2_f_0[_2372].y - _2367) / _2597) : ((-(EndfieldCB2_f_0[_2372].y + _2367)) / _2597), (_2590 > 0.0f) ? ((EndfieldCB2_f_0[_2372].x - _2363) / _2590) : ((-(EndfieldCB2_f_0[_2372].x + _2363)) / _2590)));
                    _2631 = mad(_2604, _2627, _2371);
                    _2632 = mad(_2597, _2627, _2367);
                    _2633 = mad(_2590, _2627, _2363);
                }
                else
                {
                    _2631 = _786;
                    _2632 = _785;
                    _2633 = _784;
                }
                float3 _2634 = float3(_2633, _2632, _2631);
                float _2636 = rsqrt(_173(_2634, _2634));
                float _2637 = _2636 * _2633;
                float _2638 = _2636 * _2632;
                float _2639 = _2636 * _2631;
                float _2656 = _209(((_2637 < 0.0f) ? 4294967295u : 0u) + uint(_2637 > 0.0f));
                float _2657 = _209(((_2638 < 0.0f) ? 4294967295u : 0u) + uint(_2638 > 0.0f));
                float _2661 = _173(float3(_2637, _2638, _2639), float3(_2656, _2657, _209(((_2639 < 0.0f) ? 4294967295u : 0u) + uint(_2639 > 0.0f))));
                float _2662 = _2637 / _2661;
                float _2663 = _2638 / _2661;
                bool _2665 = (_2639 / _2661) < 0.0f;
                float _2679 = max(max(_194(EndfieldCB2_f_0[_2358 + 4u], _1767), 0.0f), 9.9999997473787516355514526367188e-05f);
                uint _2691 = (((16u * _2358) + 144u) + 0u) >> 2u;
                uint _5281 = _2691 >> 2u;
                uint _5282 = _2691 & 3u;
                uint _2700 = (((16u * _2358) + 160u) + 4u) >> 2u;
                uint _5283 = _2700 >> 2u;
                uint _5284 = _2700 & 3u;
                float _2708 = clamp(mad(min(min((EndfieldCB2_f_0[_2372].z - _2380) * EndfieldCB2_f_0[_2472].z, (EndfieldCB2_f_0[_2372].y - _2379) * EndfieldCB2_f_0[_2472].y), (EndfieldCB2_f_0[_2372].x - _2378) * EndfieldCB2_f_0[_2472].x), EndfieldCB2_f_0[_5283][_5284], (((mad(_2463, _2463, -mad(_2467, _2467, mad(_2466, _2466, _2465 * _2465))) * EndfieldCB2_f_0[_5281][_5282]) * EndfieldCB2_f_0[_5281][_5282]) * (1.0f - EndfieldCB2_f_0[_5283][_5284])) * 100.0f), 0.0f, 1.0f);
                uint _2713 = (((16u * _2358) + 160u) + 12u) >> 2u;
                uint _5285 = _2713 >> 2u;
                uint _5286 = _2713 & 3u;
                float _2716 = _2708 * EndfieldCB2_f_0[_5285][_5286];
                uint _2729 = (((16u * _2358) + 80u) + 12u) >> 2u;
                float4 _2736 = _EndfieldTextureT5.SampleLevel(sampler_LinearMirrorOnce, float3(mad(mad(_2665 ? ((1.0f - abs(_2663)) * _2656) : _2662, 0.5f, 0.5f), EndfieldCB2_f_0[1u].w, EndfieldCB2_f_0[2u].w), mad(mad(_2665 ? ((1.0f - abs(_2662)) * _2657) : _2663, 0.5f, 0.5f), EndfieldCB2_f_0[1u].w, EndfieldCB2_f_0[2u].w), EndfieldCB2_f_0[_2729 >> 2u][_2729 & 3u]), _1712);
                uint _2747 = (((16u * _2358) + 144u) + 12u) >> 2u;
                uint _5289 = _2747 >> 2u;
                uint _5290 = _2747 & 3u;
                float _2765 = mad((mad(min(abs(_1762 / _2679), 1.0f), 2.0f, _1762) / (_2679 + 2.0f)) - 1.0f, asfloat(asuint(EndfieldCB1_f_0[30u].w)), 1.0f);
                _1927 = _1926 * mad(-_2708, EndfieldCB2_f_0[_5285][_5286], 1.0f);
                _1923 = mad(_2716 * (_2765 * (_2736.x * EndfieldCB2_f_0[_5289][_5290])), _1926, _1922);
                _1921 = mad(_2716 * (_2765 * (_2736.y * EndfieldCB2_f_0[_5289][_5290])), _1926, _1920);
                _1919 = mad(_2716 * (_2765 * (_2736.z * EndfieldCB2_f_0[_5289][_5290])), _1926, _1918);
            }
            else
            {
                _1927 = _1926;
                _1923 = _1922;
                _1921 = _1920;
                _1919 = _1918;
            }
            _1918 = _1919;
            _1920 = _1921;
            _1922 = _1923;
            _1924 = _1925;
            _1926 = _1927;
            continue;
        }
        else
        {
            break;
        }
    }
    float _2854 = 0.0f;
    float _2855 = 0.0f;
    float _2856 = 0.0f;
    if (_2188)
    {
        float _2775 = rsqrt(_173(_841, _841));
        float _2776 = _2775 * _784;
        float _2777 = _2775 * _785;
        float _2778 = _2775 * _786;
        float _2794 = _209(((_2776 < 0.0f) ? 4294967295u : 0u) + uint(_2776 > 0.0f));
        float _2795 = _209(((_2777 < 0.0f) ? 4294967295u : 0u) + uint(_2777 > 0.0f));
        float _2799 = _173(float3(_2776, _2777, _2778), float3(_2794, _2795, _209(((_2778 < 0.0f) ? 4294967295u : 0u) + uint(_2778 > 0.0f))));
        float _2800 = _2776 / _2799;
        float _2801 = _2777 / _2799;
        bool _2803 = (_2778 / _2799) < 0.0f;
        float _2816 = max(max(_194(EndfieldCB2_f_0[3u], _1767), 0.0f), 9.9999997473787516355514526367188e-05f);
        float4 _2829 = _EndfieldTextureT5.SampleLevel(sampler_LinearMirrorOnce, float3(mad(mad(_2803 ? ((1.0f - abs(_2801)) * _2794) : _2800, 0.5f, 0.5f), EndfieldCB2_f_0[1u].w, EndfieldCB2_f_0[2u].w), mad(mad(_2803 ? ((1.0f - abs(_2800)) * _2795) : _2801, 0.5f, 0.5f), EndfieldCB2_f_0[1u].w, EndfieldCB2_f_0[2u].w), 0.0f), _1712);
        float _2847 = mad((mad(min(abs(_1762 / _2816), 1.0f), 2.0f, _1762) / (_2816 + 2.0f)) - 1.0f, asfloat(asuint(EndfieldCB1_f_0[30u].w)), 1.0f);
        _2854 = mad(_2847 * _2829.z, _1926, _1918);
        _2855 = mad(_2847 * _2829.y, _1926, _1920);
        _2856 = mad(_2847 * _2829.x, _1926, _1922);
    }
    else
    {
        _2854 = _1918;
        _2855 = _1920;
        _2856 = _1922;
    }
    float _2861 = asfloat(asuint(EndfieldCB1_f_0[30u].z));
    float _2869 = asfloat(asuint(EndfieldCB1_f_0[29u].y));
    float _2870 = (_2856 * _2861) * _2869;
    float _2871 = (_2855 * _2861) * _2869;
    float _2872 = (_2854 * _2861) * _2869;
    float _3144 = 0.0f;
    float _3145 = 0.0f;
    float _3146 = 0.0f;
    if (asfloat(_1044.y) != 0.0f)
    {
        float4 _3121 = _EndfieldTextureT3.SampleBias(sampler_LinearRepeat, float2(TEXCOORD.x, TEXCOORD.y), _760);
        float _3123 = _3121.x;
        float4 _3130 = _EndfieldTextureT2.SampleBias(sampler_LinearRepeat, float2(TEXCOORD.x, TEXCOORD.y), _760);
        float _3137 = 1.0f - _3123;
        _3144 = mad(_3130.z, _3123, _2872 * _3137);
        _3145 = mad(_3130.y, _3123, _2871 * _3137);
        _3146 = mad(_3130.x, _3123, _2870 * _3137);
    }
    else
    {
        _3144 = _2872;
        _3145 = _2871;
        _3146 = _2870;
    }
    float _3154 = (1.0f - _583) / _583;
    float _3177 = asfloat(asuint(EndfieldCB1_f_0[74u].w));
    float _3184 = max(mad(_380, _3177, asfloat(asuint(EndfieldCB1_f_0[75u].w))), 0.00999999977648258209228515625f);
    float _3214 = (((1.0f - exp2(_3184 * (-1.44269502162933349609375f))) / _3184) * exp2(mad(_380, _3177, asfloat(asuint(EndfieldCB1_f_0[76u].w))) * 1.44269502162933349609375f)) * (-max(mad(_437, asfloat(asuint(EndfieldCB1_f_0[72u].w)), -asfloat(asuint(EndfieldCB1_f_0[71u].w))), 0.0f));
    uint4 _3218 = asuint(EndfieldCB1_f_0[73u]);
    float _3231 = exp2((_3214 * asfloat(_3218.x)) * 1.44269502162933349609375f);
    float _3232 = exp2((_3214 * asfloat(_3218.y)) * 1.44269502162933349609375f);
    float _3233 = exp2((_3214 * asfloat(_3218.z)) * 1.44269502162933349609375f);
    uint4 _3237 = asuint(EndfieldCB1_f_0[72u]);
    float _3245 = _173(_780, float3(asfloat(_3237.x), asfloat(_3237.y), asfloat(_3237.z)));
    float _3250 = asfloat(asuint(EndfieldCB1_f_0[73u].w));
    float _3255 = mad(_3250, _3250, 1.0f) - _160(_3245.xx, _3250.xx);
    float _3260 = asfloat(asuint(EndfieldCB1_f_0[83u].z));
    float _4173 = 0.0f;
    float _4174 = 0.0f;
    float _4175 = 0.0f;
    float _4176 = 0.0f;
    if (_3260 > 0.0f)
    {
        uint _3589 = (_220 * 1664525u) + 1013904223u;
        uint _3590 = ((asuint(EndfieldCB1_f_0[26u].w) & 7u) * 1664525u) + 1013904223u;
        uint _3592 = ((_219 * 1664525u) + 1013904223u) + (_3590 * _3589);
        uint _3594 = _3589 + (_3590 * _3592);
        uint _3596 = _3590 + (_3592 * _3594);
        uint _3598 = _3592 + (_3594 * _3596);
        float _3603 = _173(_780, float3(-_393, -_387, -_399));
        float _3608 = asfloat(asuint(EndfieldCB0_f_0[44u].y));
        float _3609 = _380 - _3608;
        bool _3610 = _3603 > 5.9604644775390625e-08f;
        float _3618 = asfloat(asuint(EndfieldCB1_f_0[83u].w)) * (1.0f / _3603);
        float _3620 = 1.0f / _437;
        float _3621 = _3620 * _3618;
        float _3624 = _3610 ? mad(_3609, _3621, _3608) : _3608;
        float _3626 = mad(-(_3610 ? _3621 : 0.0f), _3609, _3609);
        float _3628 = mad(-(_3610 ? _3618 : 0.0f), _3620, 1.0f);
        float _3634 = asfloat(asuint(EndfieldCB1_f_0[77u].z));
        float _3636 = max(_3626 * _3634, -127.0f);
        float _3642 = asfloat(asuint(EndfieldCB1_f_0[80u].x));
        float _3644 = max(_3626 * _3642, -127.0f);
        float _3663 = -_3636;
        float _3689 = -_3644;
        float _3696 = mad(exp2(-max((_3624 - asfloat(asuint(EndfieldCB1_f_0[77u].x))) * _3634, -127.0f)) * asfloat(asuint(EndfieldCB1_f_0[77u].y)), (abs(_3636) > 5.9604644775390625e-08f) ? ((1.0f - exp2(_3663)) / _3636) : mad(_3663, 0.2402265071868896484375f, 0.693147182464599609375f), ((abs(_3644) > 5.9604644775390625e-08f) ? ((1.0f - exp2(_3689)) / _3644) : mad(_3689, 0.2402265071868896484375f, 0.693147182464599609375f)) * (exp2(-max((_3624 - asfloat(asuint(EndfieldCB1_f_0[80u].z))) * _3642, -127.0f)) * asfloat(asuint(EndfieldCB1_f_0[80u].y))));
        float _3719 = clamp(mad(_437, asfloat(asuint(EndfieldCB1_f_0[78u].w)), asfloat(asuint(EndfieldCB1_f_0[78u].z))), 0.0f, 1.0f);
        float _3733 = min(_3719 + (clamp(mad(_437, asfloat(asuint(EndfieldCB1_f_0[78u].y)), asfloat(asuint(EndfieldCB1_f_0[78u].x))), 0.0f, 1.0f) + max(min(exp2(-((_437 * _3628) * _3696)), 1.0f), asfloat(asuint(EndfieldCB1_f_0[79u].w)))), 1.0f);
        float _3747 = asfloat(asuint(EndfieldCB1_f_0[87u].w));
        uint4 _3753 = asuint(EndfieldCB1_f_0[85u]);
        float4 _3782 = _EndfieldTextureT15.SampleLevel(sampler_LinearRepeat, float3(mad(mad(_186(_3598 >> 16u), 3.05180437862873077392578125e-05f, -1.0f), _3747, _282) * asfloat(_3753.x), mad(mad(_186((_3594 + (_3596 * _3598)) >> 16u), 3.05180437862873077392578125e-05f, -1.0f), _3747, _283) * asfloat(_3753.y), (log2(mad(_742, asfloat(asuint(EndfieldCB1_f_0[84u].x)), asfloat(asuint(EndfieldCB1_f_0[84u].y)))) * asfloat(asuint(EndfieldCB1_f_0[84u].z))) / _3260), 0.0f);
        float _3797 = clamp((_742 - asfloat(asuint(EndfieldCB1_f_0[86u].z))) * 1000000.0f, 0.0f, 1.0f);
        float _3802 = mad(_3797, _3782.w - 1.0f, 1.0f);
        float _3803 = 1.0f - _3733;
        uint4 _3807 = asuint(EndfieldCB1_f_0[81u]);
        float _3824 = exp2(log2(clamp(_173(_506, float3(asfloat(_3807.x), asfloat(_3807.y), asfloat(_3807.z))), 0.0f, 1.0f)) * asfloat(asuint(EndfieldCB1_f_0[82u].w)));
        uint4 _3828 = asuint(EndfieldCB1_f_0[82u]);
        float _3850 = 1.0f - min(exp2(-(max(mad(_3628, _437, -asfloat(asuint(EndfieldCB1_f_0[81u].w))), 0.0f) * _3696)), 1.0f);
        float _3854 = 1.0f - _3719;
        uint4 _3861 = asuint(EndfieldCB1_f_0[79u]);
        _4173 = mad(mad(asfloat(_3861.z), _3803, _3854 * (_3850 * (_3824 * asfloat(_3828.z)))), _3802, _3797 * _3782.z);
        _4174 = mad(mad(asfloat(_3861.y), _3803, _3854 * (_3850 * (_3824 * asfloat(_3828.y)))), _3802, _3797 * _3782.y);
        _4175 = mad(mad(asfloat(_3861.x), _3803, _3854 * (_3850 * (_3824 * asfloat(_3828.x)))), _3802, _3797 * _3782.x);
        _4176 = _3733 * _3802;
    }
    else
    {
        float _3878 = asfloat(asuint(EndfieldCB0_f_0[44u].y));
        float _3879 = _380 - _3878;
        float _3883 = asfloat(asuint(EndfieldCB1_f_0[77u].z));
        float _3888 = asfloat(asuint(EndfieldCB1_f_0[80u].x));
        float _3896 = max(_3879 * _3888, -127.0f);
        float _3897 = max(_3879 * _3883, -127.0f);
        float _3908 = -_3897;
        float _3930 = -_3896;
        float _3937 = mad(exp2(-max((_3878 - asfloat(asuint(EndfieldCB1_f_0[77u].x))) * _3883, -127.0f)) * asfloat(asuint(EndfieldCB1_f_0[77u].y)), (abs(_3897) > 5.9604644775390625e-08f) ? ((1.0f - exp2(_3908)) / _3897) : mad(_3908, 0.2402265071868896484375f, 0.693147182464599609375f), ((abs(_3896) > 5.9604644775390625e-08f) ? ((1.0f - exp2(_3930)) / _3896) : mad(_3930, 0.2402265071868896484375f, 0.693147182464599609375f)) * (exp2(-max((_3878 - asfloat(asuint(EndfieldCB1_f_0[80u].z))) * _3888, -127.0f)) * asfloat(asuint(EndfieldCB1_f_0[80u].y))));
        float _3956 = clamp(mad(_437, asfloat(asuint(EndfieldCB1_f_0[78u].w)), asfloat(asuint(EndfieldCB1_f_0[78u].z))), 0.0f, 1.0f);
        float _3969 = min(_3956 + (clamp(mad(_437, asfloat(asuint(EndfieldCB1_f_0[78u].y)), asfloat(asuint(EndfieldCB1_f_0[78u].x))), 0.0f, 1.0f) + max(min(exp2(-(_437 * _3937)), 1.0f), asfloat(asuint(EndfieldCB1_f_0[79u].w)))), 1.0f);
        uint4 _3972 = asuint(EndfieldCB1_f_0[81u]);
        float _3988 = exp2(log2(clamp(_173(_506, float3(asfloat(_3972.x), asfloat(_3972.y), asfloat(_3972.z))), 0.0f, 1.0f)) * asfloat(asuint(EndfieldCB1_f_0[82u].w)));
        uint4 _3991 = asuint(EndfieldCB1_f_0[82u]);
        float _4012 = 1.0f - min(exp2(-(_3937 * max(mad(_430, _433, -asfloat(asuint(EndfieldCB1_f_0[81u].w))), 0.0f))), 1.0f);
        float _4013 = 1.0f - _3969;
        float _4017 = 1.0f - _3956;
        uint4 _4023 = asuint(EndfieldCB1_f_0[79u]);
        _4173 = mad(asfloat(_4023.z), _4013, _4017 * (_4012 * (_3988 * asfloat(_3991.z))));
        _4174 = mad(asfloat(_4023.y), _4013, _4017 * (_4012 * (_3988 * asfloat(_3991.y))));
        _4175 = mad(asfloat(_4023.x), _4013, _4017 * (_4012 * (_3988 * asfloat(_3991.x))));
        _4176 = _3969;
    }
    float _4177 = _4176 * _3231;
    float _4178 = _4176 * _3232;
    float _4179 = _4176 * _3233;
    float _4184 = mad(_3245, _3245, 1.0f) * 0.0596831031143665313720703125f;
    uint4 _4189 = asuint(EndfieldCB1_f_0[74u]);
    uint4 _4199 = asuint(EndfieldCB1_f_0[76u]);
    float _4216 = mad(-_3250, _3250, 1.0f) / max(sqrt(_3255) * (_3255 * 12.56637096405029296875f), 0.001000000047497451305389404296875f);
    uint4 _4220 = asuint(EndfieldCB1_f_0[75u]);
    SV_Target.x = mad(clamp(mad((_496 * _1686) * _1757, _1116, _1115 * (_3146 * mad(_3154 * _502, _580, _580))) + mad(_1019, _1021, _712), 0.0f, 255.0f), _4177, mad((1.0f - _3231) * (clamp(mad(asfloat(_4220.x), _4216, mad(asfloat(_4189.x), _4184, asfloat(_4199.x))), 0.0f, 1.0f) * 255.0f), _4176, _4175));
    SV_Target.y = mad(clamp(mad((_497 * _1693) * _1757, _1117, _1115 * (_3145 * mad(_3154 * _503, _581, _581))) + mad(_1017, _1021, _714), 0.0f, 255.0f), _4178, mad((1.0f - _3232) * (clamp(mad(asfloat(_4220.y), _4216, mad(asfloat(_4189.y), _4184, asfloat(_4199.y))), 0.0f, 1.0f) * 255.0f), _4176, _4174));
    SV_Target.z = mad(clamp(mad((_498 * _1700) * _1757, _1118, _1115 * (_3144 * mad(_3154 * _504, _582, _582))) + mad(_1015, _1021, _716), 0.0f, 255.0f), _4179, mad((1.0f - _3233) * (clamp(mad(asfloat(_4220.z), _4216, mad(asfloat(_4189.z), _4184, asfloat(_4199.z))), 0.0f, 1.0f) * 255.0f), _4176, _4173));
    SV_Target.w = _173(float3(_4177, _4178, _4179), 0.3333333432674407958984375f.xxx);
}

SPIRV_Cross_Output main(SPIRV_Cross_Input stage_input)
{
    gl_FragCoord = stage_input.gl_FragCoord;
    gl_FragCoord.w = 1.0 / gl_FragCoord.w;
    TEXCOORD = stage_input.TEXCOORD;
    frag_main();
    SPIRV_Cross_Output stage_output;
    stage_output.SV_Target = SV_Target;
    return stage_output;
}
