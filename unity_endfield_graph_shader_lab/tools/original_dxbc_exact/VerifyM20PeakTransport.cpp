#define WIN32_LEAN_AND_MEAN
#include <Windows.h>

#include <cstdint>
#include <cstdio>

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
}

int main(int argc, char** argv)
{
    if (argc != 2)
    {
        std::fprintf(stderr, "usage: VerifyM20PeakTransport DLL\n");
        return 2;
    }
    HMODULE module = LoadLibraryA(argv[1]);
    if (module == nullptr)
    {
        std::fprintf(stderr, "load_error=%lu\n", GetLastError());
        return 3;
    }

    using GetEvent = void* (*)();
    using SetDepth = std::uint32_t (*)(void*);
    using Reset = void (*)();
    using GetUint = std::uint32_t (*)();
    using GetInt = std::int32_t (*)();
    const GetEvent getEvent = RequiredExport<GetEvent>(
        module, "EndfieldOriginalDxbcGetM20PeakRenderEventFunc");
    const SetDepth setDepth = RequiredExport<SetDepth>(
        module, "EndfieldOriginalDxbcSetM20PeakDepthResource");
    const Reset reset = RequiredExport<Reset>(
        module, "EndfieldOriginalDxbcResetM20PeakRuntimeState");
    const GetUint drawCount = RequiredExport<GetUint>(
        module, "EndfieldOriginalDxbcGetM20PeakDrawCount");
    const GetUint failureCount = RequiredExport<GetUint>(
        module, "EndfieldOriginalDxbcGetM20PeakFailureCount");
    const GetInt lastResult = RequiredExport<GetInt>(
        module, "EndfieldOriginalDxbcGetM20PeakLastResult");
    if (getEvent == nullptr || setDepth == nullptr || reset == nullptr ||
        drawCount == nullptr || failureCount == nullptr || lastResult == nullptr)
    {
        FreeLibrary(module);
        return 4;
    }

    reset();
    if (getEvent() == nullptr || setDepth(nullptr) != 0u ||
        drawCount() != 0u || failureCount() != 0u || lastResult() != 0)
    {
        FreeLibrary(module);
        return 5;
    }
    std::printf("exports=6 initial_state=clean null_depth_rejected=1\n");
    FreeLibrary(module);
    return 0;
}
