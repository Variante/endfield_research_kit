struct DiagnosticTextureVsOutput
{
    float4 position : SV_Position;
    float4 texcoord0 : TEXCOORD0;
    float4 texcoord1 : TEXCOORD1;
    float4 texcoord2 : TEXCOORD2;
    float3 texcoord3 : TEXCOORD3;
    float4 texcoord4 : TEXCOORD4;
    float4 texcoord5 : TEXCOORD5;
    float3 texcoord6 : TEXCOORD6;
    float3 texcoord7 : TEXCOORD7;
};

DiagnosticTextureVsOutput main(uint vertexId : SV_VertexID)
{
    DiagnosticTextureVsOutput output;
    float2 position = vertexId == 0 ? float2(-1.0, -1.0) :
                      (vertexId == 1 ? float2(-1.0, 3.0) : float2(3.0, -1.0));
    float2 uv = position * 0.5 + 0.5;
    output.position = float4(position, 0.5, 1.0);
    output.texcoord0 = float4(uv, 0.0, 1.0);
    output.texcoord1 = float4(uv, 0.0, 1.0);
    output.texcoord2 = float4(uv, 0.0, 1.0);
    output.texcoord3 = float3(0.0, 0.0, 0.0);
    output.texcoord4 = float4(uv, 0.0, 1.0);
    output.texcoord5 = float4(1.0, 1.0, 1.0, 1.0);
    output.texcoord6 = float3(0.0, 0.0, 1.0);
    output.texcoord7 = float3(0.0, 0.0, 1.0);
    return output;
}
