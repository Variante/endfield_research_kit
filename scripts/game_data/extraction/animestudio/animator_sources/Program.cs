using System.IO.Compression;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

// Read selected complete serialized directories without loading Mesh/Texture
// dependencies or converting models. The Python caller supplies current map
// selection/freshness gates and owns hierarchy and FBX coverage comparison.
class Program
{
    static int Main(string[] args)
    {
        if (args.Length != 3) { Console.Error.WriteLine("Expected CLI directory, selected sources JSON, output JSONL.gz"); return 2; }
        AppDomain.CurrentDomain.AssemblyResolve += (_, e) => {
            var path=Path.Combine(args[0],new AssemblyName(e.Name).Name+".dll");
            return File.Exists(path)?Assembly.LoadFrom(path):null;
        };
        try { return Run(args); } catch(Exception error) { Console.Error.WriteLine(error);return 1; }
    }
    static string Hash(byte[] data)=>Convert.ToHexString(SHA256.HashData(data)).ToLowerInvariant();
    [MethodImpl(MethodImplOptions.NoInlining)]
    static int Run(string[] args)
    {
        var selection=JArray.Parse(File.ReadAllText(args[1])).Cast<JObject>().ToArray();
        if(selection.Length==0)throw new InvalidDataException("Empty source selection");
        AnimeStudio.Logger.Default=new AnimeStudio.ConsoleLogger();
        AnimeStudio.Logger.Flags=AnimeStudio.LoggerEvent.Warning|AnimeStudio.LoggerEvent.Error;
        AnimeStudio.Progress.Silent=true;
        var classes=new HashSet<int>{1,4,23,33,95,137,224};
        using var fileOutput=File.Create(args[2]);
        using var gzip=new GZipStream(fileOutput,CompressionLevel.Fastest);
        using var writer=new StreamWriter(gzip,new UTF8Encoding(false));
        void Write(object row){writer.WriteLine(JsonConvert.SerializeObject(row,Formatting.None));}
        int directories=0,errors=0;
        foreach(var physical in selection.GroupBy(r=>Path.GetFullPath((string)r["Source"]),StringComparer.OrdinalIgnoreCase))
        foreach(var batch in physical.Select(r=>(long)r["Offset"]).Distinct().Order().Chunk(24))
        {
            var manager=new AnimeStudio.AssetsManager{Game=AnimeStudio.GameManager.GetGame("ArknightsEndfield"),SkipProcess=true};
            foreach(var offset in batch)manager.FilterData.Items.Add(new AnimeStudio.AssetsManager.AssetFilterDataItem{
                Source=physical.Key,Offset=offset,Type=AnimeStudio.ClassIDType.AssetBundle,PathID=0,Name=""});
            try
            {
                manager.LoadPreparedFiles(physical.Key);
                var found=new HashSet<long>();
                foreach(var file in manager.assetsFileList)
                {
                    if(Path.GetFullPath(file.originalPath)!=physical.Key || !batch.Contains(file.offset) || (int)file.header.m_Version!=22)
                        throw new InvalidDataException("Unselected directory or unsupported serialized version");
                    found.Add(file.offset);
                    var objects=new List<object>();
                    foreach(var item in file.m_Objects.Where(o=>classes.Contains(o.classID)))
                    {
                        var asset=new AnimeStudio.Object(new AnimeStudio.ObjectReader(file.reader,file,item,manager.Game));
                        var raw=asset.GetRawData();var body=asset.ToType();
                        if(body==null || asset.reader.Position-asset.reader.byteStart!=item.byteSize)
                            throw new InvalidDataException($"Generic body EOF/schema differs: {file.fileName}/{item.m_PathID}; class={item.classID}");
                        objects.Add(new{pathId=item.m_PathID,classId=item.classID,rawSha256=Hash(raw),body});
                    }
                    file.reader.Position=0;var metadata=file.reader.ReadBytes(checked((int)file.header.m_MetadataSize+48));
                    Write(new{kind="directory",source=file.originalPath,offset=file.offset,cab=file.fileName,
                        metadataSha256=Hash(metadata),objectCount=file.m_Objects.Count,
                        classNames=file.m_Objects.Select(o=>new{pathId=o.m_PathID,classId=o.classID,typeName=((AnimeStudio.ClassIDType)o.classID).ToString()}).ToArray(),
                        externals=file.m_Externals.Select(e=>e.pathName).ToArray(),objects});
                    directories++;
                }
                if(batch.Any(offset=>!found.Contains(offset)))throw new InvalidDataException("A selected physical bundle was not read");
            }
            catch(Exception error)
            {
                errors++;Write(new{kind="error",source=physical.Key,offsets=batch,error=error.ToString()});
            }
            finally{manager.Clear();}
            writer.Flush();
            Console.WriteLine($"directories={directories}; errors={errors}");
        }
        Write(new{kind="summary",schema="endfield.animator-source-declarations.v1",complete=errors==0,directories,errors});
        return errors==0?0:3;
    }
}
