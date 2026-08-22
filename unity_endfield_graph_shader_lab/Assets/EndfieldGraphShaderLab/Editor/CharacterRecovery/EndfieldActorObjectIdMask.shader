Shader "Hidden/Endfield/ActorObjectIdMask"
{
    SubShader
    {
        Tags { "RenderType"="Opaque" }
        Pass
        {
            ZWrite On
            ZTest LEqual
            Cull Back
            ColorMask RGBA
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "UnityCG.cginc"
            struct A { float4 vertex : POSITION; };
            struct V { float4 pos : SV_POSITION; };
            V vert(A v) { V o; o.pos = UnityObjectToClipPos(v.vertex); return o; }
            float4 frag() : SV_Target { return float4(1,1,1,1); }
            ENDHLSL
        }
    }
}
