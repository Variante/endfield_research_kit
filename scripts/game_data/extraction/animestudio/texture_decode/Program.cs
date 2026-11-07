using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using System.IO.Compression;
using Microsoft.Data.Sqlite;
using AnimeStudio.CLI;

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
            if (name == "SQLitePCLRaw.provider.e_sqlite3")
                NativeLibrary.SetDllImportResolver(assembly, (library, _, _) => {
                    if (library != "e_sqlite3" || !OperatingSystem.IsWindows() || RuntimeInformation.ProcessArchitecture != Architecture.X64)
                        throw new DllNotFoundException("Unsupported selected SQLite library/platform");
                    return NativeLibrary.Load(Path.Combine(args[0], "runtimes", "win-x64", "native", "e_sqlite3.dll"));
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
        using var store = UnityDocumentStoreWriter.OpenDetached(new FileInfo(args[2] + ".sqlite"), UnityDocumentStoreWriter.Schema);
        var outputs=new List<object>();var seen=new HashSet<string>();
        foreach(var row in rows)
        {
            var key=row.GetProperty("key").GetString();var width=row.GetProperty("width").GetInt32();var height=row.GetProperty("height").GetInt32();
            var format=row.GetProperty("formatId").GetInt32();var bytes=ReadInput(row.GetProperty("input").GetString());
            var blockBytes=format switch {10 or 26=>8,12 or 25 or 27=>16,_=>throw new InvalidDataException("Unsupported block format")};
            if(key.Length!=64||key.Any(c=>!"0123456789abcdef".Contains(c))||!seen.Add(key)||width<=0||height<=0||(long)width*height>16777216
                ||bytes.Length!=checked(((width+3)/4)*((height+3)/4)*blockBytes)||Hash(bytes)!=row.GetProperty("sha256").GetString())
                throw new InvalidDataException("Top mip key/dimensions/byte gate differs");
            var pixels=new byte[checked(width*height*4)];
            if(!new AnimeStudio.Texture2DConverter((AnimeStudio.TextureFormat)format,width,height,bytes).DecodeTexture2D(pixels))
                throw new InvalidDataException("Declared texture decoder returned unavailable: "+key);
            var name=key+".bgra32";store.Put("decoded", name, pixels);
            outputs.Add(new {key,file=name,width,height,sha256=Hash(pixels),bytes=pixels.Length});
        }
        store.Put("decoded", "decoded.json", System.Text.Encoding.UTF8.GetBytes(JsonSerializer.Serialize(new {schema="endfield.texture-top-mip-decode.v1",rows=outputs})));
        store.Complete();
        return 0;
    }
    static byte[] ReadInput(string reference)
    {
        var marker = reference.IndexOf(".sqlite", StringComparison.OrdinalIgnoreCase);
        if (marker < 0) return File.ReadAllBytes(reference);
        var database = reference[..(marker + 7)];
        var relative = reference[(marker + 8)..].Replace('\\', '/');
        if (!relative.StartsWith("inputs/", StringComparison.Ordinal) || relative.Contains(".."))
            throw new InvalidDataException("Invalid mip database row");
        using var connection = new SqliteConnection(new SqliteConnectionStringBuilder {
            DataSource = database, Mode = SqliteOpenMode.ReadOnly, Pooling = false
        }.ToString());
        connection.Open();
        using var schema = connection.CreateCommand();
        schema.CommandText = "SELECT value FROM meta WHERE key='schema'";
        if (!Equals(schema.ExecuteScalar(), UnityDocumentStoreWriter.Schema))
            throw new InvalidDataException("Invalid mip database schema");
        using var command = connection.CreateCommand();
        command.CommandText = "SELECT data, size, sha256 FROM objects WHERE type='inputs' AND name=$name";
        command.Parameters.AddWithValue("$name", relative["inputs/".Length..]);
        using var reader = command.ExecuteReader();
        if (!reader.Read()) throw new InvalidDataException("Missing mip database row");
        using var compressed = new MemoryStream((byte[])reader[0]);
        using var zlib = new ZLibStream(compressed, CompressionMode.Decompress);
        using var result = new MemoryStream();
        zlib.CopyTo(result);
        var bytes = result.ToArray();
        if (bytes.LongLength != reader.GetInt64(1) || Hash(bytes) != reader.GetString(2).ToLowerInvariant())
            throw new InvalidDataException("Mip database row length/hash differs");
        return bytes;
    }

}
