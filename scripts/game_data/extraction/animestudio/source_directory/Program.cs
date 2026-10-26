using System.Collections.Specialized;
using System.Globalization;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

// Offline sidecar: use the admitted CLI's libraries without rebuilding or
// changing that CLI. Python owns selected VFS authentication and independently
// reads metadata/body bytes; this process owns only the bounded extraction.
class Program
{
    static int Main(string[] args)
    {
        if (args.Length != 4) { Console.Error.WriteLine("Expected CLI-directory, selection JSON, output directory, class IDs"); return 2; }
        AppDomain.CurrentDomain.AssemblyResolve += (_, e) => {
            var path = Path.Combine(args[0], new AssemblyName(e.Name).Name + ".dll");
            return File.Exists(path) ? Assembly.LoadFrom(path) : null;
        };
        try { return Run(args); }
        catch (Exception error) { Console.Error.WriteLine(error.ToString()); return 1; }
    }

    static string Hash(byte[] bytes) => Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();

    [MethodImpl(MethodImplOptions.NoInlining)]
    static int Run(string[] args)
    {
        var classes = args[3].Split(',').Select(int.Parse).ToHashSet();
        var selection = JsonDocument.Parse(File.ReadAllBytes(args[1])).RootElement.EnumerateArray().ToArray();
        if (selection.Length == 0) throw new InvalidDataException("Empty source selection");
        var output = Path.GetFullPath(args[2]); Directory.CreateDirectory(output);
        AnimeStudio.Logger.Default = new AnimeStudio.ConsoleLogger();
        AnimeStudio.Logger.Flags = AnimeStudio.LoggerEvent.Warning | AnimeStudio.LoggerEvent.Error;
        AnimeStudio.Progress.Silent = true;
        var rows = new List<object>();
        foreach (var group in selection.GroupBy(e => (Source: Path.GetFullPath(e.GetProperty("Source").GetString()), Offset: e.GetProperty("Offset").GetInt64())))
        {
            var manager = new AnimeStudio.AssetsManager { Game = AnimeStudio.GameManager.GetGame("ArknightsEndfield"), SkipProcess = true };
            manager.FilterData.Items.Add(new AnimeStudio.AssetsManager.AssetFilterDataItem { Source = group.Key.Source, Offset = group.Key.Offset, Type = AnimeStudio.ClassIDType.AssetBundle, PathID = 0, Name = "" });
            try
            {
                manager.LoadPreparedFiles(group.Key.Source);
                var names = manager.assetsFileList.Select(f => f.fileName).ToHashSet();
                if (names.Count != manager.assetsFileList.Count || group.Any(e => !names.Contains(e.GetProperty("Cab").GetString())))
                    throw new InvalidDataException($"Missing/duplicate selected CAB at {group.Key}");
                foreach (var file in manager.assetsFileList)
                {
                    if (Path.GetFullPath(file.originalPath) != group.Key.Source || file.offset != group.Key.Offset || (int)file.header.m_Version != 22)
                        throw new InvalidDataException("Unselected source span or unsupported serialized header");
                    var id = Hash(Encoding.UTF8.GetBytes(group.Key.Source.ToUpperInvariant() + "|" + file.offset.ToString(CultureInfo.InvariantCulture) + "|" + file.fileName));
                    file.reader.Position = 0;
                    var metadata = file.reader.ReadBytes(checked((int)file.header.m_MetadataSize + 48));
                    var metaName = id + ".metadata.bin"; File.WriteAllBytes(Path.Combine(output, metaName), metadata);
                    var objects = new List<object>();
                    foreach (var item in file.m_Objects.Where(o => classes.Contains(o.classID)))
                    {
                        var asset = new AnimeStudio.Object(new AnimeStudio.ObjectReader(file.reader, file, item, manager.Game));
                        var raw = asset.GetRawData(); var typed = asset.ToType();
                        if (typed == null || asset.reader.Position - asset.reader.byteStart != item.byteSize)
                            throw new InvalidDataException($"Object EOF differs: {file.fileName}/{item.m_PathID}; class {item.classID}");
                        var stem = id + "_p" + unchecked((ulong)item.m_PathID).ToString("X16");
                        File.WriteAllBytes(Path.Combine(output, stem + ".dat"), raw);
                        var json = Encoding.UTF8.GetBytes(Newtonsoft.Json.JsonConvert.SerializeObject(typed));
                        File.WriteAllBytes(Path.Combine(output, stem + ".json"), json);
                        var resource = ReadResource(typed, file, manager, output, stem);
                        objects.Add(new { pathId = item.m_PathID, classId = item.classID, byteStart = item.byteStart, byteSize = item.byteSize,
                            stem, rawSha256 = Hash(raw), jsonSha256 = Hash(json), resource });
                    }
                    rows.Add(new { source = file.originalPath, offset = file.offset, cab = file.fileName, metadata = metaName,
                        metadataSha256 = Hash(metadata), fileLength = file.reader.Length, objectCount = file.m_Objects.Count, objects,
                        externals = file.m_Externals.Select(e => e.pathName).ToArray() });
                }
            }
            finally { manager.Clear(); }
        }
        File.WriteAllText(Path.Combine(output, "directory.json"), JsonSerializer.Serialize(new { schema = "endfield.serialized-directory-extraction.v1", directories = rows }));
        return 0;
    }

    static object ReadResource(OrderedDictionary typed, AnimeStudio.SerializedFile file, AnimeStudio.AssetsManager manager, string output, string stem)
    {
        if (typed["m_StreamData"] is not OrderedDictionary stream) return null;
        var path = Convert.ToString(stream["path"], CultureInfo.InvariantCulture);
        var offset = Convert.ToInt64(stream["offset"], CultureInfo.InvariantCulture);
        var size = Convert.ToInt64(stream["size"], CultureInfo.InvariantCulture);
        if (size == 0) return new { status = "empty", path, offset, size };
        var name = file.fileName + ".resS";
        if (path != "archive:/" + file.fileName + "/" + name)
            return new { status = "outside_owner_archive", path, offset, size };
        // Refuse ResourceReader's filesystem-search fallback. Only a resource
        // stream loaded from this single selected physical Bundle participates.
        var cacheField = typeof(AnimeStudio.AssetsManager).GetField("resourceFileReaders", BindingFlags.Instance | BindingFlags.NonPublic)
            ?? throw new MissingFieldException("AssetsManager.resourceFileReaders");
        var cache = (Dictionary<string, BinaryReader>)cacheField.GetValue(manager);
        if (!cache.TryGetValue(name, out var reader)) throw new InvalidDataException("Owner archive resource stream missing: " + path);
        if (offset < 0 || size < 0 || size > int.MaxValue || offset > reader.BaseStream.Length - size)
            throw new InvalidDataException("Owner archive resource range outside stream: " + path);
        reader.BaseStream.Position = offset; var bytes = reader.ReadBytes((int)size);
        if (bytes.Length != size) throw new EndOfStreamException("Owner resource range truncated");
        var resourceName = stem + ".stream.bin"; File.WriteAllBytes(Path.Combine(output, resourceName), bytes);
        return new { status = "exact_owner_archive_span", path, offset, size, file = resourceName, sha256 = Hash(bytes), archiveStreamLength = reader.BaseStream.Length };
    }
}
