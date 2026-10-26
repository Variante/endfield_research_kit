using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;

class Program
{
    static int Main(string[] args)
    {
        if(args.Length!=3) { Console.Error.WriteLine("Expected admitted CLI directory, input manifest, output directory"); return 2; }
        AppDomain.CurrentDomain.AssemblyResolve += (_,e) => {
            var name=new AssemblyName(e.Name).Name;var path=Path.Combine(args[0],name+".dll");
            if(!File.Exists(path)) return null;
            var assembly=Assembly.LoadFrom(path);
            if(name=="Texture2DDecoderWrapper") NativeLibrary.SetDllImportResolver(assembly,(library,_,_)=> {
                if(library!="Texture2DDecoderNative"||!OperatingSystem.IsWindows()||RuntimeInformation.ProcessArchitecture!=Architecture.X64)
                    throw new DllNotFoundException("Unsupported selected texture codec platform/library");
                return NativeLibrary.Load(Path.Combine(args[0],"runtimes","win-x64","native","Texture2DDecoderNative.dll"));
            });
            return assembly;
        };
        try { return Run(args); } catch(Exception e) { Console.Error.WriteLine(e); return 1; }
    }
    static string Hash(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
    [MethodImpl(MethodImplOptions.NoInlining)]
    static int Run(string[] args)
    {
        var rows=JsonDocument.Parse(File.ReadAllBytes(args[1])).RootElement.EnumerateArray();
        Directory.CreateDirectory(args[2]); var outputs=new List<object>();var seen=new HashSet<string>();
        foreach(var row in rows)
        {
            var key=row.GetProperty("key").GetString();var width=row.GetProperty("width").GetInt32();var height=row.GetProperty("height").GetInt32();
            var format=row.GetProperty("formatId").GetInt32();var bytes=File.ReadAllBytes(row.GetProperty("input").GetString());
            var blockBytes=format switch {10 or 26=>8,12 or 25 or 27=>16,_=>throw new InvalidDataException("Unsupported block format")};
            if(key.Length!=64||key.Any(c=>!"0123456789abcdef".Contains(c))||!seen.Add(key)||width<=0||height<=0||(long)width*height>16777216
                ||bytes.Length!=checked(((width+3)/4)*((height+3)/4)*blockBytes)||Hash(bytes)!=row.GetProperty("sha256").GetString())
                throw new InvalidDataException("Top mip key/dimensions/byte gate differs");
            var pixels=new byte[checked(width*height*4)];
            if(!new AnimeStudio.Texture2DConverter((AnimeStudio.TextureFormat)format,width,height,bytes).DecodeTexture2D(pixels))
                throw new InvalidDataException("Declared texture decoder returned unavailable: "+key);
            var name=key+".bgra32";File.WriteAllBytes(Path.Combine(args[2],name),pixels);
            outputs.Add(new {key,file=name,width,height,sha256=Hash(pixels),bytes=pixels.Length});
        }
        File.WriteAllText(Path.Combine(args[2],"decoded.json"),JsonSerializer.Serialize(new {schema="endfield.texture-top-mip-decode.v1",rows=outputs}));
        return 0;
    }
}
