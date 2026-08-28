#define WIN32_LEAN_AND_MEAN
#include <Windows.h>
#include <d3d11.h>

#include <cstdint>
#include <cstdio>
#include <cstdlib>

namespace
{
template <typename T>
T RequiredExport(HMODULE module, const char* name)
{
    FARPROC address = GetProcAddress(module, name);
    if (address == nullptr)
        std::fprintf(stderr, "missing_export=%s\n", name);
    return reinterpret_cast<T>(address);
}

HRESULT CreateTexture(
    ID3D11Device* device,
    UINT width,
    UINT height,
    DXGI_FORMAT format,
    ID3D11Texture2D** output)
{
    D3D11_TEXTURE2D_DESC description = {};
    description.Width = width;
    description.Height = height;
    description.MipLevels = 1;
    description.ArraySize = 1;
    description.Format = format;
    description.SampleDesc.Count = 1;
    description.Usage = D3D11_USAGE_DEFAULT;
    description.BindFlags = D3D11_BIND_SHADER_RESOURCE;
    return device->CreateTexture2D(&description, nullptr, output);
}
}

int main(int argc, char** argv)
{
    if (argc != 3)
    {
        std::fprintf(stderr, "usage: VerifyEndminfUberTransport DLL EXPECTED_READY\n");
        return 2;
    }
    const std::uint32_t expectedReady =
        static_cast<std::uint32_t>(std::strtoul(argv[2], nullptr, 10));
    HMODULE module = LoadLibraryA(argv[1]);
    if (module == nullptr)
    {
        std::fprintf(stderr, "load_error=%lu\n", GetLastError());
        return 3;
    }

    using GetUint = std::uint32_t (*)();
    using GetInt = std::int32_t (*)();
    using GetEvent = void* (*)();
    using SetTextures = std::uint32_t (*)(void*, void*, void*);
    using QueuePacket = std::uint32_t (*)(
        float, float, float, float, float, float, float);
    using Reset = void (*)();
    const GetUint payloadReady = RequiredExport<GetUint>(
        module, "EndfieldOriginalDxbcGetEndminfUberPayloadReady");
    const GetEvent getEvent = RequiredExport<GetEvent>(
        module, "EndfieldOriginalDxbcGetEndminfUberRenderEventFunc");
    const SetTextures setTextures = RequiredExport<SetTextures>(
        module, "EndfieldOriginalDxbcSetEndminfUberTextureResources");
    const QueuePacket queue = RequiredExport<QueuePacket>(
        module, "EndfieldOriginalDxbcQueueEndminfUberPacket");
    const Reset reset = RequiredExport<Reset>(
        module, "EndfieldOriginalDxbcResetEndminfUberRuntimeState");
    const GetUint drawCount = RequiredExport<GetUint>(
        module, "EndfieldOriginalDxbcGetEndminfUberDrawCount");
    const GetUint failureCount = RequiredExport<GetUint>(
        module, "EndfieldOriginalDxbcGetEndminfUberFailureCount");
    const GetInt lastResult = RequiredExport<GetInt>(
        module, "EndfieldOriginalDxbcGetEndminfUberLastResult");
    const GetUint failureStage = RequiredExport<GetUint>(
        module, "EndfieldOriginalDxbcGetEndminfUberFailureStage");
    if (payloadReady == nullptr || getEvent == nullptr || setTextures == nullptr ||
        queue == nullptr || reset == nullptr || drawCount == nullptr ||
        failureCount == nullptr || lastResult == nullptr || failureStage == nullptr)
    {
        FreeLibrary(module);
        return 4;
    }

    reset();
    if (payloadReady() != expectedReady || getEvent() == nullptr ||
        drawCount() != 0u || failureCount() != 0u || lastResult() != 0 ||
        failureStage() != 0u)
    {
        FreeLibrary(module);
        return 5;
    }
    if (setTextures(nullptr, nullptr, nullptr) != 0u ||
        failureCount() != 1u || failureStage() != 301u)
    {
        FreeLibrary(module);
        return 6;
    }
    reset();
    const std::uint32_t eventId = queue(
        1920.0f, 1080.0f, 1.0f,
        0.5f, 0.5f, 0.1f, 1.0f);
    const std::uint32_t expectedStage = expectedReady == 0u ? 401u : 403u;
    if (eventId != 0u || failureCount() != 1u ||
        failureStage() != expectedStage || lastResult() == 0)
    {
        FreeLibrary(module);
        return 7;
    }
    reset();
    if (expectedReady != 0u)
    {
        if (queue(
                1920.0f, 1080.0f, 1.0f,
                0.5f, 0.5f, -0.1f, 1.0f) != 0u ||
            failureCount() != 1u || failureStage() != 402u)
        {
            FreeLibrary(module);
            return 8;
        }
        reset();

        ID3D11Device* device = nullptr;
        ID3D11DeviceContext* context = nullptr;
        D3D_FEATURE_LEVEL featureLevel = D3D_FEATURE_LEVEL_11_0;
        HRESULT result = D3D11CreateDevice(
            nullptr, D3D_DRIVER_TYPE_WARP, nullptr, 0,
            &featureLevel, 1, D3D11_SDK_VERSION,
            &device, nullptr, &context);
        ID3D11Texture2D* textures[3] = {};
        if (SUCCEEDED(result))
            result = CreateTexture(
                device, 1920u, 1080u, DXGI_FORMAT_R16G16B16A16_FLOAT,
                &textures[0]);
        if (SUCCEEDED(result))
            result = CreateTexture(
                device, 960u, 540u, DXGI_FORMAT_R11G11B10_FLOAT,
                &textures[1]);
        if (SUCCEEDED(result))
            result = CreateTexture(
                device, 1024u, 32u, DXGI_FORMAT_R16G16B16A16_FLOAT,
                &textures[2]);
        if (FAILED(result) || setTextures(
                textures[0], textures[1], textures[2]) == 0u)
        {
            for (ID3D11Texture2D* texture : textures)
                if (texture != nullptr) texture->Release();
            if (context != nullptr) context->Release();
            if (device != nullptr) device->Release();
            FreeLibrary(module);
            return 9;
        }

        std::uint32_t queuedIds[64] = {};
        for (std::size_t index = 0; index < 64; ++index)
        {
            queuedIds[index] = queue(
                1920.0f, 1080.0f, 1.0f,
                0.5f, 0.5f,
                index == 0 ? 0.0f : 0.1f,
                1.0f);
            if (queuedIds[index] == 0u)
            {
                FreeLibrary(module);
                return 10;
            }
            for (std::size_t prior = 0; prior < index; ++prior)
            {
                if (queuedIds[index] == queuedIds[prior])
                {
                    FreeLibrary(module);
                    return 11;
                }
            }
        }
        if (queue(
                1920.0f, 1080.0f, 1.0f,
                0.5f, 0.5f, 0.1f, 1.0f) != 0u ||
            failureCount() != 1u || failureStage() != 404u)
        {
            FreeLibrary(module);
            return 12;
        }
        reset();
        for (ID3D11Texture2D* texture : textures)
            texture->Release();
        context->Release();
        device->Release();
    }
    if (drawCount() != 0u || failureCount() != 0u ||
        lastResult() != 0 || failureStage() != 0u)
    {
        FreeLibrary(module);
        return 13;
    }
    std::printf(
        "payload_ready=%u exports=9 fail_closed_stage=%u ring_tested=%u reset=1\n",
        expectedReady, expectedStage, expectedReady != 0u ? 64u : 0u);
    FreeLibrary(module);
    return 0;
}
