using System.Reflection;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text.Json;

class Program
{
    static int Main(string[] args)
    {
        if(args.Length!=2) {Console.Error.WriteLine("Expected admitted CLI directory and manifest");return 2;}
        AppDomain.CurrentDomain.AssemblyResolve+=(_,e)=>{
            var path=Path.Combine(args[0],new AssemblyName(e.Name).Name+".dll");
            return File.Exists(path)?Assembly.LoadFrom(path):null;
        };
        try {Run(args);return 0;}catch(Exception e){Console.Error.WriteLine(e);return 1;}
    }
    static string Hash(byte[] b)=>Convert.ToHexString(SHA256.HashData(b)).ToLowerInvariant();
    [MethodImpl(MethodImplOptions.NoInlining)]
    static void Run(string[] args)
    {
        var manifest=JsonDocument.Parse(File.ReadAllBytes(args[1])).RootElement;
        foreach(var row in manifest.GetProperty("segments").EnumerateArray())
        {
            var raw=File.ReadAllBytes(row.GetProperty("input").GetString());
            if(Hash(raw)!=row.GetProperty("inputSha256").GetString())throw new InvalidDataException("Compressed input changed");
            var n=row.GetProperty("decodedBytes").GetInt32();if(n<0||n>128*1024*1024)throw new InvalidDataException("Decoded size exceeds bounds");
            var decoded=new byte[n];var written=AnimeStudio.LZ4.Instance.Decompress(raw,decoded);
            if(written!=n||Hash(decoded)!=row.GetProperty("decodedSha256").GetString())throw new InvalidDataException("Independent LZ4/CLI parity differs");
        }
        foreach(var row in manifest.GetProperty("codeRecords").EnumerateArray())
        {
            var raw=File.ReadAllBytes(row.GetProperty("input").GetString());
            if(Hash(raw)!=row.GetProperty("inputSha256").GetString())throw new InvalidDataException("Code record changed");
            using var reader=new AnimeStudio.EndianBinaryReader(new MemoryStream(raw),AnimeStudio.EndianType.LittleEndian);
            var parsed=new AnimeStudio.ShaderSubProgram(reader,false,raw.Length);
            if(reader.Position!=raw.Length||Hash(parsed.m_ProgramCode)!=row.GetProperty("codeSha256").GetString()
                ||!parsed.m_Keywords.SequenceEqual(row.GetProperty("keywords").EnumerateArray().Select(v=>v.GetString())))
                throw new InvalidDataException("Independent native-code record/CLI parity differs");
        }
    }
}
