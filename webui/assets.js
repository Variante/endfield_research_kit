// Assets page behavior contract (webui/README.md links here; evidence limits
// are in memory/webui/assets.md).
//   * Search plus filter sections basic, category, type, source and sort. The
//     detail pane owns image/video/text preview with a selectable preview
//     background, an OBJ/FBX model canvas with mesh stats, material,
//     reference and related-asset lists, copy-path and download actions, and
//     ?asset= deep links. Exported JSON is not listed: every such document is
//     a Data-page store row, and a material links to its Data-page document.
//   * The Table owner fact comes from the optional data/assets/table_owners.json
//     and names the exported table row whose asset-bearing field holds this
//     asset's exact normalized stem. No such row means no owner; a shared name
//     prefix never produces one, and an absent sidecar only removes the fact.
//   * Filter chip counts are totals over grouped entries. Their tooltips and
//     the empty-list message explain why combined filters can return no rows.
//   * FBX matching with instance labels, placement, pose and bind matrices
//     excluded (`fc`),
//     or byte-identical files (`h`), shares one preview and all resource paths.
//     Pose/bind differences are selectable variants; path/name aliases share
//     each variant. Every original file has its own download.
//   * A Sprite index entry with `crop` (its texture's path) has no file and no
//     `s`; the page shows its pixel size and a Cropped from fact. Every page
//     still links to .../game/Unity/Sprite/<name>.png: serve.py answers with
//     the crop document (application/vnd.endfield.sprite-crop+json), or with
//     AnimeStudio's PNG from game/Sprite.sqlite after a debug export, and
//     sprite_worker.js renders the crop from the texture PNG so the pixels,
//     transparent ones included, equal AnimeStudio's. Without the worker (no
//     secure context) Sprite images do not display.
(() => {
  const ASSET_GROUP_ROW_H = 28;
  const ASSET_ITEM_ROW_H = 70;
  const ASSET_OVERSCAN_PX = 240;
  const DEFAULT_PREVIEW_BACKGROUND = "#0b1015";
  const DEFAULT_MODEL_COLOR = "#5c99db";
  const PREVIEW_BG_STORAGE_KEY = "asset_browser_preview_background";
  const FILTER_PANEL_STORAGE_KEY = "asset_browser_filters_collapsed";
  const UI_LOCALE_STORAGE_KEY = "webui_ui_locale";
  const MOBILE_LAYOUT_QUERY = "(max-width: 760px)";
  const AVAILABLE_VIEWS = new Set([
    "story",
    "characters",
    "gameplay",
    "audio",
    "map",
    "assets",
    "reference",
    "updates",
    "recovery",
    "data-inspector",
  ]);
  const DEBUG_ONLY_VIEWS = new Set(["recovery"]);
  const DEBUG_VIEW_FALLBACKS = Object.freeze({ recovery: "story" });
  // Facet value for files directly under the export root (empty source).
  const ROOT_SOURCE = "(root)";
  const SHARED_ASSET_NAME_PREFIXES = new Set(["S", "T", "P", "M"]);
  const MODEL_PREFIX_RE = /^([A-Z])_(.+)$/;
  const MODEL_UNPATTERNED_OBJ_GROUP = Object.freeze({
    key: "__obj_unpatterned__",
    label: "Unpatterned OBJ",
    raw: "Numeric or nonstandard OBJ names",
  });
  const MODEL_CATEGORY_LABELS = Object.freeze({
    "model-unpatterned-obj": "Unpatterned OBJ",
    "model-boss": "Model Boss",
    "model-monster": "Model Monster",
    "model-npc": "Model NPC",
    "model-character": "Model Character",
    "model-weapon": "Model Weapon",
    "model-fx": "Model FX",
    "model-factory": "Model Factory",
    "model-building": "Model Building",
    "model-environment": "Model Environment",
    "model-ui": "Model UI",
  });
  const MODEL_SEMANTIC_CATEGORY_RULES = Object.freeze([
    { category: "model-boss", tokens: ["boss"] },
    { category: "model-monster", tokens: ["monster", "enemy", "eny"] },
    { category: "model-npc", tokens: ["npc"] },
    { category: "model-character", tokens: ["actor", "char", "character"] },
    { category: "model-weapon", tokens: ["wpn", "weapon"] },
    { category: "model-fx", tokens: ["fx", "vfx", "lightning", "smoke"] },
    { category: "model-factory", tokens: ["fac", "factory", "grid", "belt", "miner", "pump", "powerpole", "electricwire"] },
    { category: "model-building", tokens: ["build", "building", "module"] },
    { category: "model-environment", tokens: ["hlod0", "hlod1", "hlod2", "hlod3", "mod", "imod", "prop", "iprop", "cprop", "tree", "bush", "rock", "grass", "water", "terrain"] },
    { category: "model-ui", tokens: ["ui"] },
  ]);
  const KNOWN_TEXTURE_SUFFIXES = new Set([
    "A", "AO", "B", "BC", "C", "D", "DA", "DIFF", "DIFFUSE", "DISP",
    "E", "EM", "EMI", "EMISSIVE", "G", "GL", "GLOSS", "H", "HM", "ID",
    "M", "MA", "MASK", "MC", "MSK", "N", "NH", "NM", "NORMAL", "NRM",
    "O", "OP", "ORM", "P", "PACK", "R", "RM", "ROUGH", "ROUGHNESS",
    "S", "SM", "SPEC", "ST", "T",
  ]);
  const {
    $,
    $$,
    applyTemplate,
    escapeHtml,
    exportFullHref,
    normalizeUiLocale,
    splitPathIdExportStem,
    relRequiresPathIdExportName,
    storageGet,
    storageSet,
  } = window.WebUI;
  const ASSET_UI_TEXTS = {
    zh: {
      showFilters: "\u663e\u793a\u7b5b\u9009",
      hideFilters: "\u9690\u85cf\u7b5b\u9009",
      title: "\u89c6\u89c9\u8d44\u4ea7",
      countLabel: "\u9879\u8d44\u6e90",
      basicFilters: "\u57fa\u7840\u7b5b\u9009",
      searchPlaceholder: "搜索路径 / 名称 / 文件夹 / 分组 / 证据",
      type: "\u7c7b\u578b",
      category: "\u5206\u7c7b",
      source: "\u6765\u6e90",
      sort: "\u6392\u5e8f",
      sortPath: "\u8def\u5f84 (A-Z)",
      sortSizeDesc: "\u6587\u4ef6\u5927\u5c0f\u4ece\u5927\u5230\u5c0f",
      sortSizeAsc: "\u6587\u4ef6\u5927\u5c0f\u4ece\u5c0f\u5230\u5927",
      sortName: "\u6587\u4ef6\u540d (A-Z)",
      reset: "\u91cd\u7f6e\u7b5b\u9009",
      filterCountHint: "\u6570\u91cf\u4e3a\u5168\u90e8\u8d44\u6e90\u6761\u76ee\u7684\u603b\u6570\u3002\u7c7b\u578b\u3001\u5206\u7c7b\u548c\u6765\u6e90\u7b5b\u9009\u9700\u540c\u65f6\u6ee1\u8db3\u3002 无可绘制面的 OBJ 默认隐藏，开启对应标签后显示。",
      noMatchingAssets: "\u6ca1\u6709\u8d44\u6e90\u7b26\u5408\u5f53\u524d\u641c\u7d22\u548c\u7b5b\u9009\u3002\u6807\u7b7e\u6570\u91cf\u4e3a\u5168\u90e8\u8d44\u6e90\u6761\u76ee\u7684\u603b\u6570\u3002\u8bf7\u6e05\u7a7a\u641c\u7d22\u6216\u91cd\u7f6e\u7b5b\u9009\u3002 查看无可绘制面的模型需开启对应标签。",
      listUnit: "\u6761\u76ee",
      empty: "\u4ece\u5de6\u4fa7\u9009\u62e9\u4e00\u4e2a\u5bfc\u51fa\u8d44\u6e90\u3002",
      openRawFile: "\u6253\u5f00\u539f\u59cb\u6587\u4ef6",
      downloadCurrentFile: "\u4e0b\u8f7d\u5f53\u524d\u6587\u4ef6",
      copyRelativePath: "\u590d\u5236\u76f8\u5bf9\u8def\u5f84",
      copiedPath: "\u5df2\u590d\u5236\u8def\u5f84",
      copyFailed: "\u590d\u5236\u5931\u8d25",
      preview: "\u9884\u89c8",
      previewBackground: "\u80cc\u666f",
      modelColor: "模型颜色",
      modelOnly: "仅显示模型",
      modelLodBest: "各部件最高细节",
      modelRecovery: "导出完整性",
      modelRecoveryGap: "已导出 {exported}/{expected} 个源网格实例。部分引用的网格数据尚未找到。",
      modelEmission: "显示发光",
      modelEmissionHelp: "开启材质发光；强光可能遮住表面细节。关闭可查看原有贴图和形状。",
      previewBackgroundCustom: "\u81ea\u5b9a\u4e49\u80cc\u666f\u8272",
      previewBackgroundPreset: "\u80cc\u666f\u8272 {color}",
      previewPlaceholder: "\u9884\u89c8\u4f1a\u663e\u793a\u5728\u8fd9\u91cc\u3002",
      inspector: "\u8d44\u6e90\u68c0\u67e5\u5668",
      relatedFiles: "\u76f8\u5173\u6587\u4ef6",
      lodVariants: "\u53d8\u4f53",
      linkedMaterials: "\u5173\u8054\u6750\u8d28",
      linkedTextures: "\u5173\u8054\u8d34\u56fe",
      referencedBy: "\u5f15\u7528\u6b64\u8d44\u6e90\u7684\u6587\u4ef6",
      modelStats: "\u6a21\u578b\u7edf\u8ba1",
      images: "\u56fe\u7247",
      models: "\u6a21\u578b",
      videos: "\u89c6\u9891",
      rootFolder: "(\u6839\u76ee\u5f55)",
      none: "(\u65e0)",
      unresolved: "\u672a\u89e3\u6790",
      variantsCount: "{count} \u4e2a\u53d8\u4f53",
      copiesCount: "{count} \u4e2a\u526f\u672c",
      assetIndexError: "\u65e0\u6cd5\u52a0\u8f7d\u8d44\u6e90\u7d22\u5f15: {error}",
      relatedMeta: "{kind} / {size}",
      factKind: "\u7c7b\u578b",
      factSource: "\u6765\u6e90",
      factFolder: "\u5206\u7ec4",
      factAssetPath: "\u8d44\u6e90\u8def\u5f84",
      factAssetPaths: "\u8d44\u6e90\u8def\u5f84",
      factResourceFiles: "\u8d44\u6e90\u6587\u4ef6",
      factVariantDifferences: "变体差异",
      fbxPoseDifferences: "包含位置、姿态或蒙皮绑定差异。",
      modelObjects: "\u5bf9\u8c61\uff08{count}\uff09",
      modelLod: "LOD {lod}",
      modelLodShared: "\u6240\u6709 LOD",
      modelObjectVfx: "\u7279\u6548",
      modelObjectShadow: "\u9634\u5f71",
      factSize: "\u5927\u5c0f",
      factCropOf: "\u88c1\u5207\u81ea",
      factCopies: "\u526f\u672c",
      factHash: "\u54c8\u5e0c",
      factSameHashFiles: "\u76f8\u540c\u54c8\u5e0c\u6587\u4ef6",
      factLodVariants: "\u53d8\u4f53",
      factSelectedRawFile: "\u5f53\u524d\u539f\u59cb\u6587\u4ef6",
      factLodSet: "\u7ec4\u5185\u6587\u4ef6",
      factRelativePath: "\u76f8\u5bf9\u8def\u5f84",
      factImageCategory: "\u56fe\u7247\u5206\u7c7b",
      factModelTags: "\u6a21\u578b\u6807\u7b7e",
      factTextureRole: "\u8d34\u56fe\u89d2\u8272",
      factLod: "LOD",
      factFamily: "\u7cfb\u5217",
      factTableOwner: "\u8868\u5f52\u5c5e",
      factPreviewProxy: "\u5ba1\u9605\u4ee3\u7406",
      categoryOther: "\u5176\u4ed6",
      textureRoleMaterial: "\u6750\u8d28 / \u5f15\u64ce\u8d34\u56fe",
      textureRoleRegular: "\u5e38\u89c4\u56fe\u7247",
      materialJson: "{name}.json",
      openInDataPage: "\u5728\u6570\u636e\u9875\u6253\u5f00",
      relationTextureResolved: "{slots} / {name}",
      relationTextureUnresolved: "{slots} / {name} / \u672a\u89e3\u6790",
      relationMaterial: "\u6750\u8d28 / {slots}",
      relationModel: "\u6a21\u578b",
      loadingImagePreview: "\u6b63\u5728\u52a0\u8f7d\u56fe\u7247\u9884\u89c8...",
      imagePreviewUnavailable: "\u65e0\u6cd5\u9884\u89c8\u8fd9\u5f20\u56fe\u7247\u3002",
      rawLinkAvailable: "\u4e0a\u65b9\u4ecd\u53ef\u6253\u5f00\u539f\u59cb\u6587\u4ef6\u3002",
      imagePixels: "{width} x {height} \u50cf\u7d20",
      loadingVideoPreview: "\u6b63\u5728\u52a0\u8f7d\u89c6\u9891\u9884\u89c8...",
      videoPreviewUnavailable: "\u65e0\u6cd5\u9884\u89c8\u8fd9\u4e2a\u89c6\u9891\u3002",
      videoDuration: "\u65f6\u957f {duration}",
      filePreviewUnavailable: "\u6b64\u6587\u4ef6\u6ca1\u6709\u53ef\u7528\u7684\u9875\u5185\u9884\u89c8\u3002",
      loadingObjPreview: "\u6b63\u5728\u52a0\u8f7d OBJ \u9884\u89c8...",
      loadingFbxSummary: "\u6b63\u5728\u8bfb\u53d6 FBX \u7ed3\u6784...",
      noModelFile: "\u6ca1\u6709\u53ef\u7528\u7684\u6a21\u578b\u6587\u4ef6\u3002",
      previewingModel: "\u6b63\u5728\u9884\u89c8 {name}\u3002\u5de6\u952e\u62d6\u52a8\u65cb\u8f6c\uff0c\u53f3\u952e\u6216 Shift \u62d6\u52a8\u5e73\u79fb\uff0c\u6eda\u8f6e\u7f29\u653e\uff0c\u53cc\u51fb\u590d\u4f4d\u3002",
      previewingModelViaObj: "\u6b63\u5728\u901a\u8fc7\u914d\u5957 OBJ \u5ba1\u9605 {name}\u3002\u5de6\u952e\u62d6\u52a8\u65cb\u8f6c\uff0c\u53f3\u952e\u6216 Shift \u62d6\u52a8\u5e73\u79fb\uff0c\u6eda\u8f6e\u7f29\u653e\uff0c\u53cc\u51fb\u590d\u4f4d\u3002",
      emptyModelTag: "空网格 / 无可绘制面",
      collisionTag: "碰撞网格",
      collisionHint: "显示从已验证的烘焙数据恢复的碰撞网格。",
      collisionPreviewHint: "碰撞几何 · 网格局部坐标；运行时证据见详情，预览未应用场景变换。",
      collisionEvidence: "碰撞证据",
      collisionDecoded: "已解码存储几何",
      collisionQueryObserved: "查询中已观察到此几何 · {count} 次结果",
      collisionNotObserved: "暂无已验证的运行时观察；不代表游戏未使用",
      collisionMovement: "已唯一匹配移动查询返回结果 · {count} 次（可行走地面 {floor} 次）",
      collisionFilter: "已接受的过滤候选 · {count} 次；不代表最终移动结果",
      collisionArrays: "运行时顶点/索引数组",
      collisionArraysComplete: "完整数组与存储数据一致 · {count} 次",
      collisionArraysPrefix: "仅已捕获前缀一致 · {count} 次；未捕获尾部未知",
      collisionSurface: "有条件的表面比较 · {count} 次；位姿分别采样",
      collisionExcludedPoints: "初始重叠或非正距离扫掠 · {count} 次；未用作表面点",
      collisionSolver: "求解器接触参与尚未证明",
      collisionAuthoredOwners: "存储的预制体归属",
      collisionAuthoredHierarchy: "存储的碰撞体层级",
      collisionAuthoredFlags: "存储设置：启用 {enabled}；整个层级激活 {active}",
      collisionAuthoredYes: "是",
      collisionAuthoredNo: "否",
      collisionAuthoredBoundary: "以上为存储配置；运行时实例、激活状态和世界位置尚未证明。",
      collisionAuthoredUnavailable: "存储归属证据不可用：{reason}",
      collisionModelSources: "定义此预制体的 Model 源记录",
      collisionModelRecord: "网格 ID {grid} · Model 序号 {ordinal}",
      collisionModelPosition: "存储位置",
      collisionModelRotation: "存储旋转轴值",
      collisionModelScale: "存储缩放",
      collisionModelBoundary: "这些是定义数据；网格变换、运行时父级和最终世界位置尚未证明。预览未应用这些数值。",
      collisionModelUnavailable: "Model 源证据不可用：{reason}",
      collisionPrefabAssemblies: "存储的碰撞组合",
      collisionPrefabPreview: "预览组合",
      collisionPrefabReset: "恢复单个网格",
      collisionPrefabDownload: "下载组合 OBJ",
      collisionPrefabSummary: "已选碰撞体 {count} 个（网格 {meshes} · 盒 {boxes}）· 存储禁用 {disabled} 个 · 层级未激活 {inactive} 个 · 已选未恢复 {missing} 个",
      collisionPrefabBoundary: "组合已选 MeshCollider 及单独验证的 BoxCollider，包含存储禁用项；应用根节点及子节点的存储变换。盒形按存储中心及完整尺寸绘制。不含其他基本形状或自定义碰撞体，不表示运行时物理形状、激活或世界位置。",
      collisionBoxPart: "存储的盒形 · 大小 [{size}] · 中心 [{center}] · 触发器 {trigger}",
      collisionBoxUnavailable: "存储盒形证据不可用：{reason}",
      collisionRenderers: "同一预制体的存储渲染组件",
      collisionRendererSummary: "MeshRenderer {count} 个 · 已验证网格对象引用 {meshes} 个 · 材质槽 {slots} 个",
      collisionRendererRecord: "{hierarchy} · 材质槽 {slots} 个 · 存储启用 {enabled}",
      collisionRendererMesh: "网格引用",
      collisionRendererSlot: "材质槽 {slot}",
      collisionRendererPointer: "文件槽 {file} · PathID {path}",
      collisionRendererExact: "已验证选中目标的存储身份",
      collisionRendererUnwitnessed: "外部文件槽尚未验证",
      collisionRendererExternal: "外部 CAB 已验证，目标对象未选入",
      collisionRendererExcluded: "目标对象未选入",
      collisionRendererAmbiguous: "外部目标物理来源不唯一",
      collisionRendererNoFilter: "MeshFilter 未恢复",
      collisionRendererNull: "空引用",
      collisionRendererBoundary: "组件通过实际预制体根节点、GameObject 回链及存储层级关联。材质槽保留顺序；未恢复的资源引用明确标注。组件链接本身证明存储归属与引用，不证明运行时绘制，也不覆盖其他 Renderer 类型。",
      collisionRendererUnavailable: "存储渲染组件证据不可用：{reason}",
      collisionRenderPreview: "预览存储渲染网格",
      collisionRenderLOD: "预览存储 LOD {lod}",
      collisionRenderUngrouped: "预览未分组的存储渲染组件",
      collisionRenderDownload: "下载渲染 OBJ",
      collisionRenderMaterial: "材质存储字段 JSON",
      collisionShaderDetails: "存储 Shader 分析",
      collisionShaderUnavailable: "未找到与此材质文件匹配的 Shader 分析。",
      collisionShaderKeywords: "存储有效关键字：{keywords}",
      collisionShaderInvalid: "存储无效关键字：{keywords}",
      collisionShaderPasses: "存储 Pass：{passes}",
      collisionShaderCandidates: "条件候选 {count} / {total} 个编译程序记录（允许额外引擎关键字）",
      collisionShaderUnknown: "Shader 未声明的有效关键字：{keywords}",
      collisionShaderBoundary: "候选来自存储关键字与编译记录；运行时程序选择、Pass 执行和资源绑定尚未证明。预览仍使用中性色。",
      collisionShaderDownload: "下载 Shader 分析 JSON",
      collisionShaderParameters: "材质值与条件参数布局",
      collisionShaderStoredValues: "材质显式存储值",
      collisionShaderDefaults: "未被显式数值覆盖的 Shader 声明（{count} 个；完整字段见 JSON）",
      collisionShaderParameterPass: "{pass} · LOD {lod} · {count} 个条件程序记录",
      collisionShaderResource: "参数表资源名：{name} · 出现于 {count}/{total} 个记录",
      collisionShaderField: "{buffer}.{name} · 出现于 {count}/{total} 个记录 · 字节偏移 {offsets}",
      collisionShaderInstructions: "编译指令的静态引用（条件候选）",
      collisionShaderInstructionPass: "{pass} · LOD {lod} · {stage} · {count} 个候选程序",
      collisionShaderInstructionStatus: "寄存器关联完整 {complete}/{total}；含动态索引 {dynamic}；含匿名字节读取 {anonymous}。",
      collisionShaderInstructionResource: "{kind} · {name} · {count}/{total} 个程序引用",
      collisionShaderInstructionField: "{buffer}.{name} · {count}/{total} 个程序引用 · 字节偏移 {offsets}",
      collisionShaderInstructionBoundary: "这是保守的编译指令静态引用；已支持的指令形式按分量掩码读取，其他形式保留可能引用，不代表游戏选中或执行了该程序。动态索引和匿名偏移保留为缺口；GPU 常量、纹理视图、采样器及最终光照仍需同一绘制的运行时证据。",
      collisionTextureInspect: "在此材质槽上检查贴图",
      collisionTextureChannel: "检查贴图通道",
      collisionTextureInspectNote: "存储贴图检查：{property} · 材质槽 {slot} · UV{uv} 缩放/偏移 · {channel}。仅显示解码最高 mip；其他槽保持中性色。未应用游戏材质运算、颜色转换或运行时采样。",
      collisionRenderTextures: "存储贴图 · {count} 个非空引用",
      collisionRenderTextureUnavailable: "解码图像不可用；存储引用与字段仍保留。",
      collisionRenderTextureUV: "UV 集 {uv} · 缩放 [{scale}] · 偏移 [{offset}]",
      collisionRenderTextureInfo: "{width}×{height} · {format} · {mips} 层 mip · 存储色彩空间枚举 {space}",
      collisionRenderTextureBoundary: "贴图预览保留解码通道并按导出图像坐标上下翻转；未做色彩转换、法线重建或材质着色，不表示运行时采样结果。",
      collisionRenderBoundary: "存储的渲染几何及 LOD 成员关系，预览使用中性色。组合应用根节点和子节点的存储变换；未恢复材质外观、额外顶点流、动画、运行时 LOD 选择或世界位置。",
      collisionRenderMissing: "渲染组件 {count} 个 · 已选未恢复 {missing} 个",
      collisionRenderDirectoryMissing: "外部文件槽已验证，目标目录未选入",
      collisionRenderAbsent: "完整选中目录中无此对象",
      collisionRenderBodyUnselected: "目标身份已验证，对象内容未选入",
      collisionRenderMembership: "存储 LOD {lod} · 屏幕比例阈值 {height}",
      collisionPrefabUnavailable: "碰撞组合不可用：{reason}",
      collisionRuntimeUnavailable: "运行时证据不可用：{reason}",
      collisionBuffer: "烘焙碰撞数据 SHA-256",
      collisionIdentity: "Unity 对象标识",
      collisionTriangle: "三角形碰撞网格",
      collisionConvex: "凸碰撞包络",
      collisionUnavailable: "碰撞预览不可用：{reason}",
      emptyModelHint: "显示无可绘制面的 OBJ，保留原始标识和下载链接。",
      geometry: "几何",
      objPreviewUnavailable: "\u65e0\u6cd5\u9884\u89c8\u6b64 OBJ \u6587\u4ef6\u3002",
      fbxSummaryLoaded: "\u8fd9\u4e2a FBX \u6ca1\u6709\u53ef\u9884\u89c8\u7684\u7f51\u683c\uff0c\u4e0b\u65b9\u5c55\u793a\u6587\u4ef6\u7ed3\u6784\u6458\u8981\u3002",
      fbxSummaryUnavailable: "\u65e0\u6cd5\u8bfb\u53d6\u8fd9\u4e2a FBX \u6587\u4ef6\u7684\u7ed3\u6784\u6458\u8981\u3002",
      fbxSummaryPlaceholder: "FBX \u7ed3\u6784\u6458\u8981\u4f1a\u663e\u793a\u5728\u4e0b\u65b9\u7684\u7edf\u8ba1\u9762\u677f\u91cc\u3002",
      selectedLod: "\u5f53\u524d LOD",
      triangles: "\u4e09\u89d2\u5f62",
      vertices: "\u9876\u70b9",
      faces: "\u9762",
      objectsGroups: "\u5bf9\u8c61 / \u7ec4",
      fbxFormat: "FBX \u683c\u5f0f",
      fbxVersion: "FBX \u7248\u672c",
      fbxNodes: "\u8282\u70b9",
      fbxModels: "\u6a21\u578b\u8282\u70b9",
      fbxGeometries: "\u7f51\u683c\u8282\u70b9",
      fbxMaterials: "\u6750\u8d28\u8282\u70b9",
      fbxTextures: "\u8d34\u56fe\u8282\u70b9",
      fbxAnimations: "\u52a8\u753b\u6811",
      fbxSampleNames: "\u793a\u4f8b\u540d\u79f0",
    },
    en: {
      showFilters: "Show filters",
      hideFilters: "Hide filters",
      title: "Exported Assets",
      countLabel: "assets",
      basicFilters: "Basic filters",
      searchPlaceholder: "Search path / name / folder / group / evidence",
      type: "Type",
      category: "Category",
      source: "Source",
      sort: "Sort",
      sortPath: "Path (A-Z)",
      sortSizeDesc: "File size (high to low)",
      sortSizeAsc: "File size (low to high)",
      sortName: "File name (A-Z)",
      reset: "Reset filters",
      filterCountHint: "Counts are totals across all asset entries. Type, category and source filters must all match. OBJ files without drawable faces stay hidden until their tag is enabled.",
      noMatchingAssets: "No assets match the current search and filters. Tag counts show totals across all asset entries. Clear the search or reset filters. To include models without drawable faces, enable their tag.",
      listUnit: "items",
      empty: "Choose an exported asset from the left.",
      openRawFile: "Open raw file",
      downloadCurrentFile: "Download current file",
      copyRelativePath: "Copy relative path",
      copiedPath: "Copied path",
      copyFailed: "Copy failed",
      preview: "Preview",
      previewBackground: "Background",
      modelColor: "Model color",
      modelOnly: "Model only",
      modelLodBest: "Best per part",
      modelRecovery: "Export completeness",
      modelRecoveryGap: "{exported}/{expected} source mesh instances exported. Some referenced mesh data has not been located.",
      modelEmission: "Show emission",
      modelEmissionHelp: "Enable material emission. Bright glow can obscure surface details; turn it off to inspect the base texture and shape.",
      previewBackgroundCustom: "Custom background color",
      previewBackgroundPreset: "Background {color}",
      previewPlaceholder: "Preview will appear here.",
      inspector: "Inspector",
      relatedFiles: "Related files",
      lodVariants: "Variants",
      linkedMaterials: "Linked materials",
      linkedTextures: "Linked textures",
      referencedBy: "Referenced by",
      modelStats: "Model stats",
      images: "Images",
      models: "Models",
      videos: "Videos",
      rootFolder: "(root)",
      none: "(none)",
      unresolved: "unresolved",
      variantsCount: "{count} variants",
      copiesCount: "{count} copies",
      assetIndexError: "Unable to load asset index: {error}",
      relatedMeta: "{kind} / {size}",
      factKind: "Kind",
      factSource: "Source",
      factFolder: "Group",
      factAssetPath: "Asset path",
      factAssetPaths: "Resource paths",
      factResourceFiles: "Resource files",
      factVariantDifferences: "Variant differences",
      fbxPoseDifferences: "Includes differences in placement, pose or skin binding.",
      modelObjects: "Objects ({count})",
      modelLod: "LOD {lod}",
      modelLodShared: "All LODs",
      modelObjectVfx: "VFX",
      modelObjectShadow: "Shadow",
      factSize: "Size",
      factCropOf: "Cropped from",
      factCopies: "Copies",
      factHash: "Hash",
      factSameHashFiles: "Same-hash files",
      factLodVariants: "Variants",
      factSelectedRawFile: "Selected raw file",
      factLodSet: "Files in group",
      factRelativePath: "Relative path",
      factImageCategory: "Image category",
      factModelTags: "Model tags",
      factTextureRole: "Texture role",
      factLod: "LOD",
      factFamily: "Family",
      factTableOwner: "Table owner",
      factPreviewProxy: "Review proxy",
      categoryOther: "Other",
      textureRoleMaterial: "Material / engine texture",
      textureRoleRegular: "Regular image",
      materialJson: "{name}.json",
      openInDataPage: "Open in Data",
      relationTextureResolved: "{slots} / {name}",
      relationTextureUnresolved: "{slots} / {name} / unresolved",
      relationMaterial: "Material / {slots}",
      relationModel: "Model",
      loadingImagePreview: "Loading image preview...",
      imagePreviewUnavailable: "Unable to preview this image.",
      rawLinkAvailable: "The raw file link is still available above.",
      imagePixels: "{width} x {height} pixels",
      loadingVideoPreview: "Loading video preview...",
      videoPreviewUnavailable: "Unable to preview this video.",
      videoDuration: "Duration {duration}",
      filePreviewUnavailable: "No in-page preview is available for this file.",
      loadingObjPreview: "Loading OBJ preview...",
      loadingFbxSummary: "Reading FBX structure...",
      noModelFile: "No model file is available.",
      previewingModel: "Previewing {name}. Drag to rotate, right-drag or Shift-drag to pan, scroll to zoom, double-click to reset.",
      previewingModelViaObj: "Reviewing {name} through a paired OBJ preview. Drag to rotate, right-drag or Shift-drag to pan, scroll to zoom, double-click to reset.",
      emptyModelTag: "Empty mesh / no drawable faces",
      collisionTag: "Collision",
      collisionHint: "Include collision meshes recovered from validated cooked data.",
      collisionPreviewHint: "Collision geometry in mesh local coordinates. Runtime evidence is in the details; no scene transform is applied to this preview.",
      collisionEvidence: "Collision evidence",
      collisionDecoded: "Decoded stored geometry",
      collisionQueryObserved: "Observed query geometry · {count} results",
      collisionNotObserved: "No validated runtime observation; this does not mean unused",
      collisionMovement: "Uniquely matched movement query returns · {count} (walkable floor: {floor})",
      collisionFilter: "Accepted filter candidates · {count}; these do not prove final movement results",
      collisionArrays: "Runtime vertex/index arrays",
      collisionArraysComplete: "Samples with complete arrays matching stored data: {count}",
      collisionArraysPrefix: "Samples with matching captured prefixes: {count}; uncaptured tails remain unknown",
      collisionSurface: "Conditional surface comparisons · {count}; poses sampled separately",
      collisionExcludedPoints: "Initial-overlap/nonpositive-distance sweeps · {count}; excluded as surface points",
      collisionSolver: "Solver-contact participation unproved",
      collisionAuthoredOwners: "Stored prefab owners",
      collisionAuthoredHierarchy: "Stored collider hierarchies",
      collisionAuthoredFlags: "Stored settings: enabled {enabled}; whole hierarchy active {active}",
      collisionAuthoredYes: "Yes",
      collisionAuthoredNo: "No",
      collisionAuthoredBoundary: "Stored configuration; live instances, activation and world placement remain unproved.",
      collisionAuthoredUnavailable: "Stored owner evidence unavailable: {reason}",
      collisionModelSources: "Model source records defining this prefab",
      collisionModelRecord: "Grid ID {grid} · Model ordinal {ordinal}",
      collisionModelPosition: "Stored position",
      collisionModelRotation: "Stored rotation axes",
      collisionModelScale: "Stored scale",
      collisionModelBoundary: "Definition data; grid transforms, runtime parents and final world placement remain unproved. The preview does not apply these values.",
      collisionModelUnavailable: "Model source evidence unavailable: {reason}",
      collisionPrefabAssemblies: "Stored collision assemblies",
      collisionPrefabPreview: "Preview assembly",
      collisionPrefabReset: "Restore single mesh",
      collisionPrefabDownload: "Download assembly OBJ",
      collisionPrefabSummary: "Selected colliders: {count} (mesh {meshes} · box {boxes}) · stored disabled: {disabled} · inactive hierarchy: {inactive} · selected unrecovered: {missing}",
      collisionPrefabBoundary: "Selected MeshColliders and separately admitted BoxColliders, including stored disabled definitions; applies root and descendant stored transforms. Boxes use stored center and full size. Other primitive/custom colliders, effective runtime shapes, activation and world placement are not reconstructed.",
      collisionBoxPart: "Stored box · size [{size}] · center [{center}] · trigger {trigger}",
      collisionBoxUnavailable: "Stored box evidence unavailable: {reason}",
      collisionRenderers: "Stored render components in the same prefab",
      collisionRendererSummary: "MeshRenderers: {count} · verified Mesh object references: {meshes} · material slots: {slots}",
      collisionRendererRecord: "{hierarchy} · material slots: {slots} · stored enabled: {enabled}",
      collisionRendererMesh: "Mesh reference",
      collisionRendererSlot: "Material slot {slot}",
      collisionRendererPointer: "File slot {file} · PathID {path}",
      collisionRendererExact: "Verified selected target identity",
      collisionRendererUnwitnessed: "External file slot unverified",
      collisionRendererExternal: "External CAB witnessed; target outside selection",
      collisionRendererExcluded: "Target outside selection",
      collisionRendererAmbiguous: "External physical target ambiguous",
      collisionRendererNoFilter: "MeshFilter unavailable",
      collisionRendererNull: "Null reference",
      collisionRendererBoundary: "Links use the actual prefab root, reciprocal GameObject components and stored hierarchy. Material slot order is retained; unresolved resources are labelled. Component links establish stored ownership and references; runtime drawing and other Renderer classes remain outside this scope.",
      collisionRendererUnavailable: "Stored render component evidence unavailable: {reason}",
      collisionRenderPreview: "Preview stored render mesh",
      collisionRenderLOD: "Preview stored LOD {lod}",
      collisionRenderUngrouped: "Preview ungrouped stored renderers",
      collisionRenderDownload: "Download render OBJ",
      collisionRenderMaterial: "Stored material fields JSON",
      collisionShaderDetails: "Stored Shader analysis",
      collisionShaderUnavailable: "No matching Shader analysis for this Material artifact.",
      collisionShaderKeywords: "Stored valid keywords: {keywords}",
      collisionShaderInvalid: "Stored invalid keywords: {keywords}",
      collisionShaderPasses: "Stored passes: {passes}",
      collisionShaderCandidates: "Conditional candidates: {count} / {total} compiled program records (additional engine keywords allowed)",
      collisionShaderUnknown: "Valid keywords undeclared by this Shader: {keywords}",
      collisionShaderBoundary: "Candidates join stored keywords to compiled records; runtime program selection, pass execution and resource binding remain unproved. The preview keeps its neutral tint.",
      collisionShaderDownload: "Download Shader analysis JSON",
      collisionShaderParameters: "Material values and conditional parameter layouts",
      collisionShaderStoredValues: "Explicit stored material values",
      collisionShaderDefaults: "Shader declarations without explicit numeric overrides ({count}; full fields in JSON)",
      collisionShaderParameterPass: "{pass} · LOD {lod} · {count} conditional program records",
      collisionShaderResource: "Parameter-table resource name: {name} · present in {count}/{total} records",
      collisionShaderField: "{buffer}.{name} · present in {count}/{total} records · byte offsets {offsets}",
      collisionShaderInstructions: "Static compiled instruction references (conditional candidates)",
      collisionShaderInstructionPass: "{pass} · LOD {lod} · {stage} · {count} candidate programs",
      collisionShaderInstructionStatus: "Complete register joins {complete}/{total}; programs with dynamic indices {dynamic}; anonymous byte reads {anonymous}.",
      collisionShaderInstructionResource: "{kind} · {name} · referenced by {count}/{total} programs",
      collisionShaderInstructionField: "{buffer}.{name} · referenced by {count}/{total} programs · byte offsets {offsets}",
      collisionShaderInstructionBoundary: "These are conservative static instruction references. Supported operand forms use component masks; other forms retain possible references. They do not prove game selection or execution. Dynamic indices and anonymous offsets remain explicit; GPU constants, texture views, samplers and final lighting require runtime evidence from the same draw.",
      collisionTextureInspect: "Inspect texture on this material slot",
      collisionTextureChannel: "Texture inspection channel",
      collisionTextureInspectNote: "Stored texture inspection: {property} · material slot {slot} · UV{uv} scale/offset · {channel}. Decoded top mip only; other slots keep a neutral tint. Game material arithmetic, colour conversion and runtime sampling are not applied.",
      collisionRenderTextures: "Stored textures · {count} non-null references",
      collisionRenderTextureUnavailable: "Decoded image unavailable; stored references and fields are retained.",
      collisionRenderTextureUV: "UV set {uv} · scale [{scale}] · offset [{offset}]",
      collisionRenderTextureInfo: "{width}×{height} · {format} · mip count {mips} · stored colour-space enum {space}",
      collisionRenderTextureBoundary: "Texture previews retain decoded channels and flip vertically for exported image coordinates; no colour conversion, normal reconstruction or material shading, and no runtime sampling claim.",
      collisionRenderBoundary: "Stored render geometry and LOD membership, previewed with a neutral tint. Assemblies apply root and descendant stored transforms; material appearance, additional vertex streams, animation, runtime LOD selection and world placement are not reconstructed.",
      collisionRenderMissing: "Renderers: {count} · selected unrecovered: {missing}",
      collisionRenderDirectoryMissing: "External slot verified; target directory outside selection",
      collisionRenderAbsent: "Target absent from complete selected directory",
      collisionRenderBodyUnselected: "Target identity verified; body outside selection",
      collisionRenderMembership: "Stored LOD {lod} · screen-relative threshold {height}",
      collisionPrefabUnavailable: "Collision assembly unavailable: {reason}",
      collisionRuntimeUnavailable: "Runtime evidence unavailable: {reason}",
      collisionBuffer: "Cooked collision SHA-256",
      collisionIdentity: "Unity object identity",
      collisionTriangle: "Triangle collision mesh",
      collisionConvex: "Convex collision hull",
      collisionUnavailable: "Collision previews unavailable: {reason}",
      emptyModelHint: "Include OBJ files with no drawable faces. These files retain their original identity and download link.",
      geometry: "Geometry",
      objPreviewUnavailable: "Unable to preview this OBJ file.",
      fbxSummaryLoaded: "This FBX has no previewable mesh, so the panel below shows its structure summary.",
      fbxSummaryUnavailable: "Unable to read a structure summary for this FBX file.",
      fbxSummaryPlaceholder: "The FBX structure summary appears in the stats panel below.",
      selectedLod: "Selected LOD",
      triangles: "Triangles",
      vertices: "Vertices",
      faces: "Faces",
      objectsGroups: "Objects / groups",
      fbxFormat: "FBX format",
      fbxVersion: "FBX version",
      fbxNodes: "Nodes",
      fbxModels: "Model nodes",
      fbxGeometries: "Geometry nodes",
      fbxMaterials: "Material nodes",
      fbxTextures: "Texture nodes",
      fbxAnimations: "Animation stacks",
      fbxSampleNames: "Sample names",
    },
  };

  const ASSET_STATE = {
    activeView: "story",
    uiLocale: "zh",
    loaded: false,
    loadPromise: null,
    entries: [],
    entryByRel: new Map(),
    rawEntryByRel: new Map(),
    filtered: [],
    rows: [],
    totalH: 0,
    expanded: new Set(),
    relations: {},
    // data/assets/table_owners.json: normalized asset stem -> exact exported
    // table rows whose asset-bearing field holds that stem. Absent stems are
    // unowned; nothing here is a name-prefix guess.
    tableOwners: {},
    exportRoot: "",
    sourceRoots: {},
    collisionStatus: null,
    selectedRel: null,
    selectedEntry: null,
    selectedVariantRel: null,
    initialAssetHandled: false,
    previewBackground: DEFAULT_PREVIEW_BACKGROUND,
    modelColor: DEFAULT_MODEL_COLOR,
    modelOnly: false,
    // Base textures expose the shape by default. Stored HDR emission can
    // saturate the LDR canvas and look like missing horns or other details.
    // Keep the authored values available through a separate display control.
    modelEmission: false,
    qTimer: null,
    detailToken: 0,
    imageObjectUrl: "",
    filters: createDefaultFilters(),
    facets: createAssetFacets(),
    modelCache: new Map(),
    fbxSummaryCache: new Map(),
    viewer: {
      rotationX: -0.35,
      rotationY: 0.75,
      zoom: 1,
      panX: 0,
      panY: 0,
      dragging: false,
      dragMode: "",
      lastX: 0,
      lastY: 0,
      renderQueued: false,
      model: null,
      canvas: null,
      ctx: null,
      gl: null,
      bound: false,
    },
  };

  function stripAssetLodSuffix(value) {
    return String(value || "").replace(/(?:[_-])lod\d+$/i, "");
  }

  function exportedAssetStemInfo(rel, name) {
    const rawStem = String(name || "").replace(/\.[^.]+$/i, "");
    const split = splitPathIdExportStem(rawStem);
    if (relRequiresPathIdExportName(rel)) {
      return split ? { stem: split.base, rawStem, pathId: split.pathId } : null;
    }
    return {
      stem: split ? split.base : rawStem,
      rawStem,
      pathId: split ? split.pathId : "",
    };
  }

  function assetGroupStem(kind, stem) {
    return kind === "model" ? stripAssetLodSuffix(stem) : String(stem || "");
  }

  function stripSharedAssetPrefix(value = "") {
    const normalized = String(value || "").trim();
    const match = normalized.match(/^([A-Za-z])[_-](.+)$/);
    if (!match) return normalized;
    if (!SHARED_ASSET_NAME_PREFIXES.has(String(match[1] || "").toUpperCase())) return normalized;
    return String(match[2] || "").trim();
  }

  function inferTextureVariantStem(stem = "", ext = "") {
    if (String(ext || "").toLowerCase() !== "png") return null;
    const match = String(stem || "").match(/^(.*?)(?:[_-])([A-Za-z]{1,10})$/);
    if (!match) return null;
    const parentStem = String(match[1] || "").trim();
    const suffixLabel = String(match[2] || "").toUpperCase();
    if (!parentStem || !suffixLabel || !/^[A-Z]{1,10}$/.test(suffixLabel)) return null;

    const looksLikeTexture = /^t[_-]/i.test(stem) || /^tex(?:ture)?[_-]/i.test(stem);
    if (!KNOWN_TEXTURE_SUFFIXES.has(suffixLabel) && !looksLikeTexture) return null;

    return { parentStem, suffixLabel };
  }

  function inferGroupedFamily(entry) {
    if (!entry) return null;
    if (entry.kind === "image") return inferTextureVariantStem(entry.stem, entry.ext);

    const match = String(entry.stem || "").match(/^(.*?)(?:[_-])([^-_]+)$/);
    if (!match) return null;
    const parentStem = String(match[1] || "").trim();
    const suffixLabel = String(match[2] || "").trim();
    if (!parentStem || !suffixLabel) return null;
    // Weapon stems end in an item id (wpn_misc_0004 vs wpn_misc_0011 are
    // different weapons), not a variant of one family. Other numbered
    // chunks (HLOD clusters, water planes) still group.
    if (/^\d{4,}$/.test(suffixLabel) && /(?:^|[_-])wpn(?:[_-]|$)/i.test(parentStem)) return null;
    return { parentStem, suffixLabel };
  }

  function createDefaultFilters() {
    return { q: "", sort: "path", showEmptyModels: false, showCollision: false };
  }

  // The exported files an asset row stands for. Update badges match these
  // against the comparison feed; walking the whole row (search text, labels)
  // finds nothing more and dominated the facet render.
  function assetFilePaths(entry) {
    const own = (row) => [row.rel, row.rawRels, row.previewRel, row.cropOf];
    return [own(entry), (entry.variants || []).map(own)];
  }

  // Type/category/source chips. Counts are totals over every asset (not
  // narrowed by search); the score-ranked search stays in applyAssetFilters.
  function createAssetFacets() {
    return window.WebUI.facets.create({
      countMode: "total",
      chipClassName: "asset-filter-chip",
      groups: [
        window.WebUI.updateBadges.filterGroup("asset", (entry) => window.WebUI.updateBadges.fileStatus(assetFilePaths(entry))),
        { id: "type", container: "#asset-type-filter", section: "asset-type", order: "count",
          values: (entry) => entry.ext || entry.kind, label: assetTypeLabel,
          title: (value) => `${assetTypeLabel(value)}\n${assetUiText("filterCountHint")}` },
        { id: "category", container: "#asset-category-filter", section: "asset-category",
          className: "asset-category-chip", values: assetCategoryValues, label: assetCategoryLabel,
          title: (value) => `${assetCategoryLabel(value)}\n${assetUiText("filterCountHint")}`,
          order: (a, b) => naturalCompare(assetCategoryLabel(a), assetCategoryLabel(b)) || naturalCompare(a, b) },
        { id: "source", container: "#asset-source-filter", section: "asset-source", order: "count",
          className: "asset-source-chip", values: (entry) => entry.source || ROOT_SOURCE,
          title: () => assetUiText("filterCountHint"),
          label: (value) => (value === ROOT_SOURCE ? assetUiText("rootFolder") : value) },
      ],
      onChange: () => applyAssetFilters(),
    });
  }

  function isMobileLayout() {
    return window.matchMedia(MOBILE_LAYOUT_QUERY).matches;
  }

  let assetPanel = null;

  function ensureAssetPanelToggle() {
    if (assetPanel) return assetPanel;
    assetPanel = window.WebUI.filters.createPanelToggle({
      panel: "#asset-filter-panel",
      toggle: "#asset-filter-toggle",
      left: "#asset-left",
      storageKey: FILTER_PANEL_STORAGE_KEY,
      isMobile: isMobileLayout,
      labels: (collapsed) => assetUiText(collapsed ? "showFilters" : "hideFilters"),
      onChange: () => renderAssetList(),
    });
    return assetPanel;
  }

  function normalizePreviewBackground(value) {
    const color = String(value || "").trim().toLowerCase();
    if (/^#[0-9a-f]{6}$/.test(color)) return color;
    if (/^#[0-9a-f]{3}$/.test(color)) {
      return `#${color[1]}${color[1]}${color[2]}${color[2]}${color[3]}${color[3]}`;
    }
    return DEFAULT_PREVIEW_BACKGROUND;
  }

  function resolveInitialPreviewBackground() {
    return normalizePreviewBackground(storageGet(PREVIEW_BG_STORAGE_KEY) || DEFAULT_PREVIEW_BACKGROUND);
  }

  function setPreviewBackground(value, { persist = true } = {}) {
    ASSET_STATE.previewBackground = normalizePreviewBackground(value);
    if (persist) storageSet(PREVIEW_BG_STORAGE_KEY, ASSET_STATE.previewBackground);
    syncPreviewBackgroundControls();
    queueModelRender();
  }

  function previewBackgroundRgb() {
    const color = normalizePreviewBackground(ASSET_STATE.previewBackground);
    return {
      r: Number.parseInt(color.slice(1, 3), 16),
      g: Number.parseInt(color.slice(3, 5), 16),
      b: Number.parseInt(color.slice(5, 7), 16),
    };
  }

  function previewBackgroundLuminance() {
    const { r, g, b } = previewBackgroundRgb();
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255;
  }

  function selectedAssetSupportsPreviewBackground(entry = ASSET_STATE.selectedEntry) {
    if (!entry) return false;
    const activeFile = getActiveAssetFile(entry);
    if (activeFile?.noDrawableFaces) return false;
    if (entry.kind === "image") return activeFile?.ext === "png";
    if (entry.kind !== "model") return false;
    const activeModel = getActiveModelFile(entry);
    const reviewModel = resolveReviewModelFile(activeModel);
    return ["obj", "fbx"].includes(activeModel?.ext) || reviewModel?.ext === "obj";
  }

  function syncPreviewBackgroundControls(entry = ASSET_STATE.selectedEntry) {
    const controls = $("#asset-preview-bg-controls");
    const input = $("#asset-preview-bg-color");
    const stage = $("#asset-preview-stage");
    if (!controls || !input || !stage) return;

    const color = normalizePreviewBackground(ASSET_STATE.previewBackground);
    const enabled = selectedAssetSupportsPreviewBackground(entry);
    controls.hidden = !enabled;
    const modelInput = $("#asset-model-color");
    const modelLabel = $("#asset-model-color-label");
    const isModel = entry?.kind === "model";
    modelInput.hidden = !isModel;
    modelLabel.hidden = !isModel;
    modelInput.value = ASSET_STATE.modelColor;
    modelLabel.textContent = assetUiText("modelColor");
    modelInput.setAttribute("aria-label", assetUiText("modelColor"));
    $("#asset-model-only-label").hidden = !isModel;
    $("#asset-model-only-text").textContent = assetUiText("modelOnly");
    $("#asset-model-only").checked = ASSET_STATE.modelOnly;
    $("#asset-model-emission-label").hidden = !isModel;
    $("#asset-model-emission-text").textContent = assetUiText("modelEmission");
    $("#asset-model-emission-label").title = assetUiText("modelEmissionHelp");
    $("#asset-model-emission").checked = ASSET_STATE.modelEmission;
    $("#asset-model-emission").disabled = ASSET_STATE.modelOnly;
    stage.classList.toggle("has-preview-bg", enabled);
    stage.style.setProperty("--asset-preview-bg-color", color);
    if (input.value.toLowerCase() !== color) input.value = color;

    $$(".asset-preview-bg-swatch").forEach((button) => {
      const swatchColor = normalizePreviewBackground(button.dataset.color || "");
      button.classList.toggle("is-active", swatchColor === color);
      button.title = assetUiText("previewBackgroundPreset", { color: swatchColor });
      button.setAttribute("aria-label", assetUiText("previewBackgroundPreset", { color: swatchColor }));
    });
  }

  function resolveInitialUiLocale() {
    const fromWindow = normalizeUiLocale(window.WEBUI_UI_LOCALE);
    if (fromWindow) return fromWindow;
    const stored = normalizeUiLocale(storageGet(UI_LOCALE_STORAGE_KEY));
    if (stored) return stored;
    return document.documentElement.lang.toLowerCase().startsWith("zh") ? "zh" : "en";
  }

  function assetUiText(key, replacements = {}) {
    const locale = ASSET_UI_TEXTS[ASSET_STATE.uiLocale] || ASSET_UI_TEXTS.en;
    const template = locale[key] || ASSET_UI_TEXTS.en[key] || key;
    return applyTemplate(template, replacements);
  }

  function assetKindLabel(kind) {
    if (kind === "image") return assetUiText("images");
    if (kind === "model") return assetUiText("models");
    if (kind === "video") return assetUiText("videos");
    return assetTypeLabel(kind);
  }

  function assetBadgeClass(kind) {
    if (kind === "image") return "asset-badge-image";
    if (kind === "model") return "asset-badge-model";
    if (kind === "video") return "asset-badge-video";
    return "asset-badge-file";
  }

  function supportsAssetVariants(kind) {
    return kind === "image" || kind === "model";
  }

  function assetTypeLabel(type) {
    return String(type || "").toUpperCase() || assetUiText("none");
  }

  function applyAssetUiStrings() {
    $("#asset-app-title").textContent = assetUiText("title");
    $("#asset-count-label").textContent = assetUiText("countLabel");
    $("#asset-basic-filter-label").textContent = assetUiText("basicFilters");
    if (assetPanel) assetPanel.sync();
    $("#asset-q").placeholder = assetUiText("searchPlaceholder");
    $("#asset-type-label").textContent = assetUiText("type");
    $("#asset-category-label").textContent = assetUiText("category");
    $("#asset-source-label").textContent = assetUiText("source");
    $("#asset-sort-label").textContent = assetUiText("sort");
    $("#asset-sort-path").textContent = assetUiText("sortPath");
    $("#asset-sort-size-desc").textContent = assetUiText("sortSizeDesc");
    $("#asset-sort-size-asc").textContent = assetUiText("sortSizeAsc");
    $("#asset-sort-name").textContent = assetUiText("sortName");
    $("#asset-reset").textContent = assetUiText("reset");
    $("#asset-list-meta-label").textContent = assetUiText("listUnit");
    if (!ASSET_STATE.selectedEntry) $("#asset-empty").textContent = assetUiText("empty");
    $("#asset-open-raw").textContent = assetUiText("openRawFile");
    $("#asset-download-current").textContent = assetUiText("downloadCurrentFile");
    $("#asset-copy-path").textContent = assetUiText("copyRelativePath");
    $("#asset-preview-label").textContent = assetUiText("preview");
    $("#asset-preview-bg-label").textContent = assetUiText("previewBackground");
    $("#asset-preview-bg-color").title = assetUiText("previewBackgroundCustom");
    $("#asset-preview-bg-color").setAttribute("aria-label", assetUiText("previewBackgroundCustom"));
    syncPreviewBackgroundControls();
    $("#asset-preview-placeholder").textContent = assetUiText("previewPlaceholder");
    $("#asset-inspector-label").textContent = assetUiText("inspector");
    $("#asset-related-label").textContent = assetUiText("relatedFiles");
    $("#asset-variants-label").textContent = assetUiText("lodVariants");
    $("#asset-materials-label").textContent = assetUiText("linkedMaterials");
    $("#asset-textures-label").textContent = assetUiText("linkedTextures");
    $("#asset-references-label").textContent = assetUiText("referencedBy");
    $("#asset-model-stats-label").textContent = assetUiText("modelStats");
  }

  function setAssetUiLocale(locale, { refresh = true } = {}) {
    ASSET_STATE.uiLocale = normalizeUiLocale(locale) || "en";
    applyAssetUiStrings();
    setDocumentTitleForView(ASSET_STATE.activeView);

    if (!refresh || !ASSET_STATE.loaded) return;
    window.WebUI.updateBadges.syncFilter("asset", "files", ASSET_STATE.facets);
    ASSET_STATE.facets.render();
    applyAssetFilters();
    if (ASSET_STATE.selectedEntry) renderSelectedAsset();
  }

  function resolveViewFromHash() {
    const hash = (window.location.hash || "").replace(/^#/, "").toLowerCase();
    if (hash === "activities") return "activities"; // Legacy links normalize in setActiveView.
    return AVAILABLE_VIEWS.has(hash) ? hash : "story";
  }

  function debugViewsEnabled() {
    return document.body.classList.contains("show-debug");
  }

  function availableView(view) {
    const candidate = AVAILABLE_VIEWS.has(view) ? view : "story";
    if (!DEBUG_ONLY_VIEWS.has(candidate) || debugViewsEnabled()) return candidate;
    return DEBUG_VIEW_FALLBACKS[candidate] || "story";
  }

  function syncDebugViewVisibility() {
    const enabled = debugViewsEnabled();
    $$(".view-tab[data-debug-view]").forEach((button) => {
      button.hidden = !enabled;
    });
    if (!enabled && DEBUG_ONLY_VIEWS.has(ASSET_STATE.activeView)) {
      setActiveView(DEBUG_VIEW_FALLBACKS[ASSET_STATE.activeView] || "story");
    }
  }

  function updateHashForView(view) {
    const nextHash = AVAILABLE_VIEWS.has(view) ? `#${view}` : "#story";
    if (window.location.hash === nextHash) return;
    const url = `${window.location.pathname}${window.location.search}${nextHash}`;
    history.replaceState(null, "", url);
  }

  function setViewBusy(view, busy) {
    const page = document.querySelector(`.page-view[data-view="${view}"]`);
    if (!page) return;
    page.setAttribute("aria-busy", busy ? "true" : "false");
  }

  function setShellStatus(message = "", { tone = "info", view = ASSET_STATE.activeView } = {}) {
    const status = $("#shell-status");
    if (!status) return;
    const text = String(message || "").trim();
    status.textContent = text;
    status.dataset.tone = tone;
    status.dataset.view = view || "";
    status.hidden = !text || (view && view !== ASSET_STATE.activeView);
  }

  function clearShellStatus(view = "") {
    const status = $("#shell-status");
    if (!status || (view && status.dataset.view !== view)) return;
    status.textContent = "";
    status.hidden = true;
    delete status.dataset.tone;
    delete status.dataset.view;
  }

  function setDocumentTitleForView(view) {
    const titleKeys = {
      story: "storyPageTitle",
      characters: "charactersPageTitle",
      gameplay: "gameplayPageTitle",
      audio: "audioPageTitle",
      "map": "mapRecoveryPageTitle",
      assets: "assetsPageTitle",
      reference: "referencePageTitle",
      updates: "updatesPageTitle",
      recovery: "recoveryPageTitle",
      "data-inspector": "dataInspectorPageTitle",
    };
    const pageTitle = uiText(titleKeys[view] || titleKeys.story);
    document.title = `${pageTitle} \u00b7 ${uiText("siteTitle")}`;
  }

  function setActiveView(view, { updateHash = true } = {}) {
    if (view === "activities") {
      const url = new URL(location.href);
      url.hash = "gameplay";
      url.searchParams.set("gameplayKind", "activity");
      url.searchParams.delete("activityTable");
      history.replaceState(history.state, "", url);
      view = "gameplay";
    }
    const requestedView = AVAILABLE_VIEWS.has(view) ? view : "story";
    ASSET_STATE.activeView = availableView(requestedView);
    document.body.dataset.activeView = ASSET_STATE.activeView;

    $$(".view-tab").forEach((button) => {
      const isActive = button.dataset.view === ASSET_STATE.activeView;
      button.classList.toggle("is-active", isActive);
      button.setAttribute("aria-selected", isActive ? "true" : "false");
      button.tabIndex = isActive ? 0 : -1;
      if (isActive) button.scrollIntoView({ block: "nearest", inline: "nearest" });
    });
    $$(".page-view").forEach((page) => {
      const isActive = page.dataset.view === ASSET_STATE.activeView;
      page.hidden = !isActive;
      page.classList.toggle("is-active", isActive);
    });

    const shellStatus = $("#shell-status");
    if (shellStatus) shellStatus.hidden = !shellStatus.textContent || shellStatus.dataset.view !== ASSET_STATE.activeView;

    if (updateHash || ASSET_STATE.activeView !== requestedView) {
      updateHashForView(ASSET_STATE.activeView);
    }
    setDocumentTitleForView(ASSET_STATE.activeView);

    if (ASSET_STATE.activeView === "assets") {
      ensureAssetsLoaded().then(() => {
        renderAssetList();
        if (ASSET_STATE.selectedEntry) renderSelectedAsset();
        queueModelRender();
      }).catch(() => {});
    }

    window.dispatchEvent(new CustomEvent("webui:view-changed", {
      detail: { view: ASSET_STATE.activeView },
    }));

    requestAnimationFrame(() => {
      window.dispatchEvent(new Event("resize"));
    });
  }

  function bindViewTabs() {
    const tabs = $$(".view-tab");
    const openTab = (view) => {
      if (view === "gameplay" && window.WebUI.gameplayTabs) {
        window.WebUI.gameplayTabs.open("character", "", { fresh: true });
      } else {
        const url = new URL(location.href);
        url.search = "";
        url.hash = "";
        history.replaceState(history.state, "", url);
        setActiveView(view);
      }
    };
    tabs.forEach((button) => {
      button.addEventListener("click", () => openTab(button.dataset.view));
    });
    $("#view-tabs")?.addEventListener("keydown", (event) => {
      if (!event.target.matches(".view-tab")) return;
      const visibleTabs = tabs.filter((tab) => !tab.hidden);
      const currentIndex = visibleTabs.indexOf(event.target);
      if (currentIndex < 0) return;
      let nextIndex = currentIndex;
      if (event.key === "ArrowRight") nextIndex = (currentIndex + 1) % visibleTabs.length;
      else if (event.key === "ArrowLeft") nextIndex = (currentIndex - 1 + visibleTabs.length) % visibleTabs.length;
      else if (event.key === "Home") nextIndex = 0;
      else if (event.key === "End") nextIndex = visibleTabs.length - 1;
      else return;
      event.preventDefault();
      const nextTab = visibleTabs[nextIndex];
      nextTab.focus();
      openTab(nextTab.dataset.view);
    });
    window.addEventListener("hashchange", () => {
      // Normalize retired/unknown hashes as well as selecting valid views.
      setActiveView(resolveViewFromHash(), { updateHash: false });
    });
  }

  function bindAssetEvents() {
    $("#asset-q").addEventListener("input", (ev) => {
      clearTimeout(ASSET_STATE.qTimer);
      const value = ev.target.value;
      ASSET_STATE.qTimer = setTimeout(() => {
        ASSET_STATE.filters.q = value.trim().toLowerCase();
        applyAssetFilters();
      }, 120);
    });

    $("#asset-sort").addEventListener("change", (ev) => {
      ASSET_STATE.filters.sort = ev.target.value;
      applyAssetFilters();
    });

    $("#asset-reset").addEventListener("click", () => {
      ASSET_STATE.filters = createDefaultFilters();
      $("#asset-q").value = "";
      $("#asset-sort").value = "path";
      ASSET_STATE.facets.reset();
    });

    $("#asset-model-color").addEventListener("input", (ev) => {
      ASSET_STATE.modelColor = normalizePreviewBackground(ev.target.value);
      queueModelRender();
    });
    $("#asset-model-only").addEventListener("change", (ev) => {
      ASSET_STATE.modelOnly = ev.target.checked;
      syncPreviewBackgroundControls();
      queueModelRender();
    });
    $("#asset-model-emission").addEventListener("change", (ev) => {
      ASSET_STATE.modelEmission = ev.target.checked;
      queueModelRender();
    });
    $("#asset-preview-bg-color").addEventListener("input", (ev) => {
      setPreviewBackground(ev.target.value);
    });

    $("#asset-preview-bg-presets").addEventListener("click", (ev) => {
      const button = ev.target.closest(".asset-preview-bg-swatch");
      if (!button) return;
      setPreviewBackground(button.dataset.color || DEFAULT_PREVIEW_BACKGROUND);
    });
    $("#asset-list-wrap").addEventListener("scroll", renderAssetList);
    window.addEventListener("resize", () => {
      renderAssetList();
      queueModelRender();
    });

    $("#asset-list").addEventListener("click", (ev) => {
      const groupRow = ev.target.closest(".asset-group-row");
      if (groupRow) {
        toggleAssetPath(groupRow.dataset.path || "");
        return;
      }

      const itemRow = ev.target.closest(".asset-item-row");
      if (!itemRow) return;
      const entry = ASSET_STATE.entryByRel.get(itemRow.dataset.rel || "");
      if (entry) selectAsset(entry, { scrollIntoView: false });
    });

    $("#asset-copy-path").addEventListener("click", async () => {
      const rel = getSelectedAssetRelForUrl();
      if (!rel) return;
      const ok = await copyTextToClipboard(rel);
      $("#asset-copy-path").textContent = ok ? assetUiText("copiedPath") : assetUiText("copyFailed");
      window.setTimeout(() => {
        $("#asset-copy-path").textContent = assetUiText("copyRelativePath");
      }, 1200);
    });
  }

  function ensureAssetsLoaded() {
    if (ASSET_STATE.loaded) return Promise.resolve();
    if (ASSET_STATE.loadPromise) return ASSET_STATE.loadPromise;

    setViewBusy("assets", true);
    clearShellStatus("assets");
    window.WebUI.showLoader("assets");
    ASSET_STATE.loadPromise = window.WebUI.fetchWithProgress("data/assets/index.json", {
        onProgress: window.WebUI.loaderProgress("assets"),
      })
        .then((res) => {
          if (!res.ok) throw new Error(`assets/index.json HTTP ${res.status}`);
          return res.json();
        })
      .then(async (payload) => {
        window.WebUI.updateLoaderPhase("assets", "preparing");
        await window.WebUI.nextPaint();
        await window.WebUI.updateBadges.loadFiles();

        const hydrated = hydrateEntries(payload.entries || []);
        ASSET_STATE.entries = hydrated.entries;
        ASSET_STATE.entryByRel = hydrated.entryByRel;
        ASSET_STATE.rawEntryByRel = hydrated.rawEntryByRel;
        ASSET_STATE.relations = {};
        ASSET_STATE.relationsPromise = null;
        // Optional sidecar: a missing or stale file leaves every asset
        // unowned instead of failing the page.
        fetch("data/assets/table_owners.json")
          .then((res) => (res.ok ? res.json() : null))
          .then((owners) => {
            ASSET_STATE.tableOwners = (owners && owners.entries) || {};
            if (ASSET_STATE.selectedEntry) renderSelectedAsset();
          })
          .catch(() => {});
        ASSET_STATE.exportRoot = String(payload.root || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, "");
        ASSET_STATE.collisionStatus = payload.collision || null;
        ASSET_STATE.sourceRoots = payload.sourceRoots && typeof payload.sourceRoots === "object"
          ? Object.fromEntries(
              Object.entries(payload.sourceRoots).map(([key, value]) => [
                key,
                String(value || "").replace(/\\/g, "/").replace(/^\/+|\/+$/g, ""),
              ])
            )
          : {};
        ASSET_STATE.loaded = true;
        $("#asset-count").textContent = ASSET_STATE.entries.length.toLocaleString();
        window.WebUI.updateLoaderPhase("assets", "rendering");
        await window.WebUI.nextPaint();

        window.WebUI.updateBadges.syncFilter("asset", "files", ASSET_STATE.facets);
        ASSET_STATE.facets.render(ASSET_STATE.entries);
        seedAssetExpansions();
        applyAssetFilters();
        applyInitialAssetSelection();
        await window.WebUI.nextPaint();
        window.WebUI.hideLoader("assets");
        setViewBusy("assets", false);
        $("#asset-empty")?.classList.remove("is-error");
      })
      .catch((error) => {
        window.WebUI.hideLoader("assets");
        setViewBusy("assets", false);
        ASSET_STATE.loadPromise = null;
        $("#asset-empty").textContent = assetUiText("assetIndexError", { error: String(error) });
        $("#asset-empty").classList.add("is-error");
        setShellStatus(assetUiText("assetIndexError", { error: String(error) }), { tone: "error", view: "assets" });
        throw error;
      });

    return ASSET_STATE.loadPromise;
  }

  // Material/texture/model relations ship as a sidecar the list, filters and
  // search never read; fetch it on first detail or model-viewer use. A
  // package without it (media only) leaves every asset unrelated.
  function ensureAssetRelations() {
    if (!ASSET_STATE.relationsPromise) {
      ASSET_STATE.relationsPromise = fetch("data/assets/relations.json")
        .then((res) => (res.ok ? res.json() : null))
        .catch(() => null)
        .then((payload) => {
          ASSET_STATE.relations = (payload && payload.relations) || {};
          ASSET_STATE.relationsLoaded = true;
        });
    }
    return ASSET_STATE.relationsPromise;
  }

  let storedShaderPromise;
  function validStoredShaderInstructions(value) {
    const count = (v) => Number.isSafeInteger(v) && v >= 0;
    return value && Array.isArray(value.passes) && value.passes.every((p) =>
      typeof p.passName === "string" && ["vertex","fragment"].includes(p.stage) && count(p.shaderLOD) &&
      count(p.candidatePrograms) && [p.completeRegisterJoins,p.dynamicReadPrograms,p.anonymousReadPrograms].every((v) => count(v) && v <= p.candidatePrograms) &&
      Array.isArray(p.namedResourceReads) && p.namedResourceReads.every((r) => typeof r.name === "string" && ["t","s","u"].includes(r.kind) && count(r.presentPrograms) && r.presentPrograms <= p.candidatePrograms) &&
      Array.isArray(p.namedFieldReads) && p.namedFieldReads.every((f) => typeof f.name === "string" && typeof f.buffer === "string" &&
        count(f.presentPrograms) && f.presentPrograms <= p.candidatePrograms && Array.isArray(f.byteOffsets) && f.byteOffsets.every(count)) &&
      Array.isArray(p.gaps) && p.gaps.every((g) => typeof g.register === "string" && typeof g.reason === "string" && count(g.presentPrograms) && g.presentPrograms <= p.candidatePrograms));
  }
  function storedShaderDetails(asset) {
    const details = document.createElement("details");
    const summary = document.createElement("summary");
    summary.textContent = assetUiText("collisionShaderDetails");
    const body = document.createElement("div");
    details.append(summary, body);
    details.addEventListener("toggle", async () => {
      if (!details.open || details.dataset.loaded) return;
      details.dataset.loaded = "1";
      storedShaderPromise ||= fetch("data/assets/shader_analysis/index.json")
        .then((r) => r.ok ? r.json() : null).catch(() => null);
      const payload = await storedShaderPromise;
      const info = payload?.schema === "endfield.assets-shader-analysis.v3" && payload.status === "validated"
        ? payload.bindings?.[asset.rel] : null;
      const keywordArrays = [info?.validKeywords, info?.invalidKeywords, info?.passNames, info?.undeclaredValidKeywords];
      if (!info || info.schema !== "endfield.stored-material-shader-info.v3" || typeof asset.sha256 !== "string" || !asset.sha256 ||
          info.materialArtifactSha256 !== asset.sha256 || typeof info.name !== "string" ||
          !keywordArrays.every((a) => Array.isArray(a) && a.every((v) => typeof v === "string")) ||
          !Number.isSafeInteger(info.conditionalCandidateCount) || !Number.isSafeInteger(info.compiledVariantCount) ||
          info.conditionalCandidateCount < 0 || info.compiledVariantCount < info.conditionalCandidateCount ||
          (info.instructions !== undefined && !validStoredShaderInstructions(info.instructions))) {
        body.textContent = assetUiText("collisionShaderUnavailable");
        return;
      }
      body.textContent = [info.name,
        assetUiText("collisionShaderKeywords", {keywords:info.validKeywords.join(", ") || "—"}),
        assetUiText("collisionShaderInvalid", {keywords:info.invalidKeywords.join(", ") || "—"}),
        assetUiText("collisionShaderPasses", {passes:info.passNames.join(", ") || "—"}),
        assetUiText("collisionShaderCandidates", {count:info.conditionalCandidateCount,total:info.compiledVariantCount}),
        ...(info.undeclaredValidKeywords.length ? [assetUiText("collisionShaderUnknown", {keywords:info.undeclaredValidKeywords.join(", ")})] : []),
        assetUiText("collisionShaderBoundary")].join("\n");
      if (typeof info.shaderAnalysisUrl === "string" && info.shaderAnalysisUrl.startsWith("/data/assets/shader_analysis/selection-")) {
        const link = document.createElement("a");
        link.href = info.shaderAnalysisUrl; link.download = info.shaderAnalysisUrl.split("/").pop();
        link.textContent = assetUiText("collisionShaderDownload");
        body.append(document.createTextNode("\n"), link);
      }
      if (info.parameters) {
        const parameters = document.createElement("details"), title = document.createElement("summary");
        title.textContent = assetUiText("collisionShaderParameters"); parameters.appendChild(title);
        const values = document.createElement("details"), valuesTitle = document.createElement("summary"), valueRows = document.createElement("div");
        valuesTitle.textContent = assetUiText("collisionShaderStoredValues") + ` (${info.parameters.storedValues.length})`;
        valueRows.textContent = info.parameters.storedValues.map((v) => v.name + " = " + JSON.stringify(v.value)).join("\n");
        values.append(valuesTitle,valueRows); parameters.append(values,document.createTextNode(assetUiText("collisionShaderDefaults", {count:info.parameters.unoverriddenDeclarations.length})));
        for (const pass of info.parameters.passes) {
          const section = document.createElement("details"), heading = document.createElement("summary");
          heading.textContent = assetUiText("collisionShaderParameterPass", {pass:pass.passName,lod:pass.shaderLOD,count:pass.candidateRecords});
          const fields = document.createElement("div");
          fields.textContent = [...pass.namedResources.map((r) => assetUiText("collisionShaderResource", {name:r.name,count:r.presentRecords,total:pass.candidateRecords})),
            ...pass.namedFields.map((f) => assetUiText("collisionShaderField", {buffer:f.buffer,name:f.name,count:f.presentRecords,total:pass.candidateRecords,
              offsets:[...new Set(f.alternatives.map((a) => a.byteOffset))].join(", ")}))].join("\n");
          section.append(heading, fields); parameters.appendChild(section);
        }
        parameters.appendChild(document.createTextNode(assetUiText("collisionShaderBoundary"))); body.appendChild(parameters);
      }
      if (info.instructions?.passes.length) {
        const instructions = document.createElement("details"), title = document.createElement("summary");
        title.textContent = assetUiText("collisionShaderInstructions"); instructions.append(title);
        for (const pass of info.instructions.passes) {
          const section = document.createElement("details"), heading = document.createElement("summary"), reads = document.createElement("div");
          heading.textContent = assetUiText("collisionShaderInstructionPass", {pass:pass.passName,lod:pass.shaderLOD,stage:pass.stage,count:pass.candidatePrograms});
          reads.textContent = [assetUiText("collisionShaderInstructionStatus", {complete:pass.completeRegisterJoins,total:pass.candidatePrograms,dynamic:pass.dynamicReadPrograms,anonymous:pass.anonymousReadPrograms}),
            ...pass.namedResourceReads.map((r) => assetUiText("collisionShaderInstructionResource", {kind:r.kind,name:r.name,count:r.presentPrograms,total:pass.candidatePrograms})),
            ...pass.namedFieldReads.map((f) => assetUiText("collisionShaderInstructionField", {buffer:f.buffer,name:f.name,count:f.presentPrograms,total:pass.candidatePrograms,offsets:f.byteOffsets.join(", ")})),
            ...pass.gaps.map((g) => `${g.register}: ${g.reason} (${g.presentPrograms}/${pass.candidatePrograms})`)].join("\n");
          section.append(heading,reads); instructions.append(section);
        }
        instructions.append(document.createTextNode(assetUiText("collisionShaderInstructionBoundary"))); body.append(instructions);
      }
    });
    return details;
  }

  function normalizeImageCategory(value) {
    const category = String(value || "").trim().toLowerCase();
    return category || "other";
  }

  function assetCategoryLabel(category) {
    const value = normalizeImageCategory(category);
    if (value === "other") return assetUiText("categoryOther");
    if (value === "material-like") return assetUiText("textureRoleMaterial");
    const prefixMatch = value.match(/^model-prefix-([a-z])$/);
    if (prefixMatch) return `Model Prefix ${prefixMatch[1].toUpperCase()}`;
    if (MODEL_CATEGORY_LABELS[value]) return MODEL_CATEGORY_LABELS[value];
    return value
      .replace(/[_-]/g, " ")
      .replace(/\b[a-z]/g, (char) => char.toUpperCase());
  }

  function isObjModel(kind, ext) {
    return kind === "model" && String(ext || "").toLowerCase() === "obj";
  }

  function modelBaseStem(stem = "") {
    return assetGroupStem("model", stem).trim();
  }

  function modelPrefixMatch(stem = "") {
    return modelBaseStem(stem).match(MODEL_PREFIX_RE);
  }

  function modelStemWithoutPrefix(stem = "") {
    const base = modelBaseStem(stem);
    const match = base.match(MODEL_PREFIX_RE);
    return match ? String(match[2] || "").trim() : base;
  }

  function isUnpatternedObjStem(stem = "") {
    const base = modelBaseStem(stem);
    return !base || /^\d+$/.test(base) || !MODEL_PREFIX_RE.test(base);
  }

  function deriveModelGroupInfo(kind = "", stem = "", ext = "") {
    if (!isObjModel(kind, ext)) return null;
    if (isUnpatternedObjStem(stem)) return { ...MODEL_UNPATTERNED_OBJ_GROUP };
    const groupStem = modelStemWithoutPrefix(stem);
    if (!groupStem) return { ...MODEL_UNPATTERNED_OBJ_GROUP };
    const originalStem = modelBaseStem(stem);
    return {
      key: groupStem.toLowerCase(),
      label: groupStem,
      raw: originalStem && originalStem !== groupStem ? originalStem : "",
    };
  }

  function classifyModelSemanticCategory(stem = "") {
    const normalized = modelStemWithoutPrefix(stem).toLowerCase();
    const tokens = new Set(normalized.split(/[^a-z0-9]+/).filter(Boolean));
    for (const rule of MODEL_SEMANTIC_CATEGORY_RULES) {
      if (rule.tokens.some((token) => tokens.has(token))) return rule.category;
    }
    return "";
  }

  function deriveModelCategories(kind = "", stem = "", ext = "") {
    if (!isObjModel(kind, ext)) return [];
    const categories = [];
    const match = modelPrefixMatch(stem);
    categories.push(match && !isUnpatternedObjStem(stem) ? `model-prefix-${match[1].toLowerCase()}` : "model-unpatterned-obj");
    const semantic = classifyModelSemanticCategory(stem);
    if (semantic && !categories.includes(semantic)) categories.push(semantic);
    return categories;
  }

  function chooseModelCategories(entries) {
    const counts = {};
    for (const entry of entries || []) {
      for (const category of entry?.modelCategories || []) {
        counts[category] = (counts[category] || 0) + 1;
      }
    }
    const categories = Object.keys(counts);
    categories.sort((a, b) => {
      const aPrefix = a.startsWith("model-prefix-") || a === "model-unpatterned-obj";
      const bPrefix = b.startsWith("model-prefix-") || b === "model-unpatterned-obj";
      if (aPrefix !== bPrefix) return aPrefix ? -1 : 1;
      return (counts[b] - counts[a]) || naturalCompare(a, b);
    });
    return categories;
  }

  function chooseImageCategory(entries) {
    const counts = countBy(entries || [], (entry) => normalizeImageCategory(entry && entry.imageCategory));
    const categories = Object.keys(counts);
    if (!categories.length) return "other";
    categories.sort((a, b) => {
      if (a === "other" && b !== "other") return 1;
      if (b === "other" && a !== "other") return -1;
      return (counts[b] - counts[a]) || naturalCompare(a, b);
    });
    return categories[0] || "other";
  }

  function isCharacterIllustrationImage(entry) {
    if (!entry || normalizeImageCategory(entry.imageCategory) !== "character") return false;
    return /^pic(?:[_-][a-z0-9]+)*[_-]chr(?:[_-]|$)/i.test(entry.stem || entry.rawStem || "");
  }

  function deriveImageExtraCategories(entry) {
    const categories = [];
    if (isCharacterIllustrationImage(entry)) categories.push("character-illustration");
    return categories;
  }

  function chooseImageExtraCategories(entries) {
    const values = new Set();
    for (const entry of entries || []) {
      for (const category of entry?.imageExtraCategories || deriveImageExtraCategories(entry)) {
        const normalized = normalizeImageCategory(category);
        if (normalized && normalized !== "other") values.add(normalized);
      }
    }
    return Array.from(values).sort((a, b) => naturalCompare(assetCategoryLabel(a), assetCategoryLabel(b)) || naturalCompare(a, b));
  }

  function assetCategoryValues(entry) {
    if (!entry) return [];
    if (entry.kind === "image") {
      const values = new Set([normalizeImageCategory(entry.imageCategory)]);
      for (const category of entry.imageExtraCategories || []) {
        const normalized = normalizeImageCategory(category);
        if (normalized && normalized !== "other") values.add(normalized);
      }
      if (entry.materialLike) values.add("material-like");
      return Array.from(values);
    }
    if (entry.kind === "model") {
      return Array.isArray(entry.modelCategories) ? entry.modelCategories.filter(Boolean) : [];
    }
    return [];
  }

  function formatAssetCategoryMeta(entry) {
    const values = assetCategoryValues(entry).map(assetCategoryLabel);
    if (entry.noDrawableFaces) values.push(assetUiText("emptyModelTag"));
    if (entry.collision) values.push(assetUiText("collisionTag"));
    return values.join(" / ");
  }

  function modelRecoveryForRaw(raw) {
    const recovery = raw.mr;
    return recovery?.status === "incomplete_geometry" && recovery.h && recovery.h === raw.h
      && Number.isSafeInteger(recovery.expected) && Number.isSafeInteger(recovery.exported)
      && recovery.exported >= 0 && recovery.expected > recovery.exported ? recovery : null;
  }

  function hydrateEntries(entries) {
    const hydrated = entries.map((raw) => {
      // Unity object documents are browsed on the Data page; an index built
      // before they left this page may still list them, so unknown kinds drop.
      const kind = String(raw.k || "image");
      if (!["image", "model", "video"].includes(kind)) return null;
      const rel = String(raw.r || "");
      const parts = rel.split("/").filter(Boolean);
      const name = parts[parts.length - 1] || rel;
      const source = parts[0] || "";
      const dirParts = parts.slice(1, -1);
      const dir = dirParts.join("/");
      const extIndex = name.lastIndexOf(".");
      const ext = extIndex >= 0 ? name.slice(extIndex + 1).toLowerCase() : "";
      const stemInfo = exportedAssetStemInfo(rel, name);
      if (!stemInfo || !stemInfo.stem) return null;
      const stem = raw.cl && raw.n ? String(raw.n) : stemInfo.stem;
      const groupInfo = deriveAssetGroupInfo(kind, stem, ext);
      const textureVariant = kind === "image" ? inferTextureVariantStem(stem, ext) : null;
      // Animator FBX: the prefab path recovered from the asset map. Same-name
      // prefabs at different paths can differ, so LOD families stay scoped to
      // their prefab path. Identical exported content is collapsed below.
      const container = kind === "model" ? String(raw.c || "") : "";
      const resourcePaths = kind === "model"
        ? Array.from(new Set([container, ...(raw.cs || [])].filter(Boolean)))
        : [];
      const variantScope = raw.cl ? `${source}::${raw.cl.key}` : ext === "fbx" ? `${source}::${container || rel}` : (kind === "model" || textureVariant ? source : dir);
      const lodMatch = kind === "model" ? stem.match(/(?:^|[_-])lod(\d+)$/i) : null;
      const lod = lodMatch ? Number(lodMatch[1]) : null;
      const imageCategory = kind === "image" ? normalizeImageCategory(raw.ic) : "";
      const imageExtraCategories = kind === "image" ? deriveImageExtraCategories({ imageCategory, stem, rawStem: stemInfo.rawStem }) : [];
      const materialLike = kind === "image" && !!raw.mt;
      const modelCategories = kind === "model" ? deriveModelCategories(kind, stem, ext) : [];
      return {
        kind,
        rel,
        size: Number(raw.s || 0),
        noDrawableFaces: kind === "model" && raw.nd === true,
        modelRecovery: kind === "model" ? modelRecoveryForRaw(raw) : null,
        collision: kind === "model" && raw.cl ? raw.cl : null,
        // A Sprite image has no file: it is a crop of this texture.
        cropOf: String(raw.crop || ""),
        pixelSize: raw.iw && raw.ih ? `${raw.iw}\u00d7${raw.ih}` : "",
        name: raw.cl ? `${stem}.${ext}` : name,
        dir,
        variantScope,
        container,
        resourcePaths,
        source,
        ext,
        stem,
        rawStem: stemInfo.rawStem,
        pathId: stemInfo.pathId || String(raw.pid || ""),
        contentHash: String(raw.h || raw.hash || raw.sha256 || ""),
        fbxContentHash: ext === "fbx" ? String(raw.fc || "") : "",
        fbxVariantHash: ext === "fbx" ? String(raw.fv || "") : "",
        exactFileDuplicate: String(raw.d || ""),
        family: stripAssetLodSuffix(stem),
        familyKey: `${source}::${groupInfo.key}`.toLowerCase(),
        groupKey: groupInfo.key,
        groupLabel: groupInfo.label,
        groupRaw: groupInfo.raw,
        lod,
        imageCategory,
        imageExtraCategories,
        materialLike,
        modelCategories,
        previewRel: String(raw.p || ""),
        // Animator FBX named after a generic object (Actor, offset): the scene root it belongs to.
        sceneRoot: kind === "model" ? String(raw.fr || "") : "",
        // Timelines keep their actors and effects under sibling `<name>_Actor` / `<name>_Effect` roots.
        sceneGroup: kind === "model" ? String(raw.fr || "").replace(/_(?:Actor|Effect)$/i, "") : "",
        searchText: "",
        variantLabel: "",
        grouped: false,
        duplicateCount: 1,
        rawRels: [rel],
      };
    }).filter(Boolean);

    const stemsByScope = new Map();
    for (const entry of hydrated) {
      if (!supportsAssetVariants(entry.kind)) continue;
      const scopeKey = `${entry.kind}::${entry.variantScope || entry.dir}`.toLowerCase();
      let scope = stemsByScope.get(scopeKey);
      if (!scope) {
        scope = new Set();
        stemsByScope.set(scopeKey, scope);
      }
      scope.add(entry.stem.toLowerCase());
    }

    const sceneRootCounts = new Map();
    for (const entry of hydrated) {
      if (!entry.sceneGroup) continue;
      const rootKey = `${entry.source}::${entry.sceneGroup}`.toLowerCase();
      sceneRootCounts.set(rootKey, (sceneRootCounts.get(rootKey) || 0) + 1);
    }
    // An Animator on the scene root itself carries no `fr`: its own name is the root.
    for (const entry of hydrated) {
      if (entry.sceneGroup || entry.kind !== "model" || entry.ext !== "fbx" || entry.dir !== "Animator") continue;
      const group = entry.stem.replace(/_(?:Actor|Effect)$/i, "");
      const rootKey = `${entry.source}::${group}`.toLowerCase();
      if (!sceneRootCounts.has(rootKey)) continue;
      entry.sceneRoot = entry.stem;
      entry.sceneGroup = group;
      sceneRootCounts.set(rootKey, sceneRootCounts.get(rootKey) + 1);
    }

    const groupedFamilies = new Set();
    const suffixedEntries = new Map();
    const suffixedFamilyVariants = new Map();
    for (const entry of hydrated) {
      if (!supportsAssetVariants(entry.kind)) continue;
      const scopeKey = `${entry.kind}::${entry.variantScope || entry.dir}`.toLowerCase();
      const suffixFamily = inferGroupedFamily(entry);
      if (!suffixFamily) continue;
      const familyKey = `${scopeKey}::${suffixFamily.parentStem}`.toLowerCase();
      let labels = suffixedFamilyVariants.get(familyKey);
      if (!labels) {
        labels = new Set();
        suffixedFamilyVariants.set(familyKey, labels);
      }
      labels.add(String(suffixFamily.suffixLabel || "").toLowerCase());
    }

    for (const entry of hydrated) {
      if (!supportsAssetVariants(entry.kind)) continue;
      const scopeKey = `${entry.kind}::${entry.variantScope || entry.dir}`.toLowerCase();
      if (entry.lod !== null) {
        groupedFamilies.add(`${scopeKey}::${entry.family}`.toLowerCase());
        continue;
      }

      const suffixFamily = inferGroupedFamily(entry);
      if (!suffixFamily) continue;
      const parentStem = suffixFamily.parentStem;
      const suffixLabel = suffixFamily.suffixLabel;
      if (!parentStem || !suffixLabel) continue;

      const scope = stemsByScope.get(scopeKey);
      const familyKey = `${scopeKey}::${parentStem}`.toLowerCase();
      const hasBaseEntry = !!(scope && scope.has(parentStem.toLowerCase()));
      const siblingSuffixes = suffixedFamilyVariants.get(familyKey);
      const hasTextureSet = !!(siblingSuffixes && siblingSuffixes.size > 1);
      if (!hasBaseEntry && !hasTextureSet) continue;
      groupedFamilies.add(familyKey);
      suffixedEntries.set(entry.rel, { parentStem, suffixLabel });
    }

    for (const entry of hydrated) {
      const scopeKey = `${entry.kind}::${entry.variantScope || entry.dir}`.toLowerCase();
      const suffixed = suffixedEntries.get(entry.rel);
      const ownFamilyKey = `${scopeKey}::${entry.stem}`.toLowerCase();
      const lodFamilyKey = `${scopeKey}::${entry.family}`.toLowerCase();
      const suffixFamilyKey = suffixed ? `${scopeKey}::${suffixed.parentStem}`.toLowerCase() : "";

      // Distinct FBX content stays separate; only LOD levels of one
      // prefab form a variant set, as for OBJ meshes. A prefab name's
      // trailing number is part of the name, so FBX skip suffix families.
      if (supportsAssetVariants(entry.kind) && entry.lod !== null && groupedFamilies.has(lodFamilyKey)) {
        entry.family = entry.family;
        entry.grouped = true;
        entry.variantLabel = `LOD ${entry.lod}`;
      } else if (supportsAssetVariants(entry.kind) && entry.ext !== "fbx" && suffixed && groupedFamilies.has(suffixFamilyKey)) {
        entry.family = suffixed.parentStem;
        entry.grouped = true;
        entry.variantLabel = suffixed.suffixLabel;
      } else if (supportsAssetVariants(entry.kind) && entry.ext !== "fbx" && groupedFamilies.has(ownFamilyKey)) {
        entry.family = entry.stem;
        entry.grouped = true;
        entry.variantLabel = entry.name;
      } else {
        entry.family = entry.stem;
        entry.grouped = false;
        entry.variantLabel = entry.name;
      }

      const familyGroupInfo = deriveAssetGroupInfo(entry.kind, entry.family, entry.ext);
      entry.groupKey = familyGroupInfo.key;
      entry.groupLabel = familyGroupInfo.label;
      entry.groupRaw = familyGroupInfo.raw;
      entry.familyKey = `${entry.source}::${familyGroupInfo.key}`.toLowerCase();
      // The path fields below already carry every file name except these;
      // walking the whole entry for file names cost seconds on 200k rows.
      entry.searchText = [
        window.WebUI.linkedFileSearchText(entry.cropOf, entry.previewRel, entry.collision),
        collisionEvidenceSearchTerms(entry.collision),
        entry.variantScope,
        entry.familyKey,
        entry.rel,
        entry.name,
        entry.dir,
        entry.source,
        entry.groupKey,
        entry.groupLabel,
        entry.groupRaw,
        entry.sceneRoot,
        entry.container,
        ...entry.resourcePaths,
        entry.rawStem,
        entry.pathId,
        entry.contentHash,
        entry.family,
        entry.variantLabel,
        entry.imageCategory,
        ...(entry.imageExtraCategories || []),
        ...(entry.modelCategories || []),
        entry.materialLike ? "material material-like texture engine" : "",
        entry.collision ? "collision cooked physics" : "",
        entry.ext,
        entry.kind,
      ].join(" ").toLowerCase();
    }

    const rawEntryByRel = new Map(hydrated.map((entry) => [entry.rel, entry]));
    return groupAssetEntries(collapseDuplicateAssetEntries(hydrated), rawEntryByRel);
  }

  function collisionEvidenceSearchTerms(collision) {
    const authored = collision?.authored;
    const ownerTerms = authored?.owners?.length ? [
      "authored owner hierarchy 存储归属 碰撞体层级",
      ...authored.owners.flatMap((owner) => owner.hierarchy.map((node) => node.name)),
    ].join(" ") : "";
    const runtime = collision?.runtime;
    const modelTerms = collision?.models?.records?.length ? "configured model source 定义场景" : "";
    const prefabTerms = collision?.prefabs?.assemblies?.length ? "assembly prefab 组合预览" : "";
    const boxTerms = collision?.prefabs?.assemblies?.some((a) => a.boxColliderCount > 0) ? "stored box BoxCollider 存储盒形" : "";
    const rendererTerms = collision?.renderers?.prefabs?.length ? ["MeshRenderer MeshFilter material slots 渲染组件 材质槽",
      ...collision.renderers.prefabs.flatMap((p) => p.records.flatMap((r) => [
        ...r.hierarchy.map((n) => n.name), r.mesh.target?.name || "", ...r.materials.map((m) => m.target?.name || "")]))].join(" ") : "";
    if (!runtime?.queryObserved) return `${ownerTerms} ${modelTerms} ${prefabTerms} ${boxTerms} ${rendererTerms}`;
    const counts = runtime.counts;
    return [
      ownerTerms,
      modelTerms,
      prefabTerms,
      boxTerms,
      rendererTerms,
      "observed query 已观察查询",
      counts.movementResults ? "movement result 移动结果" : "",
      counts.acceptedFilterCandidates ? "accepted filter 已接受过滤" : "",
      counts.completeArraySamples ? "complete arrays 完整数组" : "",
      counts.prefixArraySamples ? "captured prefix 捕获前缀" : "",
    ].join(" ");
  }

  function assetContentHash(entry) {
    return String(entry && (entry.contentHash || entry.hash || "") || "").trim();
  }

  function assetSameHashRels(entry) {
    if (!assetContentHash(entry)) return [];
    if (Array.isArray(entry && entry.sameHashFiles) && entry.sameHashFiles.length) {
      return entry.sameHashFiles.map((item) => item.rel || item).filter(Boolean);
    }
    return (entry && entry.rawRels || [entry && entry.rel]).filter(Boolean);
  }

  function formatAssetRelSummary(rels, limit = 32) {
    const values = Array.from(new Set((rels || []).filter(Boolean)));
    if (values.length <= limit) return values.join(", ");
    return `${values.slice(0, limit).join(", ")} ... +${values.length - limit}`;
  }
  function pathIdVariantLabel(entry, index = 0) {
    const pathLabel = entry?.pathId ? `p${entry.pathId}` : (entry?.name || `File ${index + 1}`);
    const baseLabel = entry?.variantLabel && ![entry.name, pathLabel].includes(entry.variantLabel) ? entry.variantLabel : "";
    return baseLabel ? `${baseLabel} / ${pathLabel}` : pathLabel;
  }

  function rawFileVariant(entry, index = 0) {
    const variant = {
      ...entry,
      duplicateCount: 1,
      rawRels: [entry.rel],
      sameHashFiles: assetContentHash(entry) ? [{ rel: entry.rel, hash: assetContentHash(entry) }] : undefined,
      variantLabel: pathIdVariantLabel(entry, index),
    };
    delete variant.variants;
    return variant;
  }

  function collapseDuplicateAssetEntries(entries) {
    // Either exact file equality or the naming-independent content key can
    // join FBX copies. A missing/different `fc` must not split equal bytes.
    const fbxParents = new Map();
    const fbxKeys = (entry) => [
      entry.fbxContentHash ? `fbx-content::${entry.fbxContentHash}` : "",
      assetContentHash(entry) ? `fbx-file::${assetContentHash(entry)}` : "",
    ].filter(Boolean);
    const fbxRoot = (key, parents = fbxParents) => {
      const trail = [];
      while (parents.get(key) !== key) {
        trail.push(key);
        key = parents.get(key);
      }
      for (const prior of trail) parents.set(prior, key);
      return key;
    };
    for (const entry of entries) {
      if (entry.ext !== "fbx") continue;
      const keys = fbxKeys(entry);
      for (const key of keys) if (!fbxParents.has(key)) fbxParents.set(key, key);
      if (keys.length === 2) fbxParents.set(fbxRoot(keys[1]), fbxRoot(keys[0]));
    }
    const buckets = new Map();
    for (const entry of entries) {
      const hash = assetContentHash(entry);
      const identity = supportsAssetVariants(entry.kind) ? entry.stem : entry.rel;
      // `fc` ignores instance placement, pose and bind matrices as well as labels.
      // `h` still means the full-file hash of the unchanged original.
      const key = entry.ext === "fbx"
        ? (fbxKeys(entry).length ? fbxRoot(fbxKeys(entry)[0]) : `rel::${entry.rel}`.toLowerCase())
        : supportsAssetVariants(entry.kind)
        ? `${entry.kind}::${entry.ext}::${entry.source}::${entry.stem}::${entry.sceneRoot || ""}::${entry.collision?.key || "render"}::${entry.noDrawableFaces ? "empty" : "geometry"}`.toLowerCase()
        : (hash ? `hash::${hash}` : `${entry.kind}::${entry.ext}::${entry.source}::${identity}`.toLowerCase());
      let bucket = buckets.get(key);
      if (!bucket) {
        bucket = [];
        buckets.set(key, bucket);
      }
      bucket.push(entry);
    }

    const deduped = [];
    for (const bucket of buckets.values()) {
      bucket.sort((a, b) => compareAssets(a, b, "path"));
      const primary = { ...bucket[0] };
      primary.duplicateCount = bucket.length;
      primary.rawRels = bucket.map((entry) => entry.rel);
      if (assetContentHash(primary)) {
        primary.sameHashFiles = bucket.filter((entry) => assetContentHash(entry) === assetContentHash(primary)).flatMap((entry) => (entry.rawRels || [entry.rel]).map((rel) => ({ rel, hash: assetContentHash(entry) })));
      }
      if (primary.ext === "fbx") {
        primary.resourcePaths = Array.from(new Set(bucket.flatMap((entry) => entry.resourcePaths)));
        if (bucket.length > 1) {
          primary.resourceFiles = primary.rawRels;
        }
        primary.searchText = bucket.map((entry) => entry.searchText).join(" ");
        const variantParents = new Map(bucket.filter((entry) => entry.fbxVariantHash)
          .map((entry) => [entry.fbxVariantHash, entry.fbxVariantHash]));
        const variantRoot = (key) => fbxRoot(key, variantParents);
        const keysByHash = new Map();
        for (const entry of bucket) {
          const hash = assetContentHash(entry);
          if (!entry.fbxVariantHash || !hash) continue;
          const previous = keysByHash.get(hash);
          if (previous) variantParents.set(variantRoot(entry.fbxVariantHash), variantRoot(previous));
          else keysByHash.set(hash, entry.fbxVariantHash);
        }
        const variantKeys = new Set(Array.from(variantParents.keys(), variantRoot));
        if (variantKeys.size > 1) {
          const variantBuckets = new Map();
          for (const entry of bucket) {
            const known = entry.fbxVariantHash || keysByHash.get(assetContentHash(entry));
            const key = known ? variantRoot(known) : `file::${entry.rel}`;
            if (!variantBuckets.has(key)) variantBuckets.set(key, []);
            variantBuckets.get(key).push(entry);
          }
          primary.variants = Array.from(variantBuckets.values(), (files) => {
            const variant = { ...files[0] };
            variant.rawRels = files.map((file) => file.rel);
            variant.duplicateCount = files.length;
            variant.resourcePaths = Array.from(new Set(files.flatMap((file) => file.resourcePaths)));
            variant.resourceFiles = variant.rawRels;
            variant.sameHashFiles = files.filter((file) => assetContentHash(file) === assetContentHash(variant))
              .map((file) => ({ rel: file.rel, hash: assetContentHash(file) }));
            variant.searchText = files.map((file) => file.searchText).join(" ");
            variant.variantLabel = variant.lod === null ? variant.stem : `LOD ${variant.lod} / ${variant.stem}`;
            return variant;
          });
          const labels = new Map();
          for (const variant of primary.variants) labels.set(variant.variantLabel, (labels.get(variant.variantLabel) || 0) + 1);
          for (const variant of primary.variants) {
            if (labels.get(variant.variantLabel) > 1) variant.variantLabel += ` / p${variant.pathId}`;
          }
          primary.fbxPoseVariants = true;
          primary.resourceFiles = primary.rawRels;
          primary.variantCount = primary.variants.length;
          primary.variantSummary = summarizeVariantLabels(primary.variants);
          primary.size = primary.variants.reduce((sum, variant) => sum + variant.size, 0);
        }
        deduped.push(primary);
        continue;
      }
      if (bucket.length > 1) {
        primary.variants = bucket.map(rawFileVariant);
        const variantsByHash = new Map();
        for (const variant of primary.variants) {
          const variantHash = assetContentHash(variant);
          if (!variantHash) continue;
          if (!variantsByHash.has(variantHash)) variantsByHash.set(variantHash, []);
          variantsByHash.get(variantHash).push(variant);
        }
        for (const [variantHash, variants] of variantsByHash.entries()) {
          if (variants.length <= 1) continue;
          const sameHashFiles = variants.map((variant) => ({ rel: variant.rel, hash: variantHash }));
          for (const variant of variants) variant.sameHashFiles = sameHashFiles;
        }
        {
          const exactCopies = new Map();
          primary.variants = primary.variants.filter((variant) => {
            const key = variant.exactFileDuplicate;
            if (!key) return true;
            const existing = exactCopies.get(key);
            if (!existing) {
              exactCopies.set(key, variant);
              return true;
            }
            existing.rawRels.push(...variant.rawRels);
            existing.duplicateCount = existing.rawRels.length;
            existing.searchText = `${existing.searchText} ${variant.searchText}`;
            return false;
          });
        }
        primary.variantCount = primary.variants.length;
        primary.variantSummary = summarizeVariantLabels(primary.variants);
        primary.searchText = [
          primary.searchText,
          ...bucket.slice(1).flatMap((entry) => [entry.rel, entry.dir, entry.pathId, entry.name]),
          ...primary.variants.map((variant) => variant.variantLabel),
        ].join(" ").toLowerCase();
      }
      deduped.push(primary);
    }

    return deduped;
  }

  function groupAssetEntries(entries, rawEntryByRel = new Map()) {
    const groupedEntries = [];
    const entryByRel = new Map();
    const assetGroups = new Map();

    for (const entry of entries) {
      if (!entry.grouped) {
        groupedEntries.push(entry);
        for (const rel of entry.rawRels || [entry.rel]) {
          entryByRel.set(rel, entry);
        }
        continue;
      }

      const scopeDir = entry.variantScope || entry.dir;
      const key = `${entry.kind}::${entry.ext}::${scopeDir.toLowerCase()}::${entry.family.toLowerCase()}::${entry.noDrawableFaces ? "empty" : "geometry"}`;
      let group = assetGroups.get(key);
      if (!group) {
        group = {
          kind: entry.kind,
          noDrawableFaces: entry.noDrawableFaces,
          collision: entry.collision,
          rel: entry.rel,
          size: 0,
          name: `${entry.family}.${entry.ext}`,
          dir: scopeDir,
          variantScope: scopeDir,
          source: entry.source,
          ext: entry.ext,
          stem: entry.family,
          family: entry.family,
          familyKey: entry.familyKey,
          groupKey: entry.groupKey,
          groupLabel: entry.groupLabel,
          groupRaw: entry.groupRaw,
          lod: null,
          imageCategory: "other",
          imageExtraCategories: [],
          materialLike: false,
          modelCategories: [],
          variantCount: 0,
          duplicateCount: 0,
          contentHash: "",
          variantSummary: "",
          searchText: "",
          rawRels: [],
          variants: [],
        };
        assetGroups.set(key, group);
      }
      if (Array.isArray(entry.variants) && entry.variants.length) {
        if (entry.fbxPoseVariants) group.fbxPoseVariants = true;
        for (const variant of entry.variants) {
          group.variants.push({
            ...variant,
            grouped: true,
            family: entry.family,
            familyKey: entry.familyKey,
            groupKey: entry.groupKey,
            groupLabel: entry.groupLabel,
            groupRaw: entry.groupRaw,
          });
        }
      } else {
        group.variants.push(entry);
      }
    }

    for (const group of assetGroups.values()) {
      if (group.ext === "fbx" && group.variants.length === 1) {
        const entry = { ...group.variants[0], grouped: false };
        groupedEntries.push(entry);
        for (const rel of entry.rawRels) entryByRel.set(rel, entry);
        continue;
      }
      group.variants.sort(compareVariants);
      group.rel = group.variants[0].rel;
      group.size = group.variants.reduce((sum, variant) => sum + variant.size, 0);
      group.imageCategory = group.kind === "image" ? chooseImageCategory(group.variants) : "";
      group.imageExtraCategories = group.kind === "image" ? chooseImageExtraCategories(group.variants) : [];
      group.materialLike = group.kind === "image" && group.variants.some((variant) => variant.materialLike);
      group.modelCategories = group.kind === "model" ? chooseModelCategories(group.variants) : [];
      group.variantCount = group.variants.length;
      group.rawRels = group.variants.flatMap((variant) => variant.rawRels || [variant.rel]);
      if (group.fbxPoseVariants) {
        group.resourceFiles = group.rawRels;
        group.resourcePaths = Array.from(new Set(group.variants.flatMap((variant) => variant.resourcePaths || [])));
      }
      group.duplicateCount = group.rawRels.length;
      group.variantSummary = summarizeVariantLabels(group.variants);
      group.searchText = [
        group.name,
        group.dir,
        group.source,
        group.groupKey,
        group.groupLabel,
        group.groupRaw,
        group.family,
        group.imageCategory,
        ...(group.imageExtraCategories || []),
        ...(group.modelCategories || []),
        group.materialLike ? "material material-like texture engine" : "",
        ...group.variants.map((variant) => variant.searchText),
      ].join(" ").toLowerCase();
      groupedEntries.push(group);
      for (const rel of group.rawRels) {
        entryByRel.set(rel, group);
      }
    }

    return {
      entries: groupedEntries,
      entryByRel,
      rawEntryByRel,
    };
  }

  function compareVariants(a, b) {
    const aIsBase = a.lod === null && a.stem.toLowerCase() === a.family.toLowerCase();
    const bIsBase = b.lod === null && b.stem.toLowerCase() === b.family.toLowerCase();
    if (aIsBase !== bIsBase) return aIsBase ? -1 : 1;
    const lodA = a.lod === null ? Number.POSITIVE_INFINITY : a.lod;
    const lodB = b.lod === null ? Number.POSITIVE_INFINITY : b.lod;
    return (lodA - lodB) || a.variantLabel.localeCompare(b.variantLabel) || a.rel.localeCompare(b.rel);
  }

  function summarizeVariantLabels(variants) {
    const labels = variants.map((variant) => {
      return variant.variantLabel || variant.name;
    });
    return labels.join(", ");
  }

  function hasHiddenDuplicateFiles(entry) {
    if (!entry) return false;
    const visibleCount = Array.isArray(entry.variants) ? entry.variants.length : 1;
    return Number(entry.duplicateCount || visibleCount) > visibleCount;
  }

  function deriveAssetGroupInfo(kind = "", stem = "", ext = "") {
    const modelGroup = deriveModelGroupInfo(kind, stem, ext);
    if (modelGroup) return modelGroup;

    const originalStem = assetGroupStem(kind, stem).trim();
    const groupStem = stripSharedAssetPrefix(originalStem);
    if (!groupStem) {
      return { key: "(root)", label: "(root)", raw: "" };
    }
    return {
      key: groupStem.toLowerCase(),
      label: groupStem,
      raw: originalStem && originalStem !== groupStem ? originalStem : "",
    };
  }

  function seedAssetExpansions() {
    if (ASSET_STATE.expanded.size) return;
    const sources = Array.from(new Set(ASSET_STATE.entries.map((entry) => entry.source).filter(Boolean)));
    for (const source of sources) {
      ASSET_STATE.expanded.add(source);
    }
  }

  function syncFilterSectionActiveCounts() {
    window.WebUI.setFilterSectionActiveCounts?.({
      "asset-basic": (ASSET_STATE.filters.q ? 1 : 0) + (ASSET_STATE.filters.sort === "path" ? 0 : 1),
    });
  }

  function renderEmptyModelTag() {
    window.WebUI.filters.buildChips("#asset-empty-model-filter", [{
      value: "empty-models",
      label: assetUiText("emptyModelTag"),
      count: ASSET_STATE.entries.filter((entry) => entry.noDrawableFaces).length,
    }, {
      value: "collision", label: assetUiText("collisionTag"),
      count: ASSET_STATE.entries.filter((entry) => entry.collision).length,
    }], {
      active: new Set([
        ...(ASSET_STATE.filters.showEmptyModels ? ["empty-models"] : []),
        ...(ASSET_STATE.filters.showCollision ? ["collision"] : []),
      ]),
      className: "asset-filter-chip",
      title: (value) => value === "collision" && ASSET_STATE.collisionStatus?.diagnostic
        ? assetUiText("collisionUnavailable", { reason: ASSET_STATE.collisionStatus.diagnostic })
        : value === "collision" && ASSET_STATE.collisionStatus?.runtime?.status === "unavailable" && ASSET_STATE.collisionStatus.runtime.diagnostic
          ? assetUiText("collisionRuntimeUnavailable", { reason: ASSET_STATE.collisionStatus.runtime.diagnostic })
        : value === "collision" && ASSET_STATE.collisionStatus?.authored?.status === "unavailable" && ASSET_STATE.collisionStatus.authored.diagnostic
          ? assetUiText("collisionAuthoredUnavailable", { reason: ASSET_STATE.collisionStatus.authored.diagnostic })
        : value === "collision" && ASSET_STATE.collisionStatus?.authored?.models?.status === "unavailable"
          ? assetUiText("collisionModelUnavailable", { reason: ASSET_STATE.collisionStatus.authored.models.diagnostic })
        : value === "collision" && ASSET_STATE.collisionStatus?.authored?.prefabs?.status === "unavailable"
          ? assetUiText("collisionPrefabUnavailable", { reason: ASSET_STATE.collisionStatus.authored.prefabs.diagnostic })
        : value === "collision" && ASSET_STATE.collisionStatus?.authored?.boxes?.status === "unavailable"
          ? assetUiText("collisionBoxUnavailable", { reason: ASSET_STATE.collisionStatus.authored.boxes.diagnostic })
        : value === "collision" && ASSET_STATE.collisionStatus?.authored?.renderers?.status === "unavailable"
          ? assetUiText("collisionRendererUnavailable", { reason: ASSET_STATE.collisionStatus.authored.renderers.diagnostic })
        : assetUiText(value === "collision" ? "collisionHint" : "emptyModelHint"),
      onToggle: (value, { on }) => {
        ASSET_STATE.filters[value === "collision" ? "showCollision" : "showEmptyModels"] = on;
        applyAssetFilters();
      },
    });
  }

  function applyAssetFilters() {
    renderEmptyModelTag();
    syncFilterSectionActiveCounts();
    const filters = ASSET_STATE.filters;
    const tokens = window.WebUI.parseQuery(filters.q);
    const scores = new Map();

    // With no chip active the facet pass keeps every entry, so skip it.
    const visibleEntries = ASSET_STATE.entries.filter((entry) =>
      (filters.showEmptyModels || !entry.noDrawableFaces) && (filters.showCollision || !entry.collision));
    const faceted = ASSET_STATE.facets.isFiltered() ? ASSET_STATE.facets.filter(visibleEntries) : visibleEntries;
    ASSET_STATE.filtered = !tokens.length ? faceted.slice() : faceted.filter((entry) => {
      const score = window.WebUI.queryScore(entry.searchText, tokens);
      if (score > 0) scores.set(entry, score);
      return score > 0;
    });

    ASSET_STATE.searchTokens = tokens;
    ASSET_STATE.searchScores = tokens.length ? scores : null;
    const byOrder = window.WebUI.sorting.comparator("asset-sort", (a, b) => compareAssets(a, b, filters.sort));
    // A multi-word query ranks every match before virtual rendering.
    ASSET_STATE.filtered.sort(tokens.length > 1
      ? (a, b) => ((scores.get(b) || 0) - (scores.get(a) || 0)) || byOrder(a, b)
      : byOrder);
    $("#asset-shown").textContent = ASSET_STATE.filtered.length.toLocaleString();
    $("#asset-total").textContent = ASSET_STATE.entries.length.toLocaleString();
    rebuildAssetTree();
  }

  function compareAssets(a, b, sort) {
    if (sort === "size-desc") {
      return (b.size - a.size) || a.rel.localeCompare(b.rel);
    }
    if (sort === "size-asc") {
      return (a.size - b.size) || a.rel.localeCompare(b.rel);
    }
    if (sort === "name") {
      return a.name.localeCompare(b.name) || a.rel.localeCompare(b.rel);
    }
    return a.rel.localeCompare(b.rel);
  }

  function naturalCompare(a, b) {
    const ax = String(a || "").match(/(\D+|\d+)/g) || [];
    const bx = String(b || "").match(/(\D+|\d+)/g) || [];
    for (let index = 0; index < Math.max(ax.length, bx.length); index += 1) {
      const ai = ax[index];
      const bi = bx[index];
      if (ai === undefined) return -1;
      if (bi === undefined) return 1;
      const an = Number(ai);
      const bn = Number(bi);
      if (!Number.isNaN(an) && !Number.isNaN(bn)) {
        if (an !== bn) return an - bn;
      } else if (ai !== bi) {
        return ai < bi ? -1 : 1;
      }
    }
    return 0;
  }

  function sumAssetLeaves(node) {
    let count = 0;
    for (const group of Object.values(node)) {
      count += (group && Array.isArray(group.items)) ? group.items.length : 0;
    }
    return count;
  }

  function rebuildAssetTree({ resetScroll = true } = {}) {
    // Multi-word query: skip the source tree and show a flat list ranked by how
    // many keywords each asset matched.
    if ((ASSET_STATE.searchTokens || []).length > 1) {
      rebuildFlatAssetSearch({ resetScroll });
      return;
    }

    const tree = {};
    const filteredEntries = ASSET_STATE.filtered;
    for (const entry of filteredEntries) {
      const source = entry.source || assetUiText("rootFolder");
      (tree[source] ??= {});
      const bucket = (tree[source][entry.groupKey] ??= {
        label: entry.groupLabel || assetUiText("rootFolder"),
        raw: entry.groupRaw || "",
        items: [],
      });
      bucket.items.push(entry);
    }

    const rows = [];
    let offset = 0;
    const autoExpand = !!ASSET_STATE.filters.q;

    const pushGroup = (level, path, label, count, raw = "") => {
      const expanded = autoExpand || ASSET_STATE.expanded.has(path);
      rows.push({
        type: "group",
        level,
        path,
        label,
        count,
        raw,
        top: offset,
        h: ASSET_GROUP_ROW_H,
        expanded,
      });
      offset += ASSET_GROUP_ROW_H;
      return expanded;
    };

    const pushItem = (entry, level = 2) => {
      rows.push({
        type: "item",
        level,
        entry,
        top: offset,
        h: ASSET_ITEM_ROW_H,
      });
      offset += ASSET_ITEM_ROW_H;
    };

    const sources = Object.keys(tree).sort(naturalCompare);
    for (const source of sources) {
      const sourcePath = source;
      if (!pushGroup(0, sourcePath, source, sumAssetLeaves(tree[source]))) continue;

      const groups = Object.keys(tree[source]).sort(naturalCompare);
      for (const groupKey of groups) {
        const group = tree[source][groupKey];
        if (group.items.length <= 1) {
          for (const entry of group.items) {
            pushItem(entry, 1);
          }
          continue;
        }

        const groupPath = `${source}/${groupKey}`;
        if (!pushGroup(1, groupPath, group.label, group.items.length, group.raw)) continue;
        for (const entry of group.items) {
          pushItem(entry, 2);
        }
      }
    }

    ASSET_STATE.rows = rows;
    ASSET_STATE.totalH = offset;
    $("#asset-list-spacer").style.height = `${offset}px`;
    if (resetScroll) $("#asset-list-wrap").scrollTop = 0;
    renderAssetList();
  }

  function rebuildFlatAssetSearch({ resetScroll = true } = {}) {
    // applyAssetFilters already ordered the matches by score, then sort order.
    const items = ASSET_STATE.filtered;

    const rows = [];
    let offset = 0;
    for (const entry of items) {
      rows.push({ type: "item", level: 0, entry, top: offset, h: ASSET_ITEM_ROW_H });
      offset += ASSET_ITEM_ROW_H;
    }

    ASSET_STATE.rows = rows;
    ASSET_STATE.totalH = offset;
    $("#asset-list-spacer").style.height = `${offset}px`;
    if (resetScroll) $("#asset-list-wrap").scrollTop = 0;
    renderAssetList();
  }

  function findFirstVisibleAssetRow(scrollTop) {
    const rows = ASSET_STATE.rows;
    let lo = 0;
    let hi = rows.length - 1;
    let answer = 0;
    while (lo <= hi) {
      const mid = (lo + hi) >> 1;
      if (rows[mid].top + rows[mid].h <= scrollTop) {
        lo = mid + 1;
      } else {
        answer = mid;
        hi = mid - 1;
      }
    }
    return answer;
  }

  function renderAssetList() {
    const wrap = $("#asset-list-wrap");
    const spacer = $("#asset-list-spacer");
    const list = $("#asset-list");
    if (!wrap || !spacer || !list) return;

    const total = ASSET_STATE.rows.length;
    spacer.style.height = `${ASSET_STATE.totalH}px`;
    if (!total) {
      const message = document.createElement("div");
      message.className = "asset-list-empty";
      message.setAttribute("role", "status");
      message.textContent = assetUiText("noMatchingAssets");
      list.replaceChildren(message);
      return;
    }

    const viewportHeight = wrap.clientHeight || 0;
    const scrollTop = wrap.scrollTop || 0;
    const startTop = Math.max(0, scrollTop - ASSET_OVERSCAN_PX);
    const endTop = scrollTop + viewportHeight + ASSET_OVERSCAN_PX;

    const fragment = document.createDocumentFragment();
    let index = findFirstVisibleAssetRow(startTop);
    while (index < total && ASSET_STATE.rows[index].top < endTop) {
      fragment.appendChild(renderAssetRow(ASSET_STATE.rows[index]));
      index += 1;
    }
    list.replaceChildren(fragment);
  }

  function renderAssetRow(row) {
    if (row.type === "group") return renderAssetGroupRow(row);
    return renderAssetItemRow(row);
  }

  function renderAssetGroupRow(row) {
    const div = document.createElement("div");
    div.className = `row group lvl-${row.level} asset-group-row` + (row.expanded ? " expanded" : "");
    div.dataset.path = row.path;
    div.style.top = `${row.top}px`;
    div.style.height = `${row.h}px`;
    div.style.paddingLeft = `${8 + row.level * 14}px`;
    const twisty = row.expanded ? "v" : ">";
    const label = row.label === "(root)" ? assetUiText("rootFolder") : row.label;
    div.innerHTML =
      `<span class="twisty">${twisty}</span>` +
      `<span class="group-main">` +
        `<span class="label" title="${escapeHtml(label)}">${escapeHtml(label)}</span>` +
        (row.raw ? `<span class="sub mono" title="${escapeHtml(row.raw)}">${escapeHtml(row.raw)}</span>` : "") +
      `</span>` +
      `<span class="group-count">${row.count}</span>`;
    return div;
  }

  function renderAssetItemRow(row) {
    const entry = row.entry;
    const div = document.createElement("div");
    div.className = "row asset-item-row";
    if (ASSET_STATE.selectedRel === entry.rel) div.classList.add("is-selected");
    div.dataset.rel = entry.rel;
    div.style.top = `${row.top}px`;
    div.style.height = `${row.h}px`;
    div.style.paddingLeft = `${8 + (row.level ?? 2) * 14}px`;

    const line1 = document.createElement("div");
    line1.className = "asset-row-line1";

    const badge = document.createElement("span");
    badge.className = `asset-badge ${assetBadgeClass(entry.kind)}`;
    badge.textContent = assetTypeLabel(entry.ext || entry.kind);
    line1.appendChild(badge);

    const name = document.createElement("div");
    name.className = "asset-row-name";
    name.textContent = entry.name;
    name.insertAdjacentHTML("beforeend", window.WebUI.updateBadges.fileHtml(assetFilePaths(entry)));
    line1.appendChild(name);

    const size = document.createElement("div");
    size.className = "asset-row-size";
    size.textContent = formatAssetSize(entry);
    line1.appendChild(size);

    const line2 = document.createElement("div");
    line2.className = "asset-row-line2";

    const dir = document.createElement("div");
    dir.className = "asset-row-dir";
    dir.textContent = entry.container || entry.dir || assetUiText("rootFolder");
    line2.appendChild(dir);

    const extra = document.createElement("div");
    extra.className = "asset-row-extra";
    if (Array.isArray(entry.variants)) {
      extra.textContent = [
        entry.source,
        formatAssetCategoryMeta(entry),
        assetUiText("variantsCount", { count: entry.variantCount }),
        hasHiddenDuplicateFiles(entry) ? assetUiText("copiesCount", { count: entry.duplicateCount }) : "",
      ]
        .filter(Boolean)
        .join(" / ");
    } else {
      extra.textContent = [
        entry.source,
        formatAssetCategoryMeta(entry),
        hasHiddenDuplicateFiles(entry) ? assetUiText("copiesCount", { count: entry.duplicateCount }) : "",
        entry.lod === null ? "" : `LOD ${entry.lod}`,
      ]
        .filter(Boolean)
        .join(" / ");
    }
    line2.appendChild(extra);

    div.appendChild(line1);
    div.appendChild(line2);
    return div;
  }

  function selectAsset(entry, { scrollIntoView = true, updateUrl = true, variantRel = "" } = {}) {
    ASSET_STATE.selectedRel = entry.rel;
    ASSET_STATE.selectedEntry = entry;
    ASSET_STATE.selectedVariantRel = resolveInitialVariantRel(entry, variantRel);
    expandAssetEntryPaths(entry);
    renderAssetList();
    if (scrollIntoView) scrollSelectedAssetIntoView(entry);
    if (updateUrl) updateUrlForSelectedAsset(getSelectedAssetRelForUrl());
    renderSelectedAsset();
  }

  function assetEntryTreePaths(entry) {
    if (!entry) return [];
    const source = entry.source || assetUiText("rootFolder");
    return [source, `${source}/${entry.groupKey}`];
  }

  function expandAssetEntryPaths(entry) {
    let changed = false;
    for (const path of assetEntryTreePaths(entry)) {
      if (!ASSET_STATE.expanded.has(path)) {
        ASSET_STATE.expanded.add(path);
        changed = true;
      }
    }
    if (changed) rebuildAssetTree({ resetScroll: false });
  }

  function toggleAssetPath(path) {
    const wrap = $("#asset-list-wrap");
    const prevScroll = wrap.scrollTop;
    if (ASSET_STATE.expanded.has(path)) ASSET_STATE.expanded.delete(path);
    else ASSET_STATE.expanded.add(path);
    rebuildAssetTree({ resetScroll: false });
    wrap.scrollTop = Math.min(prevScroll, ASSET_STATE.totalH);
    renderAssetList();
  }

  function applyInitialAssetSelection() {
    if (ASSET_STATE.initialAssetHandled) return;
    ASSET_STATE.initialAssetHandled = true;

    const rel = getAssetRelFromQuery();
    if (!rel) return;
    const entry = ASSET_STATE.entryByRel.get(rel);
    if (!entry) return;
    selectAsset(entry, { scrollIntoView: true, updateUrl: false, variantRel: rel });
  }

  function getAssetRelFromQuery() {
    const params = new URLSearchParams(window.location.search);
    return params.get("asset") || "";
  }

  function updateUrlForSelectedAsset(rel) {
    const url = new URL(window.location.href);
    if (rel) url.searchParams.set("asset", rel);
    else url.searchParams.delete("asset");
    if (ASSET_STATE.activeView === "assets") url.hash = "#assets";
    history.replaceState(null, "", `${url.pathname}${url.search}${url.hash}`);
  }

  function resolveInitialVariantRel(entry, requestedRel = "") {
    if (!entry || !Array.isArray(entry.variants)) return null;
    const findVariant = (rel) => rel && entry.variants.find((variant) => variant.rel === rel || variant.rawRels?.includes(rel));
    const requested = findVariant(requestedRel);
    if (requested) return requested.rel;
    const selected = findVariant(ASSET_STATE.selectedVariantRel);
    if (selected) return selected.rel;
    return entry.variants[0]?.rel || null;
  }

  function isVariantGroup(entry) {
    return !!(entry && Array.isArray(entry.variants) && entry.variants.length);
  }

  function getActiveVariant(entry = ASSET_STATE.selectedEntry) {
    if (!isVariantGroup(entry)) return null;
    return entry.variants.find((variant) => variant.rel === ASSET_STATE.selectedVariantRel) || entry.variants[0] || null;
  }

  function getActiveAssetFile(entry = ASSET_STATE.selectedEntry) {
    if (!entry) return null;
    if (isVariantGroup(entry)) return getActiveVariant(entry);
    return entry;
  }

  function getActiveModelFile(entry = ASSET_STATE.selectedEntry) {
    if (!entry || entry.kind !== "model") return null;
    if (isVariantGroup(entry)) return getActiveVariant(entry);
    return entry;
  }

  function getSelectedAssetRelForUrl() {
    const entry = ASSET_STATE.selectedEntry;
    if (!entry) return "";
    return getActiveAssetFile(entry)?.rel || entry.rel;
  }

  function scrollSelectedAssetIntoView(entry) {
    const wrap = $("#asset-list-wrap");
    if (!wrap) return;

    const row = ASSET_STATE.rows.find((candidate) => candidate.type === "item" && candidate.entry.rel === entry.rel);
    if (!row) return;

    const top = row.top;
    const bottom = row.top + row.h;
    if (top < wrap.scrollTop) {
      wrap.scrollTop = top;
    } else if (bottom > wrap.scrollTop + wrap.clientHeight) {
      wrap.scrollTop = bottom - wrap.clientHeight;
    }
  }

  function locateSelectedAsset() {
    const entry = ASSET_STATE.selectedEntry;
    if (!entry) return null;
    expandAssetEntryPaths(entry);
    renderAssetList();
    scrollSelectedAssetIntoView(entry);
    if (isMobileLayout()) $("#asset-left")?.scrollIntoView({ block: "start", behavior: "smooth" });
    return null;
  }

  function renderSelectedAsset() {
    window.WebUI.locateCurrent?.sync($("#asset-locate-current"), Boolean(ASSET_STATE.selectedEntry));
    const entry = ASSET_STATE.selectedEntry;
    if (!entry) {
      $("#asset-empty").hidden = false;
      $("#asset-detail").hidden = true;
      return;
    }

    $("#asset-empty").hidden = true;
    $("#asset-detail").hidden = false;
    const activeVariant = getActiveAssetFile(entry);
    $("#asset-detail-title").textContent = entry.name;
    $("#asset-detail-title").insertAdjacentHTML("beforeend", window.WebUI.updateBadges.fileHtml(assetFilePaths(activeVariant || entry)));
    $("#asset-detail-meta").textContent = activeVariant ? activeVariant.rel : entry.rel;
    $("#asset-open-raw").href = assetHref(activeVariant ? activeVariant.rel : entry.rel);
    renderCurrentFileDownload(entry);
    renderFacts(entry);
    renderRelated(entry);
    renderVariants(entry);
    renderRelations(entry);
    // The change record sits in the inspector beside the facts it describes;
    // the title badge covers this file, so only other linked files are marked.
    const detail = $("#asset-detail");
    detail.querySelectorAll(".version-update-files").forEach((node) => node.remove());
    $("#asset-inspector-label").insertAdjacentHTML("afterend", window.WebUI.updateBadges.fileDetails(activeVariant || entry));
    ASSET_STATE.detailToken += 1;
    resetAssetPreviewSurface();
    renderModelObjectToggles(null);
    window.WebUI.updateBadges.decorateFiles(detail, { exclude: activeVariant || entry });
    syncPreviewBackgroundControls(entry);

    if (entry.kind === "image") {
      renderImagePreview(activeVariant || entry);
    } else if (entry.kind === "model") {
      renderModelPreview(entry);
    } else if (entry.kind === "video") {
      renderVideoPreview(activeVariant || entry);
    } else {
      renderFilePreview(activeVariant || entry);
    }
  }

  function formatAssetKindValue(entry, activeVariant = null) {
    const file = activeVariant || entry;
    const type = assetTypeLabel(file?.ext || entry.ext || entry.kind);
    return `${type} / ${assetKindLabel(entry.kind)}`;
  }

  function renderCurrentFileDownload(entry) {
    const link = $("#asset-download-current");
    if (!link) return;

    const activeFile = getActiveAssetFile(entry);
    const rel = activeFile?.rel || entry?.rel || "";
    if (!rel) {
      link.hidden = true;
      link.removeAttribute("href");
      link.removeAttribute("download");
      link.removeAttribute("title");
      return;
    }

    link.hidden = false;
    link.href = assetHref(rel);
    link.download = rel.split("/").pop() || "";
    link.title = rel;
    link.textContent = assetUiText("downloadCurrentFile");
  }

  // Exact table ownership only: the sidecar is keyed by the same normalized
  // stem the index carries, so a lookup either hits an exported row that names
  // this asset or the asset stays unowned. No prefix or family fallback.
  function assetTableOwnerSummary(entry) {
    if (entry?.collision) return "";
    const stem = String(entry?.stem || entry?.rawStem || "");
    const record = stem ? ASSET_STATE.tableOwners[stem] : null;
    const owners = (record && record.owners) || [];
    if (!owners.length) return "";
    const shown = owners.map((owner) => `${owner.table} / ${owner.row} (${owner.field})`);
    const total = Number(record.ownerCount || owners.length);
    return total > owners.length
      ? `${shown.join("; ")} ... +${total - owners.length}`
      : shown.join("; ");
  }

  function renderFacts(entry) {
    const activeVariant = getActiveAssetFile(entry);
    const facts = [
      [assetUiText("factKind"), formatAssetKindValue(entry, activeVariant)],
      [assetUiText("factSource"), entry.source || assetUiText("none")],
      [assetUiText("factFolder"), entry.groupLabel || entry.groupRaw || (entry.groupKey === "(root)" ? assetUiText("rootFolder") : entry.groupKey)],
      [assetUiText("factSize"), formatAssetSize(entry)],
    ];
    if (entry.cropOf) facts.push([assetUiText("factCropOf"), entry.cropOf]);
    const activeFile = activeVariant || entry;
    const resourcePaths = (entry.fbxPoseVariants ? entry.resourcePaths : activeFile.resourcePaths) || [];
    if (resourcePaths.length) {
      facts.push([assetUiText(resourcePaths.length > 1 ? "factAssetPaths" : "factAssetPath"), resourcePaths.join("\n")]);
    }
    const resourceFiles = entry.fbxPoseVariants ? entry.resourceFiles : activeFile.resourceFiles;
    if (resourceFiles?.length > 1) {
      facts.push([assetUiText("factResourceFiles"), resourceFiles.join("\n")]);
    }
    if (activeFile.noDrawableFaces) facts.push([assetUiText("geometry"), assetUiText("emptyModelTag")]);
    if (activeFile.modelRecovery) facts.push([
      assetUiText("modelRecovery"), assetUiText("modelRecoveryGap", activeFile.modelRecovery),
    ]);
    if (activeFile.collision) {
      const collision = activeFile.collision;
      const identity = collision.identity;
      facts.push([assetUiText("geometry"), assetUiText(collision.kind === "convex" ? "collisionConvex" : "collisionTriangle")]);
      const runtime = collision.runtime;
      const evidence = [assetUiText("collisionDecoded")];
      if (runtime?.queryObserved) {
        const counts = runtime.counts;
        evidence.push(assetUiText("collisionQueryObserved", { count: counts.querySamples }));
        if (counts.movementResults) evidence.push(assetUiText("collisionMovement", { count: counts.movementResults, floor: counts.walkableFloorResults }));
        if (counts.acceptedFilterCandidates) evidence.push(assetUiText("collisionFilter", { count: counts.acceptedFilterCandidates }));
        if (counts.conditionalSurfaceSamples) evidence.push(assetUiText("collisionSurface", { count: counts.conditionalSurfaceSamples }));
        if (counts.excludedSweepPoints) evidence.push(assetUiText("collisionExcludedPoints", { count: counts.excludedSweepPoints }));
        const arrays = [];
        if (counts.completeArraySamples) arrays.push(assetUiText("collisionArraysComplete", { count: counts.completeArraySamples }));
        if (counts.prefixArraySamples) arrays.push(assetUiText("collisionArraysPrefix", { count: counts.prefixArraySamples }));
        if (arrays.length) evidence.push(arrays.join("\n"));
      } else {
        evidence.push(assetUiText("collisionNotObserved"));
      }
      evidence.push(assetUiText("collisionSolver"));
      facts.push([assetUiText("collisionEvidence"), evidence.join("\n")]);
      const owners = collision.authored?.owners || [];
      if (owners.length) {
        const prefabs = [...new Set(owners.flatMap((owner) => owner.prefabPaths))];
        if (prefabs.length) facts.push([assetUiText("collisionAuthoredOwners"), prefabs.join("\n")]);
        facts.push([assetUiText("collisionAuthoredHierarchy"), owners.map((owner) =>
          `${owner.hierarchy.map((node) => node.name).join(" / ")}\n${assetUiText("collisionAuthoredFlags", {
            enabled: assetUiText(owner.enabled ? "collisionAuthoredYes" : "collisionAuthoredNo"),
            active: assetUiText(owner.hierarchy.every((node) => node.active) ? "collisionAuthoredYes" : "collisionAuthoredNo"),
          })}`).join("\n\n") + `\n\n${assetUiText("collisionAuthoredBoundary")}`]);
      }
      const modelRecords = collision.models?.records || [];
      if (collision.prefabs?.assemblies?.length) {
        facts.push([assetUiText("collisionPrefabAssemblies"), ""]);
      }
      if (collision.renderers?.prefabs?.length) facts.push([assetUiText("collisionRenderers"), ""]);
      if (modelRecords.length) {
        const sources = new Map();
        for (const row of modelRecords) sources.set(JSON.stringify([row.source, row.gridOrdinal, row.ordinal, row.byteOffset]), row);
        const axes = (vector) => ["X", "Y", "Z"].map((axis) => typeof vector[axis] === "number" ? String(vector[axis]) : vector[axis].special).join(", ");
        facts.push([assetUiText("collisionModelSources"), [...sources.values()].map((row) =>
          `${row.source}\n${assetUiText("collisionModelRecord", { grid: row.uniqueId, ordinal: row.ordinal })}\n` +
          `${assetUiText("collisionModelPosition")}: [${axes(row.storedTransform.Pos)}]\n` +
          `${assetUiText("collisionModelRotation")}: [${axes(row.storedTransform.Rot)}]\n` +
          `${assetUiText("collisionModelScale")}: [${axes(row.storedTransform.Scl)}]`
        ).join("\n\n") + `\n\n${assetUiText("collisionModelBoundary")}`]);
      }
      facts.push([assetUiText("collisionIdentity"), `${identity.sourceFile} / PathID ${identity.pathId}\n${identity.sourceOriginalPath} @ ${identity.sourceOffset}`]);
      facts.push([assetUiText("collisionBuffer"), collision.bufferSha256]);
    }
    if (entry.kind === "image") {
      facts.push([assetUiText("factImageCategory"), formatAssetCategoryMeta(activeFile || entry)]);
      facts.push([
        assetUiText("factTextureRole"),
        (activeFile.materialLike || entry.materialLike)
          ? assetUiText("textureRoleMaterial")
          : assetUiText("textureRoleRegular"),
      ]);
    } else if (entry.kind === "model") {
      const modelCategories = assetCategoryValues(activeFile).length ? assetCategoryValues(activeFile) : assetCategoryValues(entry);
      if (modelCategories.length) {
        facts.push([assetUiText("factModelTags"), modelCategories.map(assetCategoryLabel).join(" / ")]);
      }
    }
    if (hasHiddenDuplicateFiles(entry)) {
      facts.push([assetUiText("factCopies"), String(entry.duplicateCount)]);
    }
    const activeHash = assetContentHash(activeFile);
    const sameHashRels = assetSameHashRels(activeFile);
    if (activeHash) facts.push([assetUiText("factHash"), activeHash]);
    if (sameHashRels.length > 1) facts.push([assetUiText("factSameHashFiles"), formatAssetRelSummary(sameHashRels)]);
    if (isVariantGroup(entry)) {
      facts.push([assetUiText("factLodVariants"), String(entry.variantCount)]);
      if (entry.fbxPoseVariants) facts.push([assetUiText("factVariantDifferences"), assetUiText("fbxPoseDifferences")]);
      facts.push([assetUiText("factSelectedRawFile"), activeVariant ? activeVariant.rel : entry.rel]);
      facts.push([assetUiText("factLodSet"), entry.variantSummary || assetUiText("none")]);
    }
    facts.push([assetUiText("factRelativePath"), activeVariant ? activeVariant.rel : entry.rel]);
    if (activeVariant?.previewRel && activeVariant.previewRel !== activeVariant.rel) {
      facts.push([assetUiText("factPreviewProxy"), activeVariant.previewRel]);
    }
    if ((activeVariant || entry).lod !== null) facts.push([assetUiText("factLod"), String((activeVariant || entry).lod)]);
    if (entry.family && entry.family !== entry.stem) facts.push([assetUiText("factFamily"), entry.family]);
    const tableOwnerSummary = assetTableOwnerSummary(entry);
    if (tableOwnerSummary) facts.push([assetUiText("factTableOwner"), tableOwnerSummary]);

    const wrap = $("#asset-facts");
    const fragment = document.createDocumentFragment();
    for (const [label, value] of facts) {
      const item = document.createElement("div");
      item.className = "asset-fact";

      const factLabel = document.createElement("div");
      factLabel.className = "asset-fact-label";
      factLabel.textContent = label;
      item.appendChild(factLabel);

      const factValue = document.createElement("div");
      factValue.className = "asset-fact-value";
      if (String(value).includes("\n")) factValue.classList.add("asset-fact-multiline");
      if (label === assetUiText("factResourceFiles")) {
        for (const [index, rel] of resourceFiles.entries()) {
          if (index) factValue.appendChild(document.createTextNode("\n"));
          const link = document.createElement("a");
          link.href = assetHref(rel);
          link.download = rel.split("/").pop();
          link.textContent = rel;
          factValue.appendChild(link);
        }
      } else if (label === assetUiText("collisionPrefabAssemblies")) {
        for (const assembly of activeFile.collision.prefabs.assemblies) {
          const block = document.createElement("div");
          block.className = "asset-fact-multiline";
          block.textContent = assembly.prefabPaths.join("\n") + "\n" + assetUiText("collisionPrefabSummary", {
            count: assembly.colliderCount, disabled: assembly.storedDisabledCount,
            inactive: assembly.storedInactiveCount, missing: assembly.selectedMissingCount,
            meshes: assembly.meshColliderCount ?? assembly.colliderCount, boxes: assembly.boxColliderCount ?? 0,
          }) + "\n";
          for (const box of assembly.boxParts || []) {
            block.appendChild(document.createTextNode(box.hierarchy.map((n) => n.name).join(" / ") + "\n" +
              assetUiText("collisionBoxPart", {size:box.size.join(", "), center:box.center.join(", "),
                trigger:assetUiText(box.isTrigger ? "collisionAuthoredYes" : "collisionAuthoredNo")}) + "\n"));
          }
          const preview = document.createElement("button");
          preview.type = "button";
          preview.className = "asset-variant-chip";
          preview.textContent = assetUiText("collisionPrefabPreview");
          preview.addEventListener("click", () => renderCollisionAssemblyPreview(assembly));
          const download = document.createElement("a");
          download.href = assetHref(assembly.rel);
          download.download = assembly.rel.split("/").pop();
          download.textContent = assetUiText("collisionPrefabDownload");
          block.append(preview, document.createTextNode(" "), download);
          factValue.appendChild(block);
        }
        const reset = document.createElement("button");
        reset.type = "button";
        reset.className = "asset-variant-chip";
        reset.textContent = assetUiText("collisionPrefabReset");
        reset.addEventListener("click", () => renderModelPreview(entry));
        factValue.append(reset, document.createTextNode("\n" + assetUiText("collisionPrefabBoundary")));
      } else if (label === assetUiText("collisionRenderers")) {
        item.classList.add("asset-fact-renderer");
        const statusKeys = {exact_selected_target_identity:"collisionRendererExact", external_slot_unwitnessed:"collisionRendererUnwitnessed",
          external_target_outside_selection:"collisionRendererExternal", target_body_outside_selection:"collisionRendererExcluded",
          external_physical_target_ambiguous:"collisionRendererAmbiguous", mesh_filter_unavailable:"collisionRendererNoFilter", null:"collisionRendererNull",
          external_directory_unavailable:"collisionRenderDirectoryMissing", target_absent_from_complete_directory:"collisionRenderAbsent",
          exact_directory_target_body_unselected:"collisionRenderBodyUnselected"};
        const describe = (pointer) => [assetUiText(statusKeys[pointer.status] || "collisionRendererUnwitnessed"),
          pointer.target?.name || "",
          pointer.pathId !== undefined ? assetUiText("collisionRendererPointer", {file:pointer.fileId, path:pointer.pathId}) : "",
          pointer.target?.identity?.sourceFile || pointer.expectedCab || ""].filter(Boolean).join(" · ");
        for (const prefab of activeFile.collision.renderers.prefabs) {
          const block = document.createElement("div");
          block.className = "asset-fact-multiline";
          block.textContent = prefab.prefabPaths.join("\n") + "\n" + assetUiText("collisionRendererSummary", {
            count:prefab.records.length, meshes:prefab.records.filter((r) => r.mesh.status === "exact_selected_target_identity").length,
            slots:prefab.records.reduce((total, r) => total + r.materials.length, 0),
          }) + "\n";
          for (const assembly of prefab.renderAssemblies || []) {
            const preview = document.createElement("button"); preview.type = "button"; preview.className = "asset-variant-chip";
            preview.textContent = assetUiText(assembly.lodOrdinal === null ? "collisionRenderUngrouped" : "collisionRenderLOD", {lod:assembly.lodOrdinal});
            preview.addEventListener("click", () => renderDecodedObjPreview(assembly, "collisionRenderBoundary", "collisionRendererUnavailable"));
            const download = document.createElement("a"); download.href = assetHref(assembly.rel); download.download = assembly.rel.split("/").pop();
            download.textContent = assetUiText("collisionRenderDownload");
            block.append(preview, document.createTextNode(" "), download, document.createTextNode("\n" + assetUiText("collisionRenderMissing", {
              count:assembly.rendererCount, missing:assembly.selectedMissingCount}) + "\n"));
          }
          for (const renderer of prefab.records) {
            const details = document.createElement("details");
            const summary = document.createElement("summary");
            summary.textContent = assetUiText("collisionRendererRecord", {hierarchy:renderer.hierarchy.map((n) => n.name).join(" / "),
              slots:renderer.materials.length, enabled:assetUiText(renderer.enabled ? "collisionAuthoredYes" : "collisionAuthoredNo")});
            const refs = document.createElement("div");
            refs.textContent = [assetUiText("collisionRendererMesh") + ": " + describe(renderer.mesh),
              ...(renderer.lodMemberships || []).map((m) => assetUiText("collisionRenderMembership", {lod:m.ordinal, height:m.screenRelativeHeight})),
              ...renderer.materials.map((p, i) => assetUiText("collisionRendererSlot", {slot:i}) + ": " + describe(p))].join("\n");
            if (renderer.mesh.target?.asset) {
              const preview = document.createElement("button"); preview.type = "button"; preview.className = "asset-variant-chip";
              preview.textContent = assetUiText("collisionRenderPreview");
              preview.addEventListener("click", () => renderDecodedObjPreview(renderer.mesh.target.asset, "collisionRenderBoundary", "collisionRendererUnavailable"));
              refs.append(document.createTextNode("\n"), preview);
            }
            for (const [slot, material] of renderer.materials.entries()) {
              if (!material.target?.asset) continue;
              const link = document.createElement("a"); link.href = assetHref(material.target.asset.rel); link.download = material.target.asset.rel.split("/").pop();
              link.textContent = material.target.name + " · " + assetUiText("collisionRenderMaterial");
              refs.append(document.createTextNode("\n"), link);
              refs.appendChild(storedShaderDetails(material.target.asset));
              const textures = (material.target.storedTextures || []).filter((t) => t.reference.status !== "null");
              if (textures.length) {
                const textureDetails = document.createElement("details");
                const textureSummary = document.createElement("summary");
                textureSummary.textContent = assetUiText("collisionRenderTextures", {count:textures.length});
                textureDetails.appendChild(textureSummary);
                for (const texture of textures) {
                  const textureRow = document.createElement("div"); textureRow.className = "asset-stored-texture";
                  textureRow.textContent = texture.property + " · " + (texture.target?.name || texture.reference.status) + "\n" +
                    assetUiText("collisionRenderTextureUV", {uv:texture.uvSet, scale:[texture.scale.x, texture.scale.y].join(", "), offset:[texture.offset.x, texture.offset.y].join(", ")});
                  const preview = texture.target?.preview;
                  if (preview) {
                    const imageLink = document.createElement("a"); imageLink.href = assetHref(preview.rel); imageLink.target = "_blank"; imageLink.rel = "noopener";
                    const image = document.createElement("img"); image.src = imageLink.href; image.alt = texture.target.name; image.loading = "lazy";
                    image.width = Math.min(128, preview.width); image.height = Math.round(image.width * preview.height / preview.width);
                    imageLink.appendChild(image); textureRow.append(document.createTextNode("\n"), imageLink,
                      document.createTextNode("\n" + assetUiText("collisionRenderTextureInfo", {width:preview.width,height:preview.height,format:preview.format,mips:preview.mipCount,space:preview.storedColorSpace})));
                    if (renderer.mesh.target?.asset && (texture.uvSet === 0 && renderer.mesh.target.asset.hasUV0 || texture.uvSet === 1 && renderer.mesh.target.asset.hasUV1)) {
                      const channel = document.createElement("select"); channel.setAttribute("aria-label", assetUiText("collisionTextureChannel"));
                      for (const [i, name] of ["RGB", "R", "G", "B", "A"].entries()) {
                        const option = document.createElement("option"); option.value = i; option.textContent = name; channel.appendChild(option);
                      }
                      const inspect = document.createElement("button"); inspect.type = "button"; inspect.className = "asset-variant-chip";
                      inspect.textContent = assetUiText("collisionTextureInspect");
                      inspect.addEventListener("click", () => renderStoredTextureInspection({...renderer.mesh.target.asset,sourceMeshRawSha256:renderer.mesh.target.rawSha256}, texture, slot, Number(channel.value)));
                      textureRow.append(document.createTextNode("\n"), channel, inspect);
                    }
                  } else textureRow.appendChild(document.createTextNode("\n" + assetUiText("collisionRenderTextureUnavailable")));
                  textureDetails.appendChild(textureRow);
                }
                textureDetails.appendChild(document.createTextNode(assetUiText("collisionRenderTextureBoundary")));
                refs.appendChild(textureDetails);
              }
            }
            details.append(summary, refs); block.appendChild(details);
          }
          factValue.appendChild(block);
        }
        factValue.appendChild(document.createTextNode("\n" + assetUiText("collisionRendererBoundary") + "\n" + assetUiText("collisionRenderBoundary")));
      } else if (label === assetUiText("collisionModelSources")) {
        const names = new Map((activeFile.collision?.models?.records || []).filter((row) => row.dataName).map((row) => [row.source, row.dataName]));
        for (const [index, line] of String(value).split("\n").entries()) {
          if (index) factValue.appendChild(document.createTextNode("\n"));
          if (names.has(line)) {
            const link = document.createElement("a");
            link.href = window.WebUI.dataPageUrl({ store: "undecoded", group: "DynamicStreaming", name: names.get(line) });
            link.dataset.dataPageLink = "";
            link.textContent = line;
            factValue.appendChild(link);
          } else factValue.appendChild(document.createTextNode(line));
        }
      } else {
        factValue.textContent = value;
      }
      item.appendChild(factValue);

      fragment.appendChild(item);
    }
    wrap.replaceChildren(fragment);
  }

  function renderVariants(entry) {
    const outer = $("#asset-variants-wrap");
    const wrap = $("#asset-variants");
    if (!outer || !wrap) return;

    if (!isVariantGroup(entry) || entry.variants.length <= 1) {
      outer.hidden = true;
      wrap.replaceChildren();
      return;
    }

    const fragment = document.createDocumentFragment();
    for (const variant of entry.variants) {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "asset-variant-chip";
      if (variant.rel === ASSET_STATE.selectedVariantRel) button.classList.add("is-active");
      button.textContent = variant.variantLabel || variant.name;
      button.title = [
        `${variant.rel} (${formatBytes(variant.size)})`,
        ...(variant.resourcePaths || []),
        hasHiddenDuplicateFiles(variant) ? assetUiText("copiesCount", { count: variant.duplicateCount }) : "",
      ].filter(Boolean).join(" / ");
      button.addEventListener("click", () => {
        ASSET_STATE.selectedVariantRel = variant.rel;
        updateUrlForSelectedAsset(variant.rel);
        renderSelectedAsset();
      });
      fragment.appendChild(button);
    }

    wrap.replaceChildren(fragment);
    outer.hidden = false;
  }

  function renderRelated(entry) {
    const related = ASSET_STATE.entries
      .filter((item) => item.familyKey === entry.familyKey && item.rel !== entry.rel)
      .sort((a, b) => compareAssets(a, b, "path"))
      .slice(0, 12);

    const wrap = $("#asset-related");
    const outer = $("#asset-related-wrap");
    if (!related.length) {
      outer.hidden = true;
      wrap.replaceChildren();
      return;
    }

    const fragment = document.createDocumentFragment();
    for (const item of related) {
      const block = document.createElement("div");
      block.className = "asset-related-item";

      const link = document.createElement("a");
      link.href = "#assets";
      link.textContent = item.rel;
      link.addEventListener("click", (ev) => {
        ev.preventDefault();
        selectAsset(item, { scrollIntoView: true });
      });
      block.appendChild(link);

      const meta = document.createElement("div");
      meta.className = "asset-related-meta";
      meta.textContent = assetUiText("relatedMeta", {
        kind: assetTypeLabel(item.ext || item.kind),
        size: formatAssetSize(item),
      });
      block.appendChild(meta);

      fragment.appendChild(block);
    }

    wrap.replaceChildren(fragment);
    outer.hidden = false;
  }

  function renderRelations(entry) {
    ASSET_STATE.relationsEntry = entry;
    if (!ASSET_STATE.relationsLoaded) {
      ensureAssetRelations().then(() => {
        if (ASSET_STATE.relationsEntry === entry) renderRelations(entry);
      });
    }
    const relation = collectEntryRelations(entry);

    renderRelationList(
      "#asset-materials-wrap",
      "#asset-materials",
      relation.materials || [],
      renderMaterialRelationItem,
    );
    renderRelationList(
      "#asset-textures-wrap",
      "#asset-textures",
      coalesceTextureRelations(relation.textures || []),
      renderTextureRelationItem,
    );

    const references = [
      ...(relation.referencedByModels || []).map((item) => ({ ...item, kind: "model" })),
      ...(relation.referencedByMaterials || []).map((item) => ({ ...item, kind: "material" })),
    ];
    renderRelationList(
      "#asset-references-wrap",
      "#asset-references",
      coalesceReferenceRelations(references),
      renderReferenceRelationItem,
    );
  }

  function collectEntryRelations(entry) {
    if (!isVariantGroup(entry)) {
      return ASSET_STATE.relations[entry?.rel] || {};
    }

    if (entry.kind !== "model") {
      return ASSET_STATE.relations[getActiveAssetFile(entry)?.rel] || {};
    }

    const merged = {
      materials: [],
      textures: [],
      referencedByModels: [],
      referencedByMaterials: [],
    };

    for (const variant of entry.variants) {
      const relation = ASSET_STATE.relations[variant.rel] || {};
      for (const field of Object.keys(merged)) {
        for (const item of relation[field] || []) {
          if (!merged[field].some((existing) => JSON.stringify(existing) === JSON.stringify(item))) {
            merged[field].push(item);
          }
        }
      }
    }

    return merged;
  }

  function renderRelationList(outerSelector, wrapSelector, items, renderItem) {
    const outer = $(outerSelector);
    const wrap = $(wrapSelector);
    if (!outer || !wrap) return;

    if (!items || !items.length) {
      outer.hidden = true;
      wrap.replaceChildren();
      return;
    }

    const fragment = document.createDocumentFragment();
    for (const item of items) {
      fragment.appendChild(renderItem(item));
    }
    wrap.replaceChildren(fragment);
    outer.hidden = false;
  }

  function coalesceTextureRelations(items) {
    const grouped = new Map();
    for (const item of items) {
      const key = `${item.rel || ""}\u0000${item.name || ""}`;
      let current = grouped.get(key);
      if (!current) {
        current = {
          ...item,
          slots: [],
        };
        grouped.set(key, current);
      }
      if (item.slot && !current.slots.includes(item.slot)) {
        current.slots.push(item.slot);
      }
    }
    return Array.from(grouped.values());
  }

  function coalesceReferenceRelations(items) {
    const grouped = new Map();
    for (const item of items) {
      const key = `${item.kind || ""}\u0000${item.rel || ""}\u0000${item.name || ""}`;
      let current = grouped.get(key);
      if (!current) {
        current = {
          ...item,
          slots: [],
        };
        grouped.set(key, current);
      }
      if (item.slot && !current.slots.includes(item.slot)) {
        current.slots.push(item.slot);
      }
    }
    return Array.from(grouped.values());
  }

  // Material documents live in the export's Unity store and open on the Data
  // page. Without a store reference the rel is shown as plain text.
  function createDataPageLink(rel) {
    const url = window.WebUI.dataPageUrlForRel?.(rel) || "";
    if (!url) {
      const label = document.createElement("div");
      label.textContent = rel;
      return label;
    }
    const link = document.createElement("a");
    link.href = url;
    link.dataset.dataPageLink = "1";
    link.title = assetUiText("openInDataPage");
    link.textContent = rel;
    return link;
  }

  function renderMaterialRelationItem(item) {
    const block = document.createElement("div");
    block.className = "asset-related-item";
    block.appendChild(createDataPageLink(item.rel));

    const meta = document.createElement("div");
    meta.className = "asset-related-meta";
    meta.textContent = `${assetUiText("materialJson", { name: item.name })} / ${assetUiText("openInDataPage")}`;
    block.appendChild(meta);
    return block;
  }

  function renderTextureRelationItem(item) {
    const block = document.createElement("div");
    block.className = "asset-related-item";

    if (item.rel && ASSET_STATE.entryByRel.has(item.rel)) {
      block.appendChild(createAssetSelectLink(item.rel));
    } else if (item.rel) {
      const link = document.createElement("a");
      link.href = assetHref(item.rel);
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = item.rel;
      block.appendChild(link);
    } else {
      const label = document.createElement("div");
      label.textContent = item.name;
      block.appendChild(label);
    }

    const meta = document.createElement("div");
    meta.className = "asset-related-meta";
      meta.textContent = item.rel
      ? assetUiText("relationTextureResolved", {
          slots: (item.slots && item.slots.length ? item.slots : [item.slot]).join(", "),
          name: item.name,
        })
      : assetUiText("relationTextureUnresolved", {
          slots: (item.slots && item.slots.length ? item.slots : [item.slot]).join(", "),
          name: item.name,
        });
    block.appendChild(meta);
    return block;
  }

  function renderReferenceRelationItem(item) {
    const block = document.createElement("div");
    block.className = "asset-related-item";

    if (item.kind === "model" && item.rel && ASSET_STATE.entryByRel.has(item.rel)) {
      block.appendChild(createAssetSelectLink(item.rel));
    } else if (item.kind === "material" && item.rel) {
      block.appendChild(createDataPageLink(item.rel));
    } else if (item.rel) {
      const link = document.createElement("a");
      link.href = assetHref(item.rel);
      link.target = "_blank";
      link.rel = "noopener";
      link.textContent = item.rel;
      block.appendChild(link);
    } else {
      const label = document.createElement("div");
      label.textContent = item.name || "(unknown)";
      block.appendChild(label);
    }

    const meta = document.createElement("div");
    meta.className = "asset-related-meta";
    if (item.kind === "material") {
      meta.textContent = assetUiText("relationMaterial", {
        slots: (item.slots && item.slots.length ? item.slots : [item.slot]).join(", "),
      });
    } else {
      meta.textContent = assetUiText("relationModel");
    }
    block.appendChild(meta);
    return block;
  }

  function createAssetSelectLink(rel) {
    const entry = ASSET_STATE.entryByRel.get(rel);
    const link = document.createElement("a");
    link.href = "#assets";
    link.textContent = rel;
    link.addEventListener("click", (ev) => {
      ev.preventDefault();
      if (!entry) return;
      selectAsset(entry, { scrollIntoView: true, variantRel: rel });
    });
    return link;
  }

  function resetAssetPreviewSurface() {
    const img = $("#asset-preview-image");
    const video = $("#asset-preview-video");
    const canvas = $("#asset-model-canvas");
    const placeholder = $("#asset-preview-placeholder");
    const note = $("#asset-preview-note");
    const modelWrap = $("#asset-model-stats-wrap");
    const bgControls = $("#asset-preview-bg-controls");
    const stage = $("#asset-preview-stage");

    ASSET_STATE.viewer.model = null;
    if (img) {
      img.onload = null;
      img.onerror = null;
      img.removeAttribute("src");
      img.hidden = true;
    }
    if (video) {
      video.onloadedmetadata = null;
      video.onerror = null;
      video.pause();
      video.removeAttribute("src");
      video.load();
      video.hidden = true;
    }
    if (canvas) canvas.hidden = true;
    if (bgControls) bgControls.hidden = true;
    if (stage) stage.classList.remove("has-preview-bg");
    if (placeholder) {
      placeholder.hidden = true;
      placeholder.textContent = assetUiText("previewPlaceholder");
    }
    if (note) {
      note.hidden = true;
      note.textContent = "";
    }
    if (modelWrap) modelWrap.hidden = true;
    $("#asset-model-stats").replaceChildren();
  }

  function renderImagePreview(entry) {
    const img = $("#asset-preview-image");
    const canvas = $("#asset-model-canvas");
    const placeholder = $("#asset-preview-placeholder");
    const note = $("#asset-preview-note");
    const modelWrap = $("#asset-model-stats-wrap");

    ASSET_STATE.viewer.model = null;
    modelWrap.hidden = true;
    $("#asset-model-stats").replaceChildren();

    canvas.hidden = true;
    img.hidden = false;
    placeholder.hidden = true;
    note.hidden = false;
    note.textContent = assetUiText("loadingImagePreview");

    img.onload = () => {
      note.textContent = assetUiText("imagePixels", {
        width: img.naturalWidth.toLocaleString(),
        height: img.naturalHeight.toLocaleString(),
      });
    };
    img.onerror = () => {
      img.hidden = true;
      placeholder.hidden = false;
      placeholder.textContent = assetUiText("imagePreviewUnavailable");
      note.textContent = assetUiText("rawLinkAvailable");
    };
    img.src = assetHref(entry.rel);
    img.alt = entry.name;
  }

  function renderVideoPreview(entry) {
    const video = $("#asset-preview-video");
    const placeholder = $("#asset-preview-placeholder");
    const note = $("#asset-preview-note");
    if (!video) {
      renderFilePreview(entry);
      return;
    }

    video.hidden = false;
    placeholder.hidden = true;
    note.hidden = false;
    note.textContent = assetUiText("loadingVideoPreview");

    video.onloadedmetadata = () => {
      note.textContent = Number.isFinite(video.duration)
        ? assetUiText("videoDuration", { duration: formatDuration(video.duration) })
        : formatBytes(entry.size);
    };
    video.onerror = () => {
      video.hidden = true;
      placeholder.hidden = false;
      placeholder.textContent = assetUiText("videoPreviewUnavailable");
      note.textContent = assetUiText("rawLinkAvailable");
    };
    video.src = assetHref(entry.rel);
    video.load();
  }

  function renderFilePreview(entry) {
    const placeholder = $("#asset-preview-placeholder");
    const note = $("#asset-preview-note");
    placeholder.hidden = false;
    placeholder.textContent = assetUiText("filePreviewUnavailable");
    note.hidden = false;
    note.textContent = entry?.rel ? assetUiText("rawLinkAvailable") : "";
  }

  const MODEL_CACHE_LIMIT = 8;
  const VIEWER_DEFAULTS = { rotationX: -0.35, rotationY: 0.75, zoom: 1, panX: 0, panY: 0 };
  const VIEWER_FOV_TAN = Math.tan((35 * Math.PI) / 360);
  const VIEWER_DISTANCE = 4.2;
  const CANVAS_TRIANGLE_LIMIT = 60000;

  function rememberCached(cache, key, value) {
    cache.delete(key);
    cache.set(key, value);
    while (cache.size > MODEL_CACHE_LIMIT) cache.delete(cache.keys().next().value);
    return value;
  }

  async function loadObjModel(rel) {
    const cached = ASSET_STATE.modelCache.get(rel);
    if (cached) return rememberCached(ASSET_STATE.modelCache, rel, cached);

    const res = await fetch(assetHref(rel));
    if (!res.ok) throw new Error(`OBJ HTTP ${res.status}`);
    const model = parseObj(await res.text());
    await ensureAssetRelations();
    bindObjMaterials(model, ASSET_STATE.relations[rel] || {});
    return rememberCached(ASSET_STATE.modelCache, rel, model);
  }

  function resolveReviewModelFile(activeVariant) {
    if (!activeVariant) return null;
    if (activeVariant.ext === "obj") return activeVariant;
    if (activeVariant.previewRel) {
      return ASSET_STATE.rawEntryByRel.get(activeVariant.previewRel) || null;
    }
    return null;
  }

  function renderModelStatGrid(stats) {
    const wrap = $("#asset-model-stats");
    const fragment = document.createDocumentFragment();
    for (const [label, value] of stats) {
      const block = document.createElement("div");
      block.className = "asset-model-stat";

      const statLabel = document.createElement("div");
      statLabel.className = "asset-model-stat-label";
      statLabel.textContent = label;
      block.appendChild(statLabel);

      const statValue = document.createElement("div");
      statValue.className = "asset-model-stat-value";
      statValue.textContent = value;
      block.appendChild(statValue);

      fragment.appendChild(block);
    }

    wrap.replaceChildren(fragment);
  }

  function meshModelStats(model) {
    return [
      [assetUiText("vertices"), (model.triangleCount ? model.vertexCount : (model.sourceVertexCount ?? model.vertexCount)).toLocaleString()],
      [assetUiText("faces"), model.faceCount.toLocaleString()],
      [assetUiText("triangles"), model.triangleCount.toLocaleString()],
      [assetUiText("objectsGroups"), model.objectCount.toLocaleString()],
    ];
  }

  function fbxSummaryStats(summary) {
    const stats = [
      [assetUiText("fbxFormat"), summary.format || assetUiText("none")],
      [assetUiText("fbxVersion"), summary.version ? String(summary.version) : assetUiText("none")],
      [assetUiText("fbxNodes"), Number(summary.nodeCount || 0).toLocaleString()],
      [assetUiText("fbxModels"), Number(summary.counts?.Model || 0).toLocaleString()],
      [assetUiText("fbxGeometries"), Number(summary.counts?.Geometry || 0).toLocaleString()],
      [assetUiText("fbxMaterials"), Number(summary.counts?.Material || 0).toLocaleString()],
      [assetUiText("fbxTextures"), Number(summary.counts?.Texture || 0).toLocaleString()],
      [assetUiText("fbxAnimations"), Number(summary.counts?.AnimationStack || 0).toLocaleString()],
    ];
    if (summary.sampleNames && summary.sampleNames.length) {
      stats.push([assetUiText("fbxSampleNames"), summary.sampleNames.join(", ")]);
    }
    return stats;
  }

  function renderModelStats(activeVariant, { model = null, reviewVariant = null, summary = null } = {}) {
    const stats = [];
    if (activeVariant?.ext === "fbx") {
      stats.push([assetUiText("factSelectedRawFile"), activeVariant.rel]);
      if (activeVariant.lod !== null) stats.push([assetUiText("factLod"), String(activeVariant.lod)]);
    } else {
      stats.push([
        assetUiText("selectedLod"),
        activeVariant && activeVariant.lod !== null ? `LOD ${activeVariant.lod}` : activeVariant?.name || assetUiText("none"),
      ]);
    }
    if (reviewVariant && reviewVariant.rel !== activeVariant?.rel) {
      stats.push([assetUiText("factPreviewProxy"), reviewVariant.rel]);
    }
    if (model && !model.triangleCount) stats.push([assetUiText("geometry"), assetUiText("emptyModelTag")]);
    if (model) stats.push(...meshModelStats(model));
    if (summary) stats.push(...fbxSummaryStats(summary));
    renderModelStatGrid(stats);
  }

  function showViewerModel(model) {
    Object.assign(ASSET_STATE.viewer, VIEWER_DEFAULTS, { model });
    renderModelObjectToggles(model);
    queueModelRender();
  }

  // One switch per FBX mesh object, grouped by LOD. The LOD chips pick which
  // level draws without touching the switches; effects and shadow proxies
  // start off.
  function renderModelObjectToggles(model) {
    const wrap = $("#asset-objects-wrap");
    const list = $("#asset-objects");
    const objects = model?.objects || [];
    list.replaceChildren();
    wrap.hidden = objects.length < 2;
    if (wrap.hidden) return;
    $("#asset-objects-label").textContent = assetUiText("modelObjects", { count: objects.length });
    const lods = model.lods || [];
    const sections = new Map();
    const lodChips = [];
    const syncLods = () => {
      for (const [lod, chip] of lodChips) chip.classList.toggle("is-active", lod === model.lod);
      for (const [lod, section] of sections) section.classList.toggle("is-inactive", lod !== null && (model.lod === "best"
        ? !objects.some((object) => object.lod === lod && object.bestLod === lod) : lod !== model.lod));
    };
    if (lods.length > 1) {
      const bar = document.createElement("div");
      bar.className = "asset-variant-list asset-lod-list";
      for (const lod of model.mixedLods ? ["best", ...lods] : lods) {
        const chip = document.createElement("button");
        chip.type = "button";
        chip.className = "asset-variant-chip";
        chip.textContent = lod === "best" ? assetUiText("modelLodBest") : assetUiText("modelLod", { lod });
        chip.addEventListener("click", () => {
          model.lod = lod;
          syncLods();
          queueModelRender();
        });
        lodChips.push([lod, chip]);
        bar.append(chip);
      }
      list.append(bar);
    }
    const ordered = [...objects].sort((a, b) => (a.lod ?? -1) - (b.lod ?? -1));
    for (const object of ordered) {
      object.visible = object.defaultVisible;
      const lod = lods.length ? object.lod : null;
      if (!sections.has(lod)) {
        const section = document.createElement("div");
        section.className = "asset-object-section";
        if (lods.length) {
          const head = document.createElement("div");
          head.className = "asset-object-section-head";
          head.textContent = lod === null ? assetUiText("modelLodShared") : assetUiText("modelLod", { lod });
          section.append(head);
        }
        const grid = document.createElement("div");
        grid.className = "asset-object-grid";
        section.append(grid);
        sections.set(lod, section);
        list.append(section);
      }
      const label = document.createElement("label");
      label.className = "asset-object-toggle";
      const input = document.createElement("input");
      input.type = "checkbox";
      input.checked = object.visible !== false;
      input.addEventListener("change", () => {
        object.visible = input.checked;
        queueModelRender();
      });
      const name = document.createElement("span");
      name.textContent = object.name;
      name.title = object.name;
      label.append(input, name);
      if (object.kind) {
        const tag = document.createElement("em");
        tag.className = "asset-object-tag";
        tag.textContent = assetUiText(object.kind === "vfx" ? "modelObjectVfx" : "modelObjectShadow");
        label.append(tag);
      }
      sections.get(lod).lastChild.append(label);
    }
    syncLods();
  }

  async function renderCollisionAssemblyPreview(assembly) {
    return renderDecodedObjPreview(assembly, "collisionPrefabBoundary", "collisionPrefabUnavailable");
  }

  async function renderDecodedObjPreview(assembly, boundaryKey, errorKey) {
    const token = ++ASSET_STATE.detailToken;
    const note = $("#asset-preview-note");
    note.textContent = assetUiText("loadingObjPreview");
    try {
      const model = await loadObjModel(assembly.rel);
      if (token !== ASSET_STATE.detailToken) return;
      $("#asset-model-canvas").hidden = false;
      $("#asset-preview-placeholder").hidden = true;
      $("#asset-model-stats-wrap").hidden = false;
      renderModelStatGrid(meshModelStats(model));
      showViewerModel(model);
      note.textContent = assetUiText(boundaryKey);
    } catch (error) {
      if (token === ASSET_STATE.detailToken) {
        note.textContent = assetUiText(errorKey, { reason: String(error.message || error) });
      }
    }
  }

  async function verifiedStoredBytes(asset) {
    if (!/^(StoredRender|StoredUV)\/[^/\\]+$/.test(asset.rel) || !/^[a-f0-9]{64}$/.test(asset.sha256)) throw new Error("Invalid stored artifact descriptor");
    const response = await fetch(assetHref(asset.rel));
    if (!response.ok) throw new Error(`Stored artifact HTTP ${response.status}`);
    const bytes = await response.arrayBuffer();
    const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map((n) => n.toString(16).padStart(2, "0")).join("");
    if (digest !== asset.sha256) throw new Error("Stored artifact hash differs");
    return bytes;
  }

  function storedTextureInspection(model, asset, texture, slot, channel) {
    if (!asset.hasUV0 || texture.uvSet !== (asset.uvSet ?? 0) || !Number.isInteger(slot) || slot < 0 || slot >= asset.submeshCount ||
        !Number.isInteger(channel) || channel < 0 || channel > 4) throw new Error("Stored UV/material slot unavailable");
    const scale = [texture.scale.x, texture.scale.y], offset = [texture.offset.x, texture.offset.y];
    if (![...scale, ...offset].every(Number.isFinite)) throw new Error("Stored UV transform is non-finite");
    const sampler = texture.target.preview.sampler;
    if (![sampler.m_WrapU, sampler.m_WrapV].every((v) => Number.isInteger(v) && v >= 0 && v <= 3) ||
        ![0, 1, 2].includes(sampler.m_FilterMode)) throw new Error("Stored texture sampler unsupported");
    let found = false;
    const groups = model.groups.map((group) => {
      const match = group.name.match(/_submesh_(\d+)$/);
      if (!match || Number(match[1]) >= asset.submeshCount) throw new Error("Stored OBJ submesh census differs");
      const selected = Number(match[1]) === slot;
      if (selected && (!model.uvs || group.hasUvs === false)) throw new Error("Stored submesh has no complete projected UV coordinates");
      found ||= selected;
      return {...group,material:"",textureRel:"",blend:null,inspection:selected ? {scale,offset,channel,sampler} : null};
    });
    if (!found) throw new Error("Stored material slot has no drawable submesh");
    return {...model,groups}; // Immutable cache geometry; inspection never leaks to a neutral view.
  }

  async function storedInspectionTexture(state, descriptor) {
    const sampler = descriptor.sampler;
    const key = `inspection:${descriptor.sha256}:${sampler.m_WrapU}:${sampler.m_WrapV}:${sampler.m_FilterMode}`;
    if (state.textures.has(key)) return state.textures.get(key).promise;
    const promise = (async () => {
      const bytes = await verifiedStoredBytes(descriptor);
      const image = await createImageBitmap(new Blob([bytes], {type:"image/png"}),
        {imageOrientation:"flipY",premultiplyAlpha:"none",colorSpaceConversion:"none"});
      try {
        if (state.lost || image.width !== descriptor.width || image.height !== descriptor.height) throw new Error("Stored PNG dimensions/context differ");
        const powerOfTwo = (n) => n > 0 && (n & (n - 1)) === 0;
        if (!state.isWebGl2 && (!powerOfTwo(image.width) || !powerOfTwo(image.height)) &&
            [sampler.m_WrapU,sampler.m_WrapV].some((v) => v === 0 || v === 2)) throw new Error("WebGL1 cannot wrap this stored NPOT image");
        const gl = state.context;
        if (Math.max(image.width,image.height) > gl.getParameter(gl.MAX_TEXTURE_SIZE)) throw new Error("Stored PNG exceeds this WebGL texture limit");
        const texture = gl.createTexture();
        if (!texture) throw new Error("WebGL texture allocation failed");
        gl.bindTexture(gl.TEXTURE_2D, texture);
        const unpack = [gl.UNPACK_COLORSPACE_CONVERSION_WEBGL,gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,gl.UNPACK_FLIP_Y_WEBGL];
        const previous = unpack.map((key) => gl.getParameter(key));
        try {
          gl.pixelStorei(unpack[0],gl.NONE); gl.pixelStorei(unpack[1],false); gl.pixelStorei(unpack[2],false);
          gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,image);
        } catch (e) {gl.deleteTexture(texture);throw e;}
        finally {unpack.forEach((key,i) => gl.pixelStorei(key,previous[i]));}
        const wrap = (v) => [gl.REPEAT,gl.CLAMP_TO_EDGE,gl.MIRRORED_REPEAT,gl.CLAMP_TO_EDGE][v];
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, wrap(sampler.m_WrapU));
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, wrap(sampler.m_WrapV));
        const filter = sampler.m_FilterMode === 0 ? gl.NEAREST : gl.LINEAR;
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, filter); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, filter);
        return texture; // Top mip only; no invented mip chain or live sampler override.
      } finally {image.close();}
    })();
    state.textures.set(key,{promise});
    try {return await promise;} catch (e) {state.textures.delete(key);throw e;}
  }

  async function renderStoredTextureInspection(asset, texture, slot, channel) {
    const token = ++ASSET_STATE.detailToken, note = $("#asset-preview-note");
    note.textContent = assetUiText("loadingObjPreview");
    try {
      const projected = await storedUvAsset(asset,texture.uvSet);
      const bytes = await verifiedStoredBytes(projected);
      const model = storedTextureInspection(parseObj(new TextDecoder().decode(bytes)),projected,texture,slot,channel);
      const state = ASSET_STATE.viewer.gl;
      if (!state || ASSET_STATE.modelOnly) throw new Error("Texture inspection requires WebGL with Model only turned off");
      const image = await storedInspectionTexture(state,texture.target.preview);
      if (token !== ASSET_STATE.detailToken) return;
      for (const group of model.groups) if (group.inspection) group.inspection.texture = image;
      $("#asset-model-canvas").hidden = false; $("#asset-preview-placeholder").hidden = true;
      $("#asset-model-stats-wrap").hidden = false; renderModelStatGrid(meshModelStats(model)); showViewerModel(model);
      note.textContent = assetUiText("collisionTextureInspectNote", {property:texture.property,slot,uv:texture.uvSet,channel:["RGB","R","G","B","A"][channel]});
    } catch (e) {
      if (token === ASSET_STATE.detailToken) note.textContent = assetUiText("collisionRendererUnavailable", {reason:String(e.message || e)});
    }
  }

  let storedUvPromise;
  async function storedUvAsset(asset,uvSet) {
    if (uvSet === 0) return asset;
    if (uvSet !== 1 || !asset.hasUV1) throw new Error("Stored UV channel unavailable");
    storedUvPromise ||= fetch("data/assets/mesh_uv/index.json").then((r) => r.ok ? r.json() : null).catch(() => null);
    const payload = await storedUvPromise;
    const target = payload?.schema === "endfield.assets-stored-mesh-uv.v2" && payload.status === "validated" ? payload.bindings?.[asset.rel] : null;
    if (!target || target.originalMeshArtifactSha256 !== asset.sha256 || typeof asset.sourceMeshRawSha256 !== "string" ||
        target.originalMeshRawSha256 !== asset.sourceMeshRawSha256 || payload.originalStoredRenderRoot !== ASSET_STATE.sourceRoots.StoredRender || target.uvSet !== 1 ||
        !/^StoredUV\/[^/\\]+$/.test(target.rel) || !/^webui\/data\/assets\/mesh_uv\/selection-[^/\\]+$/.test(payload.sourceRoot)) throw new Error("No matching admitted UV1 projection");
    ASSET_STATE.sourceRoots.StoredUV = payload.sourceRoot;
    return target;
  }

  async function renderModelPreview(entry) {
    const img = $("#asset-preview-image");
    const canvas = $("#asset-model-canvas");
    const placeholder = $("#asset-preview-placeholder");
    const note = $("#asset-preview-note");
    const modelWrap = $("#asset-model-stats-wrap");
    const activeVariant = getActiveModelFile(entry);

    img.hidden = true;
    canvas.hidden = true;
    placeholder.hidden = true;
    note.hidden = false;
    note.textContent = assetUiText("previewPlaceholder");
    modelWrap.hidden = true;
    ASSET_STATE.viewer.model = null;
    renderModelObjectToggles(null);
    $("#asset-model-stats").replaceChildren();

    initModelViewer(canvas);

    const token = ++ASSET_STATE.detailToken;
    const current = () => token === ASSET_STATE.detailToken;
    try {
      if (!activeVariant) throw new Error(assetUiText("noModelFile"));
      const reviewVariant = resolveReviewModelFile(activeVariant);

      // An FBX is drawn from its own geometry first; the paired OBJ proxy
      // only stands in when the FBX carries no readable mesh.
      let fbx = null;
      let fbxError = null;
      if (activeVariant.ext === "fbx") {
        note.textContent = assetUiText("loadingFbxSummary");
        try {
          fbx = await loadFbxAsset(activeVariant.rel);
        } catch (error) {
          fbxError = error;
        }
        if (!current()) return;
        if (fbx?.model && fbx.model.triangleCount) {
          canvas.hidden = false;
          renderModelStats(activeVariant, { model: fbx.model, summary: fbx.summary });
          modelWrap.hidden = false;
          note.textContent = assetUiText("previewingModel", { name: activeVariant.name });
          showViewerModel(fbx.model);
          return;
        }
      }

      if (reviewVariant && reviewVariant.ext === "obj") {
        try {
          canvas.hidden = false;
          note.textContent = assetUiText("loadingObjPreview");
          const model = await loadObjModel(reviewVariant.rel);
          if (!current()) return;

          renderModelStats(activeVariant, { model, reviewVariant, summary: fbx?.summary || null });
          modelWrap.hidden = false;
          note.textContent = reviewVariant.rel === activeVariant.rel
            ? assetUiText("previewingModel", { name: activeVariant.name })
            : assetUiText("previewingModelViaObj", { name: activeVariant.name });
          if (activeVariant.collision) note.textContent = assetUiText("collisionPreviewHint");
          if (!model.triangleCount) {
            canvas.hidden = true;
            placeholder.hidden = false;
            placeholder.textContent = assetUiText("emptyModelTag");
            note.textContent = assetUiText("emptyModelHint");
          }
          showViewerModel(model);
          return;
        } catch (error) {
          if (activeVariant.ext !== "fbx") throw error;
          if (!current()) return;
          ASSET_STATE.viewer.model = null;
          canvas.hidden = true;
        }
      }

      if (fbx) {
        placeholder.hidden = false;
        placeholder.textContent = assetUiText("fbxSummaryPlaceholder");
        renderModelStats(activeVariant, { summary: fbx.summary });
        modelWrap.hidden = false;
        note.textContent = fbx.geometryError
          ? `${assetUiText("fbxSummaryLoaded")} (${fbx.geometryError})`
          : assetUiText("fbxSummaryLoaded");
        return;
      }

      throw fbxError || new Error(assetUiText("objPreviewUnavailable"));
    } catch (error) {
      if (!current()) return;
      canvas.hidden = true;
      placeholder.hidden = false;
      placeholder.textContent = activeVariant?.ext === "fbx"
        ? assetUiText("fbxSummaryUnavailable")
        : assetUiText("objPreviewUnavailable");
      note.textContent = String(error);
      ASSET_STATE.viewer.model = null;
      modelWrap.hidden = true;
    }
  }

  function initModelViewer(canvas) {
    const viewer = ASSET_STATE.viewer;
    if (viewer.bound) return;
    viewer.canvas = canvas;
    viewer.bound = true;
    viewer.gl = createModelGl(canvas);
    if (!viewer.gl) viewer.ctx = canvas.getContext("2d");

    canvas.addEventListener("webglcontextlost", (ev) => {
      ev.preventDefault();
      if (viewer.gl) viewer.gl.lost = true;
    });
    canvas.addEventListener("webglcontextrestored", () => {
      viewer.gl = createModelGl(canvas);
      queueModelRender();
    });

    canvas.addEventListener("contextmenu", (ev) => ev.preventDefault());
    canvas.addEventListener("pointerdown", (ev) => {
      if (!viewer.model) return;
      viewer.dragging = true;
      viewer.dragMode = ev.button === 2 || ev.button === 1 || ev.shiftKey ? "pan" : "rotate";
      viewer.lastX = ev.clientX;
      viewer.lastY = ev.clientY;
      canvas.setPointerCapture(ev.pointerId);
      ev.preventDefault();
    });

    canvas.addEventListener("pointermove", (ev) => {
      if (!viewer.dragging || !viewer.model) return;
      const dx = ev.clientX - viewer.lastX;
      const dy = ev.clientY - viewer.lastY;
      viewer.lastX = ev.clientX;
      viewer.lastY = ev.clientY;
      if (viewer.dragMode === "pan") {
        // One CSS pixel moves the model by the same distance on screen.
        const distance = viewerCameraDistance(viewer.model, canvas.clientWidth / Math.max(1, canvas.clientHeight));
        const worldPerPixel = (2 * VIEWER_FOV_TAN * distance) / Math.max(1, canvas.clientHeight);
        viewer.panX += dx * worldPerPixel;
        viewer.panY -= dy * worldPerPixel;
      } else {
        viewer.rotationY += dx * 0.01;
        viewer.rotationX = clamp(viewer.rotationX + dy * 0.01, -Math.PI / 2, Math.PI / 2);
      }
      queueModelRender();
    });

    const endDrag = () => {
      viewer.dragging = false;
      viewer.dragMode = "";
    };
    canvas.addEventListener("pointerup", endDrag);
    canvas.addEventListener("pointercancel", endDrag);

    canvas.addEventListener("dblclick", () => {
      if (!viewer.model) return;
      Object.assign(viewer, VIEWER_DEFAULTS);
      queueModelRender();
    });

    canvas.addEventListener("wheel", (ev) => {
      if (!viewer.model) return;
      ev.preventDefault();
      viewer.zoom = clamp(viewer.zoom * Math.exp(-ev.deltaY * 0.0015), 0.2, 12);
      queueModelRender();
    }, { passive: false });

    if (typeof ResizeObserver === "function") {
      new ResizeObserver(() => queueModelRender()).observe(canvas);
    }
  }

  function queueModelRender() {
    const viewer = ASSET_STATE.viewer;
    if (ASSET_STATE.activeView !== "assets") return;
    if (!viewer.model || !viewer.canvas || viewer.renderQueued) return;
    viewer.renderQueued = true;
    requestAnimationFrame(() => {
      viewer.renderQueued = false;
      renderModelCanvas();
    });
  }

  function resizeModelCanvas(canvas) {
    const width = Math.max(1, canvas.clientWidth);
    const height = Math.max(1, canvas.clientHeight);
    const dpr = window.devicePixelRatio || 1;
    const pixelWidth = Math.max(1, Math.round(width * dpr));
    const pixelHeight = Math.max(1, Math.round(height * dpr));
    if (canvas.width !== pixelWidth || canvas.height !== pixelHeight) {
      canvas.width = pixelWidth;
      canvas.height = pixelHeight;
    }
    return { width, height, dpr };
  }

  // Orbit rotation R = Rx * Ry, column-major: columns are the model X, Y, Z axes in view space.
  function viewerRotation() {
    const viewer = ASSET_STATE.viewer;
    const cx = Math.cos(viewer.rotationX);
    const sx = Math.sin(viewer.rotationX);
    const cy = Math.cos(viewer.rotationY);
    const sy = Math.sin(viewer.rotationY);
    return [
      cy, sx * sy, -cx * sy,
      0, cx, sx,
      sy, -sx * cy, cx * cy,
    ];
  }

  function viewerCameraDistance(model, aspect = 1) {
    // The normalized AABB fits a cube, whose diagonal can exceed the camera's
    // field of view after orbiting. Fit its enclosing sphere to the smaller
    // viewport dimension; keep the user's zoom relative to that default fit.
    const radius = Number.isFinite(model.fitRadius) && model.fitRadius > 0 ? model.fitRadius : Math.sqrt(3);
    const halfAngle = Math.atan(VIEWER_FOV_TAN * Math.min(1, Math.max(0.01, aspect)));
    const fitted = radius * 1.08 / Math.sin(halfAngle);
    return Math.max(VIEWER_DISTANCE, fitted) / ASSET_STATE.viewer.zoom;
  }

  // Column-major model-view matrix: pan * orbit * fit-to-unit-cube.
  function viewerModelViewMatrix(model, aspect = 1) {
    const viewer = ASSET_STATE.viewer;
    const r = viewerRotation();
    const s = model.scale;
    const [mx, my, mz] = model.center;
    const m = new Float32Array(16);
    for (let col = 0; col < 3; col += 1) {
      m[col * 4] = r[col * 3] * s;
      m[col * 4 + 1] = r[col * 3 + 1] * s;
      m[col * 4 + 2] = r[col * 3 + 2] * s;
    }
    for (let row = 0; row < 3; row += 1) {
      m[12 + row] = -(m[row] * mx + m[4 + row] * my + m[8 + row] * mz);
    }
    m[12] += viewer.panX;
    m[13] += viewer.panY;
    m[14] -= viewerCameraDistance(model, aspect);
    m[15] = 1;
    return m;
  }

  function viewerProjectionMatrix(aspect, distance) {
    const near = Math.max(0.01, distance - 4);
    const far = distance + 4;
    const f = 1 / VIEWER_FOV_TAN;
    const p = new Float32Array(16);
    p[0] = f / aspect;
    p[5] = f;
    p[10] = (far + near) / (near - far);
    p[11] = -1;
    p[14] = (2 * far * near) / (near - far);
    return p;
  }

  function renderModelCanvas() {
    const { canvas, gl, model } = ASSET_STATE.viewer;
    if (!canvas || !model || canvas.hidden) return;
    const size = resizeModelCanvas(canvas);
    renderModelAxes(size.dpr);
    if (gl) {
      if (!gl.lost) renderModelGl(gl, model, size);
      return;
    }
    renderModelCanvas2d(model, size);
  }

  const MODEL_AXES = [
    { label: "X", color: "#e5484d" },
    { label: "Y", color: "#30a46c" },
    { label: "Z", color: "#3e7bfa" },
  ];

  // Corner gizmo: the model's file axes (as stored in the OBJ/FBX) under the current orbit.
  function renderModelAxes(dpr = window.devicePixelRatio || 1) {
    const canvas = $("#asset-model-axes");
    if (!canvas) return;
    const cssSize = canvas.clientWidth || 88;
    const pixels = Math.round(cssSize * dpr);
    if (canvas.width !== pixels || canvas.height !== pixels) {
      canvas.width = pixels;
      canvas.height = pixels;
    }
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, cssSize, cssSize);
    const r = viewerRotation();
    const half = cssSize / 2;
    const length = half - 14;
    const ink = previewBackgroundLuminance() > 0.55 ? "rgba(0,0,0,0.55)" : "rgba(255,255,255,0.7)";
    const axes = [];
    for (let i = 0; i < 3; i += 1) {
      const [x, y, z] = [r[i * 3], r[i * 3 + 1], r[i * 3 + 2]];
      axes.push({ ...MODEL_AXES[i], x, y, z, sign: 1 });
      axes.push({ ...MODEL_AXES[i], x: -x, y: -y, z: -z, sign: -1 });
    }
    // Painter's order: view-space +z points at the viewer.
    axes.sort((a, b) => a.z - b.z);
    ctx.lineCap = "round";
    ctx.font = "600 11px system-ui, sans-serif";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillStyle = ink;
    ctx.beginPath();
    ctx.arc(half, half, 2, 0, Math.PI * 2);
    ctx.fill();
    for (const axis of axes) {
      const ex = half + axis.x * length;
      const ey = half - axis.y * length;
      ctx.globalAlpha = axis.sign > 0 ? 0.65 + 0.35 * Math.max(0, axis.z) : 0.35;
      ctx.strokeStyle = axis.color;
      ctx.lineWidth = axis.sign > 0 ? 2.5 : 1.5;
      if (axis.sign < 0) ctx.setLineDash([3, 3]);
      ctx.beginPath();
      ctx.moveTo(half, half);
      ctx.lineTo(ex, ey);
      ctx.stroke();
      ctx.setLineDash([]);
      if (axis.sign < 0) continue;
      ctx.fillStyle = axis.color;
      ctx.beginPath();
      ctx.arc(ex, ey, 7, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#fff";
      ctx.fillText(axis.label, ex, ey + 0.5);
    }
    ctx.globalAlpha = 1;
  }

  const MODEL_VERTEX_SHADER = `
    attribute vec3 aPosition;
    attribute vec3 aNormal;
    attribute vec2 aUv;
    uniform mat4 uModelView;
    uniform mat4 uProjection;
    varying vec3 vNormal;
    varying vec3 vView;
    varying vec2 vUv;
    void main() {
      vec4 viewPos = uModelView * vec4(aPosition, 1.0);
      vNormal = mat3(uModelView) * aNormal;
      vView = viewPos.xyz;
      vUv = aUv;
      gl_Position = uProjection * viewPos;
    }
  `;

  const MODEL_FRAGMENT_SHADER = `
    precision mediump float;
    varying vec3 vNormal;
    varying vec3 vView;
    varying vec2 vUv;
    uniform vec3 uColor;
    uniform sampler2D uTexture;
    uniform float uHasTexture;
    uniform vec4 uTint;
    uniform float uAvatar;
    uniform vec3 uAvatarBase;
    uniform vec3 uAvatarTint;
    uniform vec3 uAvatarAdd;
    uniform vec3 uEmission;
    uniform sampler2D uEmissionTexture;
    uniform float uHasEmissionTexture;
    uniform float uAlphaClip;
    uniform float uEffect;
    uniform float uPremultiply;
    uniform float uInspection;
    uniform float uChannel;
    uniform vec4 uUvTransform;
    uniform vec2 uMirrorOnce;
    void main() {
      vec3 n = normalize(vNormal);
      if (!gl_FrontFacing) n = -n;
      vec3 v = normalize(-vView);
      float key = max(dot(n, normalize(vec3(0.45, 0.6, 0.65))), 0.0);
      float fill = max(dot(n, normalize(vec3(-0.6, -0.15, 0.4))), 0.0);
      float rim = pow(1.0 - max(dot(n, v), 0.0), 3.0);
      float spec = pow(max(dot(n, normalize(normalize(vec3(0.45, 0.6, 0.65)) + v)), 0.0), 32.0);
      vec3 color;
      float alpha = uTint.a;
      if (uHasTexture > 0.5) {
        vec2 uv = vUv * uUvTransform.xy + uUvTransform.zw;
        if (uInspection > 0.5) uv = mix(uv, clamp(abs(uv), 0.0, 1.0), uMirrorOnce);
        vec4 texel = texture2D(uTexture, uv);
        if (uInspection > 0.5) {
          vec3 inspected = texel.rgb;
          if (uChannel > 0.5 && uChannel < 1.5) inspected = vec3(texel.r);
          else if (uChannel < 2.5 && uChannel > 1.5) inspected = vec3(texel.g);
          else if (uChannel < 3.5 && uChannel > 2.5) inspected = vec3(texel.b);
          else if (uChannel > 3.5) inspected = vec3(texel.a);
          gl_FragColor = vec4(inspected, 1.0); return;
        }
        texel *= uTint;
        if (uAvatar > 0.5) {
          // CharacterNPR: G mixes base tint -> base colour, B selects the
          // additional tint, and R is the intensity of that result.
          texel.rgb = mix(mix(uAvatarTint, uAvatarBase, texel.g), uAvatarAdd, texel.b) * texel.r;
        }
        alpha = texel.a;
        if (alpha < uAlphaClip) discard;
        // Transparent effects (glows, beams) are unlit: texture times tint.
        color = uEffect > 0.5
          ? texel.rgb
          : texel.rgb * (0.55 + key * 0.4 + fill * 0.12) + vec3(0.08) * rim;
      } else {
        color = uEffect > 0.5
          ? uColor * uTint.rgb
          : uColor * uTint.rgb * (0.24 + key * 0.62 + fill * 0.22) + vec3(0.32) * rim + vec3(0.18) * spec;
      }
      vec3 emission = uEmission;
      if (uHasEmissionTexture > 0.5) emission *= texture2D(uEmissionTexture, vUv).rgb;
      color += emission;
      if (uPremultiply > 0.5) color *= alpha;
      gl_FragColor = vec4(color, alpha);
    }
  `;

  function createModelGl(canvas) {
    const options = { antialias: true, alpha: false, preserveDrawingBuffer: false };
    let gl = canvas.getContext("webgl2", options);
    const isWebGl2 = Boolean(gl);
    if (!gl) gl = canvas.getContext("webgl", options) || canvas.getContext("experimental-webgl", options);
    if (!gl) return null;

    const compile = (type, source) => {
      const shader = gl.createShader(type);
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        throw new Error(gl.getShaderInfoLog(shader) || "shader compile failed");
      }
      return shader;
    };
    try {
      const program = gl.createProgram();
      gl.attachShader(program, compile(gl.VERTEX_SHADER, MODEL_VERTEX_SHADER));
      gl.attachShader(program, compile(gl.FRAGMENT_SHADER, MODEL_FRAGMENT_SHADER));
      gl.linkProgram(program);
      if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
        throw new Error(gl.getProgramInfoLog(program) || "program link failed");
      }
      return {
        context: gl,
        program,
        isWebGl2,
        uint32Indices: isWebGl2 || Boolean(gl.getExtension("OES_element_index_uint")),
        aPosition: gl.getAttribLocation(program, "aPosition"),
        aNormal: gl.getAttribLocation(program, "aNormal"),
        aUv: gl.getAttribLocation(program, "aUv"),
        uModelView: gl.getUniformLocation(program, "uModelView"),
        uProjection: gl.getUniformLocation(program, "uProjection"),
        uColor: gl.getUniformLocation(program, "uColor"),
        uTexture: gl.getUniformLocation(program, "uTexture"),
        uHasTexture: gl.getUniformLocation(program, "uHasTexture"),
        uTint: gl.getUniformLocation(program, "uTint"),
        uAvatar: gl.getUniformLocation(program, "uAvatar"),
        uAvatarBase: gl.getUniformLocation(program, "uAvatarBase"),
        uAvatarTint: gl.getUniformLocation(program, "uAvatarTint"),
        uAvatarAdd: gl.getUniformLocation(program, "uAvatarAdd"),
        uEmission: gl.getUniformLocation(program, "uEmission"),
        uEmissionTexture: gl.getUniformLocation(program, "uEmissionTexture"),
        uHasEmissionTexture: gl.getUniformLocation(program, "uHasEmissionTexture"),
        uAlphaClip: gl.getUniformLocation(program, "uAlphaClip"),
        uEffect: gl.getUniformLocation(program, "uEffect"),
        uPremultiply: gl.getUniformLocation(program, "uPremultiply"),
        uInspection: gl.getUniformLocation(program, "uInspection"),
        uChannel: gl.getUniformLocation(program, "uChannel"),
        uUvTransform: gl.getUniformLocation(program, "uUvTransform"),
        uMirrorOnce: gl.getUniformLocation(program, "uMirrorOnce"),
        textures: new Map(),
        uploaded: null,
        buffers: null,
        lost: false,
      };
    } catch (error) {
      console.warn("[assets] WebGL model viewer unavailable:", error);
      return null;
    }
  }

  // Material name -> base-colour texture rel, from the index's Material
  // relations. FBX materials carry only their Unity name, so a name whose
  // exported materials disagree on the base map stays untextured.
  const MODEL_BASE_TEXTURE_SLOTS = ["_BaseMap", "_BaseColorMap", "_MainTex"];
  function materialBaseTextureIndex() {
    if (ASSET_STATE.materialBaseTextures?.source === ASSET_STATE.relations) return ASSET_STATE.materialBaseTextures.byName;
    const candidates = new Map();
    for (const [rel, relation] of Object.entries(ASSET_STATE.relations || {})) {
      const match = rel.match(/^Unity\/Material\/(.+)_p[0-9A-F]{16}\.json$/i);
      if (!match) continue;
      const textures = relation?.textures || [];
      const base = MODEL_BASE_TEXTURE_SLOTS.map((slot) => textures.find((texture) => texture.slot === slot && texture.rel)).find(Boolean);
      const name = match[1].toLowerCase();
      if (!candidates.has(name)) candidates.set(name, new Set());
      candidates.get(name).add(base?.rel || "");
    }
    // When same-name materials disagree, keep the one texture named after
    // the material itself (M_x -> T_x...); otherwise leave it untextured.
    const byName = new Map();
    for (const [name, rels] of candidates) {
      if (rels.size === 1) {
        byName.set(name, [...rels][0]);
        continue;
      }
      const stem = name.replace(/^m_/, "");
      const own = [...rels].filter((rel) => rel && rel.split("/").pop().toLowerCase().replace(/^t_/, "").startsWith(stem));
      byName.set(name, own.length === 1 ? own[0] : "");
    }
    ASSET_STATE.materialBaseTextures = { source: ASSET_STATE.relations, byName };
    return byName;
  }

  // How a material blends (index `blend`: render queue, Unity BlendMode
  // src/dst, depth write, alpha-test threshold, cull, tint, avatar masks and
  // emission), by material name.
  // Same-name materials take the one whose base texture the viewer chose.
  function materialBlendIndex() {
    if (ASSET_STATE.materialBlends?.source === ASSET_STATE.relations) return ASSET_STATE.materialBlends.byName;
    const chosen = materialBaseTextureIndex();
    const byName = new Map();
    for (const [rel, relation] of Object.entries(ASSET_STATE.relations || {})) {
      if (!relation?.blend) continue;
      const match = rel.match(/^Unity\/Material\/(.+)_p[0-9A-F]{16}\.json$/i);
      if (!match) continue;
      const name = match[1].toLowerCase();
      const textures = relation.textures || [];
      const base = MODEL_BASE_TEXTURE_SLOTS.map((slot) => textures.find((texture) => texture.slot === slot && texture.rel)).find(Boolean);
      if (!byName.has(name) || (base?.rel || "") === chosen.get(name)) byName.set(name, relation.blend);
    }
    ASSET_STATE.materialBlends = { source: ASSET_STATE.relations, byName };
    return byName;
  }

  // Unity BlendMode enum → WebGL factor.
  function modelBlendFactor(gl, mode) {
    return [gl.ZERO, gl.ONE, gl.DST_COLOR, gl.SRC_COLOR, gl.ONE_MINUS_DST_COLOR, gl.SRC_ALPHA,
      gl.ONE_MINUS_SRC_COLOR, gl.DST_ALPHA, gl.ONE_MINUS_DST_ALPHA, gl.SRC_ALPHA_SATURATE,
      gl.ONE_MINUS_SRC_ALPHA][mode] ?? gl.ONE;
  }

  function modelGroupTexture(state, material, textureRel = null) {
    const rel = textureRel ?? (material ? materialBaseTextureIndex().get(material.toLowerCase()) : "");
    if (!rel) return null;
    let entry = state.textures.get(rel);
    if (!entry) {
      const gl = state.context;
      entry = { texture: null };
      state.textures.set(rel, entry);
      const image = new Image();
      image.onload = () => {
        if (state.lost) return;
        const texture = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, texture);
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
        const powerOfTwo = (n) => (n & (n - 1)) === 0;
        // WebGL1 can only repeat and mipmap power-of-two textures.
        if (state.isWebGl2 || (powerOfTwo(image.width) && powerOfTwo(image.height))) {
          gl.generateMipmap(gl.TEXTURE_2D);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
        } else {
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
          gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
        }
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
        entry.texture = texture;
        queueModelRender();
      };
      image.onerror = () => console.warn("[assets] model texture failed to load:", rel);
      image.src = assetHref(rel);
    }
    return entry.texture;
  }

  function uploadModelGl(state, model) {
    const gl = state.context;
    if (state.buffers) {
      gl.deleteBuffer(state.buffers.position);
      gl.deleteBuffer(state.buffers.normal);
      if (state.buffers.uv) gl.deleteBuffer(state.buffers.uv);
      if (state.buffers.index) gl.deleteBuffer(state.buffers.index);
      if (state.buffers.sortedIndex) gl.deleteBuffer(state.buffers.sortedIndex);
    }

    let positions = model.positions;
    let normals = model.normals;
    let uvs = model.uvs || null;
    let indices = model.indices;
    // Without 32-bit index support, large meshes are drawn unindexed. The
    // expansion keeps index order, so material groups keep their ranges.
    const needsUnindexed = !state.uint32Indices && model.vertexCount > 65535;
    if (needsUnindexed) {
      positions = new Float32Array(indices.length * 3);
      normals = new Float32Array(indices.length * 3);
      uvs = model.uvs ? new Float32Array(indices.length * 2) : null;
      for (let i = 0; i < indices.length; i += 1) {
        const src = indices[i] * 3;
        positions.set(model.positions.subarray(src, src + 3), i * 3);
        normals.set(model.normals.subarray(src, src + 3), i * 3);
        if (uvs) uvs.set(model.uvs.subarray(indices[i] * 2, indices[i] * 2 + 2), i * 2);
      }
      indices = null;
    } else if (!state.uint32Indices) {
      indices = Uint16Array.from(indices);
    }

    const position = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, position);
    gl.bufferData(gl.ARRAY_BUFFER, positions, gl.STATIC_DRAW);
    const normal = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, normal);
    gl.bufferData(gl.ARRAY_BUFFER, normals, gl.STATIC_DRAW);
    let uv = null;
    if (uvs) {
      uv = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, uv);
      gl.bufferData(gl.ARRAY_BUFFER, uvs, gl.STATIC_DRAW);
    }
    let index = null;
    if (indices) {
      index = gl.createBuffer();
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, index);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);
    }
    const count = indices ? indices.length : positions.length / 3;
    state.buffers = {
      position,
      normal,
      uv,
      index,
      sortedIndex: null,
      indexType: indices instanceof Uint16Array ? gl.UNSIGNED_SHORT : gl.UNSIGNED_INT,
      indexSize: indices instanceof Uint16Array ? 2 : 4,
      count,
      groups: model.groups?.length ? model.groups : [{ material: "", start: 0, count }],
    };
    state.uploaded = model;
  }

  function renderModelGl(state, model, { width, height }) {
    const gl = state.context;
    if (state.uploaded !== model) uploadModelGl(state, model);
    const buffers = state.buffers;
    const background = previewBackgroundRgb();

    gl.viewport(0, 0, gl.drawingBufferWidth, gl.drawingBufferHeight);
    gl.clearColor(background.r / 255, background.g / 255, background.b / 255, 1);
    // Reset before clearing, since depthMask also controls depth-buffer clears.
    // Opaque and alpha-tested surfaces must occlude their rear triangles.
    gl.depthMask(true);
    gl.disable(gl.BLEND);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.disable(gl.CULL_FACE);

    gl.useProgram(state.program);
    gl.uniformMatrix4fv(state.uModelView, false, viewerModelViewMatrix(model, width / height));
    gl.uniformMatrix4fv(state.uProjection, false, viewerProjectionMatrix(width / height, viewerCameraDistance(model, width / height)));
    const color = ASSET_STATE.modelColor;
    gl.uniform3f(state.uColor, ...[1, 3, 5].map((offset) => Number.parseInt(color.slice(offset, offset + 2), 16) / 255));
    gl.uniform1i(state.uTexture, 0);
    gl.uniform1i(state.uEmissionTexture, 1);

    gl.bindBuffer(gl.ARRAY_BUFFER, buffers.position);
    gl.enableVertexAttribArray(state.aPosition);
    gl.vertexAttribPointer(state.aPosition, 3, gl.FLOAT, false, 0, 0);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffers.normal);
    gl.enableVertexAttribArray(state.aNormal);
    gl.vertexAttribPointer(state.aNormal, 3, gl.FLOAT, false, 0, 0);
    if (state.aUv >= 0) {
      if (buffers.uv) {
        gl.bindBuffer(gl.ARRAY_BUFFER, buffers.uv);
        gl.enableVertexAttribArray(state.aUv);
        gl.vertexAttribPointer(state.aUv, 2, gl.FLOAT, false, 0, 0);
      } else {
        gl.disableVertexAttribArray(state.aUv);
        gl.vertexAttrib2f(state.aUv, 0, 0);
      }
    }
    if (buffers.index) gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buffers.index);

    // Opaque and alpha-tested groups first, then transparent ones in render
    // queue order with their own blend factors and depth write, so glass,
    // hair cards and light effects (additive, unlit) composite over the body.
    const blends = materialBlendIndex();
    const modelOnly = ASSET_STATE.modelOnly;
    const visible = buffers.groups
      .filter((group) => !modelGroupHidden(model, group))
      .map((group) => ({ group, blend: modelOnly ? null : group.blend ?? blends.get(String(group.material || "").toLowerCase()) ?? null }));
    const transparent = (item) => item.blend && item.blend.src !== undefined;
    const draw = ({ group, blend }) => {
      const inspection = !modelOnly ? group.inspection : null;
      const texture = !modelOnly && buffers.uv && group.hasUvs !== false ? inspection?.texture || modelGroupTexture(state, group.material, group.textureRel) : null;
      gl.uniform1f(state.uInspection, inspection ? 1 : 0); gl.uniform1f(state.uChannel, inspection?.channel || 0);
      gl.uniform4f(state.uUvTransform, ...(inspection ? [...inspection.scale,...inspection.offset] : [1,1,0,0]));
      gl.uniform2f(state.uMirrorOnce, inspection?.sampler.m_WrapU === 3 ? 1 : 0, inspection?.sampler.m_WrapV === 3 ? 1 : 0);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, texture);
      gl.uniform1f(state.uHasTexture, texture ? 1 : 0);
      const tint = blend?.tint || [1, 1, 1, 1];
      gl.uniform4f(state.uTint, tint[0], tint[1], tint[2], tint[3]);
      const avatar = blend?.avatar;
      gl.uniform1f(state.uAvatar, avatar ? 1 : 0);
      gl.uniform3f(state.uAvatarBase, ...(avatar?.[0] || [1, 1, 1]));
      gl.uniform3f(state.uAvatarTint, ...(avatar?.[1] || [1, 1, 1]));
      gl.uniform3f(state.uAvatarAdd, ...(avatar?.[2] || [1, 1, 1]));
      const emission = ASSET_STATE.modelEmission ? blend?.emission : null;
      const emissionTexture = buffers.uv && group.hasUvs !== false && emission?.textureRel
        ? modelGroupTexture(state, "", emission.textureRel) : null;
      gl.activeTexture(gl.TEXTURE1);
      gl.bindTexture(gl.TEXTURE_2D, emissionTexture);
      gl.uniform1f(state.uHasEmissionTexture, emissionTexture ? 1 : 0);
      // Keep mapped emission off until its map loads, including UV-less groups.
      gl.uniform3f(state.uEmission, ...(emission && (!emission.textureRel || emissionTexture) ? emission.color : [0, 0, 0]));
      gl.uniform1f(state.uAlphaClip, blend?.clip ?? -1);
      const additive = transparent({ blend }) && blend.dst === 1;
      gl.uniform1f(state.uEffect, additive ? 1 : 0);
      gl.uniform1f(state.uPremultiply, transparent({ blend }) && blend.src === 1 && !additive ? 1 : 0);
      if (transparent({ blend }) && !blend.zw && blend.dst !== 1) {
        // Without depth writes, rear faces must blend before front faces.
        // Keep queue/material ranges intact; reorder only this draw's triangles.
        const order = modelTriangleDepthOrder(model, group, viewerModelViewMatrix(model));
        if (buffers.index) {
          const IndexArray = buffers.indexSize === 2 ? Uint16Array : Uint32Array;
          const sorted = new IndexArray(group.count);
          for (let i = 0; i < order.length; i += 1) {
            const start = order[i];
            sorted.set(model.indices.subarray(start, start + 3), i * 3);
          }
          buffers.sortedIndex ||= gl.createBuffer();
          gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buffers.sortedIndex);
          gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, sorted, gl.DYNAMIC_DRAW);
          gl.drawElements(gl.TRIANGLES, sorted.length, buffers.indexType, 0);
        } else {
          // Expanded vertices preserve the original index offsets.
          for (const start of order) gl.drawArrays(gl.TRIANGLES, start, 3);
        }
      } else if (buffers.index) {
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, buffers.index);
        gl.drawElements(gl.TRIANGLES, group.count, buffers.indexType, group.start * buffers.indexSize);
      } else {
        gl.drawArrays(gl.TRIANGLES, group.start, group.count);
      }
    };
    for (const item of visible) if (!transparent(item)) draw(item);
    const layered = visible.filter(transparent).sort((a, b) => (a.blend.q ?? 3000) - (b.blend.q ?? 3000));
    if (layered.length) {
      gl.enable(gl.BLEND);
      for (const item of layered) {
        gl.blendFunc(modelBlendFactor(gl, item.blend.src), modelBlendFactor(gl, item.blend.dst));
        gl.depthMask(Boolean(item.blend.zw));
        draw(item);
      }
      gl.depthMask(true);
      gl.disable(gl.BLEND);
    }
  }

  function modelGroupHidden(model, group) {
    const object = group.object === undefined ? null : model.objects?.[group.object];
    return Boolean(object) && !modelObjectShown(model, object);
  }

  function modelTriangleDepthOrder(model, group, matrix) {
    const triangles = [];
    const positions = model.positions;
    for (let start = group.start; start < group.start + group.count; start += 3) {
      let depth = 0;
      for (let k = 0; k < 3; k += 1) {
        const vertex = model.indices[start + k] * 3;
        depth += matrix[2] * positions[vertex] + matrix[6] * positions[vertex + 1]
          + matrix[10] * positions[vertex + 2];
      }
      triangles.push({ start, depth });
    }
    // Camera-space Z is negative ahead of the eye: smaller means farther.
    triangles.sort((a, b) => a.depth - b.depth || a.start - b.start);
    return triangles.map((triangle) => triangle.start);
  }

  // A part draws when its own switch is on and it belongs to the selected LOD;
  // changing the LOD leaves every switch as the user set it.
  function modelObjectShown(model, object) {
    const selected = model.lod === "best" ? object.bestLod : model.lod;
    return object.visible !== false && (object.lod === null || selected === null || selected === undefined || object.lod === selected);
  }

  // Software fallback for browsers without WebGL: painter-sorted triangles,
  // sampled down to CANVAS_TRIANGLE_LIMIT.
  function renderModelCanvas2d(model, { width, height, dpr }) {
    const { ctx } = ASSET_STATE.viewer;
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = normalizePreviewBackground(ASSET_STATE.previewBackground);
    ctx.fillRect(0, 0, width, height);

    const mv = viewerModelViewMatrix(model, width / height);
    const focal = (height * 0.5) / VIEWER_FOV_TAN;
    const vertexCount = model.vertexCount;
    const screen = new Float32Array(vertexCount * 3);
    const pos = model.positions;
    for (let i = 0; i < vertexCount; i += 1) {
      const x = pos[i * 3];
      const y = pos[i * 3 + 1];
      const z = pos[i * 3 + 2];
      const vx = mv[0] * x + mv[4] * y + mv[8] * z + mv[12];
      const vy = mv[1] * x + mv[5] * y + mv[9] * z + mv[13];
      const vz = mv[2] * x + mv[6] * y + mv[10] * z + mv[14];
      const depth = Math.max(0.05, -vz);
      screen[i * 3] = width * 0.5 + (vx / depth) * focal;
      screen[i * 3 + 1] = height * 0.5 - (vy / depth) * focal;
      screen[i * 3 + 2] = vz;
    }

    const indices = model.indices;
    const triangleCount = indices.length / 3;
    const stride = Math.max(1, Math.ceil(triangleCount / CANVAS_TRIANGLE_LIMIT));
    const shown = new Uint8Array(triangleCount).fill(1);
    for (const group of model.groups || []) {
      if (modelGroupHidden(model, group)) shown.fill(0, group.start / 3, (group.start + group.count) / 3);
    }
    const order = [];
    for (let t = 0; t < triangleCount; t += stride) if (shown[t]) order.push(t);
    const faceDepth = new Float32Array(triangleCount);
    for (const t of order) {
      faceDepth[t] = screen[indices[t * 3] * 3 + 2] + screen[indices[t * 3 + 1] * 3 + 2] + screen[indices[t * 3 + 2] * 3 + 2];
    }
    order.sort((a, b) => faceDepth[a] - faceDepth[b]);

    const baseColor = [1, 3, 5].map((offset) => Number.parseInt(ASSET_STATE.modelColor.slice(offset, offset + 2), 16));
    const nrm = model.normals;
    for (const t of order) {
      const a = indices[t * 3];
      const b = indices[t * 3 + 1];
      const c = indices[t * 3 + 2];
      // View-space z of the averaged vertex normal approximates facing.
      const nx = nrm[a * 3] + nrm[b * 3] + nrm[c * 3];
      const ny = nrm[a * 3 + 1] + nrm[b * 3 + 1] + nrm[c * 3 + 1];
      const nz = nrm[a * 3 + 2] + nrm[b * 3 + 2] + nrm[c * 3 + 2];
      const vz = mv[2] * nx + mv[6] * ny + mv[10] * nz;
      const vy = mv[1] * nx + mv[5] * ny + mv[9] * nz;
      const len = Math.hypot(nx, ny, nz) * model.scale || 1;
      const light = clamp(0.3 + Math.abs(vz / len) * 0.5 + (vy / len) * 0.15, 0.15, 0.95);
      ctx.beginPath();
      ctx.moveTo(screen[a * 3], screen[a * 3 + 1]);
      ctx.lineTo(screen[b * 3], screen[b * 3 + 1]);
      ctx.lineTo(screen[c * 3], screen[c * 3 + 1]);
      ctx.closePath();
      ctx.fillStyle = `rgb(${Math.round(baseColor[0] * light + 20)}, ${Math.round(baseColor[1] * light + 30)}, ${Math.round(baseColor[2] * light + 30)})`;
      ctx.fill();
    }
  }

  // Shared mesh shape for OBJ and FBX: flat typed arrays, area-weighted
  // vertex normals, and a fit-to-unit-cube center/scale for the camera.
  // `welds` (optional) maps each vertex to the vertex whose normal it shares,
  // so per-polygon-vertex splits for UVs still shade smoothly.
  function finalizeMesh(positions, indices, faceCount, objectCount, welds = null) {
    const vertexCount = positions.length / 3;
    let minX = Infinity, minY = Infinity, minZ = Infinity;
    let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;
    for (let i = 0; i < positions.length; i += 3) {
      const x = positions[i];
      const y = positions[i + 1];
      const z = positions[i + 2];
      if (x < minX) minX = x;
      if (y < minY) minY = y;
      if (z < minZ) minZ = z;
      if (x > maxX) maxX = x;
      if (y > maxY) maxY = y;
      if (z > maxZ) maxZ = z;
    }

    const normals = new Float32Array(positions.length);
    const weld = welds ? (index) => welds[index] * 3 : (index) => index * 3;
    for (let t = 0; t < indices.length; t += 3) {
      const a = weld(indices[t]);
      const b = weld(indices[t + 1]);
      const c = weld(indices[t + 2]);
      const ux = positions[b] - positions[a];
      const uy = positions[b + 1] - positions[a + 1];
      const uz = positions[b + 2] - positions[a + 2];
      const vx = positions[c] - positions[a];
      const vy = positions[c + 1] - positions[a + 1];
      const vz = positions[c + 2] - positions[a + 2];
      const nx = uy * vz - uz * vy;
      const ny = uz * vx - ux * vz;
      const nz = ux * vy - uy * vx;
      for (const v of [a, b, c]) {
        normals[v] += nx;
        normals[v + 1] += ny;
        normals[v + 2] += nz;
      }
    }
    for (let i = 0; i < normals.length; i += 3) {
      const len = Math.hypot(normals[i], normals[i + 1], normals[i + 2]);
      if (len > 0) {
        normals[i] /= len;
        normals[i + 1] /= len;
        normals[i + 2] /= len;
      } else {
        normals[i + 2] = 1;
      }
    }
    if (welds) {
      for (let v = 0; v < vertexCount; v += 1) {
        const from = welds[v] * 3;
        if (from !== v * 3) normals.set(normals.subarray(from, from + 3), v * 3);
      }
    }

    const hasBounds = vertexCount > 0;
    const maxSpan = hasBounds ? Math.max(maxX - minX, maxY - minY, maxZ - minZ) || 1 : 1;
    return {
      positions,
      normals,
      indices,
      vertexCount,
      faceCount,
      triangleCount: indices.length / 3,
      objectCount,
      center: hasBounds ? [(minX + maxX) * 0.5, (minY + maxY) * 0.5, (minZ + maxZ) * 0.5] : [0, 0, 0],
      scale: 2 / maxSpan,
      fitRadius: hasBounds ? Math.hypot(maxX - minX, maxY - minY, maxZ - minZ) / maxSpan : 1,
    };
  }

  function growFloat32(array, length) {
    if (length <= array.length) return array;
    const next = new Float32Array(Math.max(length, array.length * 2));
    next.set(array);
    return next;
  }

  function growUint32(array, length) {
    if (length <= array.length) return array;
    const next = new Uint32Array(Math.max(length, array.length * 2));
    next.set(array);
    return next;
  }

  // OBJ face corners have independent position/UV/normal indexes. Split at
  // UV and authored-normal seams; weld generated normals by source position.
  function parseObj(text) {
    const sourcePositions = [], sourceUvs = [], sourceNormals = [];
    let positions = new Float32Array(3 * 4096), uvs = new Float32Array(2 * 4096);
    let indices = new Uint32Array(3 * 8192);
    const corners = new Map(), weldByPosition = new Map(), welds = [], normals = [];
    const groups = [];
    let vertexCount = 0, indexCount = 0, faceCount = 0, objectCount = 0;
    let material = "", name = "", group = null, anyUvs = false;
    const resolve = (value, count) => {
      if (!/^-?\d+$/.test(value || "")) return -1;
      const raw = Number(value);
      const index = raw > 0 ? raw - 1 : count + raw;
      return raw && index >= 0 && index < count ? index : -1;
    };
    let start = 0;
    while (start < text.length) {
      let end = text.indexOf("\n", start);
      if (end < 0) end = text.length;
      const line = text.slice(start, end).split("#", 1)[0].trim();
      start = end + 1;
      const match = line.match(/^(\S+)\s+(.*)$/);
      if (!match) continue;
      const [, command, value] = match;
      if (["v", "vt", "vn"].includes(command)) {
        const values = value.trim().split(/\s+/).map(Number);
        const width = command === "vt" ? 2 : 3;
        if (values.length >= width && values.slice(0, width).every(Number.isFinite)) {
          (command === "v" ? sourcePositions : command === "vt" ? sourceUvs : sourceNormals).push(values.slice(0, width));
        }
      } else if (command === "usemtl") {
        material = value.trim();
        group = null;
      } else if (command === "o" || command === "g") {
        name = value.trim();
        objectCount += 1;
        group = null;
      } else if (command === "f") {
        const face = value.trim().split(/\s+/).map((token) => {
          const parts = token.split("/");
          return [resolve(parts[0], sourcePositions.length), resolve(parts[1], sourceUvs.length), resolve(parts[2], sourceNormals.length)];
        });
        // Reject the entire invalid polygon rather than inventing a smaller one.
        if (face.length < 3 || face.some(([position]) => position < 0)) continue;
        if (!group) {
          group = { material, name, start: indexCount, count: 0, hasUvs: true };
          groups.push(group);
        }
        faceCount += 1;
        const vertices = face.map(([position, uv, normal]) => {
          if (uv < 0) group.hasUvs = false;
          const key = `${position}/${uv}/${normal}`;
          if (corners.has(key)) return corners.get(key);
          const index = vertexCount++;
          corners.set(key, index);
          positions = growFloat32(positions, vertexCount * 3);
          uvs = growFloat32(uvs, vertexCount * 2);
          positions.set(sourcePositions[position], index * 3);
          if (uv >= 0) { uvs.set(sourceUvs[uv], index * 2); anyUvs = true; }
          if (!weldByPosition.has(position)) weldByPosition.set(position, index);
          welds.push(weldByPosition.get(position));
          normals.push(normal >= 0 ? sourceNormals[normal] : null);
          return index;
        });
        for (let i = 1; i + 1 < vertices.length; i += 1) {
          if (new Set([face[0][0], face[i][0], face[i + 1][0]]).size < 3) continue;
          indices = growUint32(indices, indexCount + 3);
          indices.set([vertices[0], vertices[i], vertices[i + 1]], indexCount);
          indexCount += 3;
          group.count += 3;
        }
      }
    }
    const mesh = finalizeMesh(positions.slice(0, vertexCount * 3), indices.slice(0, indexCount), faceCount, objectCount, welds);
    for (let index = 0; index < normals.length; index += 1) {
      const normal = normals[index];
      if (!normal) continue;
      const length = Math.hypot(...normal);
      if (length) mesh.normals.set(normal.map((value) => value / length), index * 3);
    }
    return Object.assign(mesh, { sourceVertexCount: sourcePositions.length, uvs: anyUvs ? uvs.slice(0, vertexCount * 2) : null, groups: groups.filter((group) => group.count) });
  }

  // Name-linked materials are preview candidates, not renderer slot proof.
  // A single linked material can shade an exported Mesh OBJ; multiple
  // candidates require an explicit usemtl name, never guessed slot order.
  function bindObjMaterials(model, relation) {
    const linked = relation.materials || [];
    const names = [...new Set(linked.map((material) => material.name).filter(Boolean))];
    for (const group of model.groups || []) {
      if (!group.material && names.length === 1) group.material = names[0];
      const candidates = linked.filter((material) => material.name?.toLowerCase() === group.material.toLowerCase());
      if (candidates.length !== 1) continue;
      const data = ASSET_STATE.relations[candidates[0].rel];
      if (!data) continue;
      const base = MODEL_BASE_TEXTURE_SLOTS.map((slot) => data.textures?.find((texture) => texture.slot === slot && texture.rel)).find(Boolean);
      group.textureRel = base?.rel || "";
      group.blend = data.blend || null;
    }
  }

  async function loadFbxAsset(rel) {
    await ensureAssetRelations();
    const cached = ASSET_STATE.fbxSummaryCache.get(rel);
    if (cached) return rememberCached(ASSET_STATE.fbxSummaryCache, rel, cached);

    const res = await fetch(assetHref(rel));
    if (!res.ok) throw new Error(`FBX HTTP ${res.status}`);
    const buffer = await res.arrayBuffer();
    const bytes = new Uint8Array(buffer);
    const header = new TextDecoder("ascii").decode(bytes.subarray(0, Math.min(bytes.length, 21)));
    let asset;
    if (header.startsWith("Kaydara FBX Binary")) {
      const tree = parseBinaryFbxTree(buffer);
      asset = { summary: summarizeFbxTree(tree), model: null, geometryError: "" };
      try {
        asset.model = await buildFbxMesh(tree, buffer);
      } catch (error) {
        asset.geometryError = String(error?.message || error);
      }
    } else {
      const text = new TextDecoder("utf-8").decode(bytes.subarray(0, Math.min(bytes.length, 512000)));
      asset = { summary: parseAsciiFbxSummary(text), model: null, geometryError: "" };
    }
    return rememberCached(ASSET_STATE.fbxSummaryCache, rel, asset);
  }

  function parseAsciiFbxSummary(text) {
    const summary = {
      format: "ASCII",
      version: 0,
      nodeCount: 0,
      counts: {},
      sampleNames: [],
    };

    const versionMatch = text.match(/FBXVersion:\s*(\d+)/);
    if (versionMatch) summary.version = Number(versionMatch[1]) || 0;

    const sampleSet = new Set();
    const nodeRe = /^\s*([A-Za-z][A-Za-z0-9_]+)\s*:/gm;
    let match;
    while ((match = nodeRe.exec(text))) {
      const name = match[1];
      summary.nodeCount += 1;
      summary.counts[name] = (summary.counts[name] || 0) + 1;
    }

    const sampleRe = /^\s*(Model|Geometry|Material|Texture|AnimationStack)\s*:\s*"([^"]+)"/gm;
    while ((match = sampleRe.exec(text)) && summary.sampleNames.length < 6) {
      const cleaned = cleanFbxSampleName(match[2]);
      if (!cleaned || sampleSet.has(cleaned)) continue;
      sampleSet.add(cleaned);
      summary.sampleNames.push(cleaned);
    }

    return summary;
  }

  // Binary FBX node tree. Scalar properties are decoded in place (64-bit
  // integers as decimal strings, so object ids stay exact); array properties
  // stay lazy descriptors that decodeFbxArray inflates on demand.
  function parseBinaryFbxTree(buffer) {
    const bytes = new Uint8Array(buffer);
    const view = new DataView(buffer);
    const decoder = new TextDecoder("utf-8");
    const version = bytes.length >= 27 ? view.getUint32(23, true) : 0;
    const is64 = version >= 7500;
    const wordSize = is64 ? 8 : 4;
    const nullRecordLen = is64 ? 25 : 13;
    const tree = { format: "Binary", version, nodes: [], complete: true };

    const readWord = (offset) => (is64 ? Number(view.getBigUint64(offset, true)) : view.getUint32(offset, true));

    function isNullRecord(offset) {
      if (offset + nullRecordLen > bytes.length) return false;
      for (let index = 0; index < nullRecordLen; index += 1) {
        if (bytes[offset + index] !== 0) return false;
      }
      return true;
    }

    function readProperty(offset) {
      const type = String.fromCharCode(bytes[offset]);
      const cursor = offset + 1;
      switch (type) {
        case "Y": return [view.getInt16(cursor, true), cursor + 2];
        case "C": return [bytes[cursor] !== 0, cursor + 1];
        case "I": return [view.getInt32(cursor, true), cursor + 4];
        case "F": return [view.getFloat32(cursor, true), cursor + 4];
        case "D": return [view.getFloat64(cursor, true), cursor + 8];
        case "L": return [view.getBigInt64(cursor, true).toString(), cursor + 8];
        case "R": return [null, cursor + 4 + view.getUint32(cursor, true)];
        case "S": {
          const length = view.getUint32(cursor, true);
          const end = Math.min(bytes.length, cursor + 4 + length);
          return [decoder.decode(bytes.subarray(cursor + 4, end)), cursor + 4 + length];
        }
        case "b":
        case "c":
        case "d":
        case "f":
        case "i":
        case "l": {
          const descriptor = {
            arrayType: type,
            length: view.getUint32(cursor, true),
            encoding: view.getUint32(cursor + 4, true),
            byteLength: view.getUint32(cursor + 8, true),
            offset: cursor + 12,
          };
          return [descriptor, descriptor.offset + descriptor.byteLength];
        }
        default:
          throw new Error(`Unsupported FBX property type: ${type}`);
      }
    }

    function parseNode(offset) {
      const endOffset = readWord(offset);
      const propertyCount = readWord(offset + wordSize);
      const propertyListLen = readWord(offset + wordSize * 2);
      let cursor = offset + wordSize * 3;
      const nameLen = bytes[cursor];
      cursor += 1;
      if (!endOffset || endOffset <= offset || endOffset > bytes.length) {
        throw new Error(`FBX node at ${offset} has invalid end offset ${endOffset}`);
      }
      const node = {
        name: decoder.decode(bytes.subarray(cursor, cursor + nameLen)),
        props: [],
        children: [],
      };
      cursor += nameLen;

      const propEnd = cursor + propertyListLen;
      for (let index = 0; index < propertyCount && cursor < propEnd; index += 1) {
        const [value, next] = readProperty(cursor);
        node.props.push(value);
        cursor = next;
      }
      cursor = propEnd;

      while (cursor + nullRecordLen <= endOffset) {
        if (isNullRecord(cursor)) {
          cursor += nullRecordLen;
          break;
        }
        const child = parseNode(cursor);
        node.children.push(child.node);
        cursor = child.nextOffset;
      }
      return { node, nextOffset: endOffset };
    }

    try {
      let cursor = 27;
      while (cursor + nullRecordLen <= bytes.length && !isNullRecord(cursor)) {
        const { node, nextOffset } = parseNode(cursor);
        tree.nodes.push(node);
        cursor = nextOffset;
      }
    } catch (error) {
      if (!tree.nodes.length) throw error;
      tree.complete = false;
    }
    return tree;
  }

  function summarizeFbxTree(tree) {
    const summary = {
      format: tree.format,
      version: tree.version,
      nodeCount: 0,
      counts: {},
      sampleNames: [],
    };
    const sampleSet = new Set();
    const sampleKinds = new Set(["Model", "Geometry", "Material", "Texture", "AnimationStack"]);
    const stack = [...tree.nodes];
    while (stack.length) {
      const node = stack.pop();
      summary.nodeCount += 1;
      summary.counts[node.name] = (summary.counts[node.name] || 0) + 1;
      if (sampleKinds.has(node.name) && summary.sampleNames.length < 6) {
        for (const value of node.props) {
          if (typeof value !== "string") continue;
          const cleaned = cleanFbxSampleName(value);
          if (!cleaned || /^-?\d+$/.test(cleaned) || sampleSet.has(cleaned)) continue;
          sampleSet.add(cleaned);
          summary.sampleNames.push(cleaned);
          break;
        }
      }
      stack.push(...node.children);
    }
    return summary;
  }

  async function inflateZlib(data) {
    if (typeof DecompressionStream !== "function") {
      throw new Error("compressed FBX arrays need DecompressionStream");
    }
    const stream = new Blob([data]).stream().pipeThrough(new DecompressionStream("deflate"));
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }

  async function decodeFbxArray(buffer, descriptor) {
    if (!descriptor || typeof descriptor !== "object" || !descriptor.arrayType) return null;
    const raw = new Uint8Array(buffer, descriptor.offset, descriptor.byteLength);
    let data;
    if (descriptor.encoding === 0) data = raw.slice();
    else if (descriptor.encoding === 1) data = await inflateZlib(raw);
    else throw new Error(`Unsupported FBX array encoding ${descriptor.encoding}`);

    const out = data.buffer;
    switch (descriptor.arrayType) {
      case "d": return new Float64Array(out, 0, descriptor.length);
      case "f": return new Float32Array(out, 0, descriptor.length);
      case "i": return new Int32Array(out, 0, descriptor.length);
      case "l": return Float64Array.from(new BigInt64Array(out, 0, descriptor.length), Number);
      default: return new Uint8Array(out, 0, descriptor.length);
    }
  }

  function fbxChild(node, name) {
    return node?.children.find((child) => child.name === name) || null;
  }

  // Properties70 P records: [name, type, label, flags, ...values].
  function fbxProperties70(node) {
    const props = new Map();
    for (const record of fbxChild(node, "Properties70")?.children || []) {
      if (record.name === "P" && typeof record.props[0] === "string") {
        props.set(record.props[0], record.props.slice(4));
      }
    }
    return props;
  }

  function mat4Multiply(a, b) {
    const out = new Float64Array(16);
    for (let col = 0; col < 4; col += 1) {
      for (let row = 0; row < 4; row += 1) {
        out[col * 4 + row] =
          a[row] * b[col * 4] + a[4 + row] * b[col * 4 + 1] + a[8 + row] * b[col * 4 + 2] + a[12 + row] * b[col * 4 + 3];
      }
    }
    return out;
  }

  // T * R * S with FBX's default XYZ Euler order (R = Rz * Ry * Rx).
  function mat4FromFbxTransform(translation, rotationDeg, scaling) {
    const [rx, ry, rz] = rotationDeg.map((deg) => (deg * Math.PI) / 180);
    const cx = Math.cos(rx), sx = Math.sin(rx);
    const cy = Math.cos(ry), sy = Math.sin(ry);
    const cz = Math.cos(rz), sz = Math.sin(rz);
    const r = [
      cy * cz, cy * sz, -sy,
      sx * sy * cz - cx * sz, sx * sy * sz + cx * cz, sx * cy,
      cx * sy * cz + sx * sz, cx * sy * sz - sx * cz, cx * cy,
    ];
    const m = new Float64Array(16);
    for (let col = 0; col < 3; col += 1) {
      m[col * 4] = r[col * 3] * scaling[col];
      m[col * 4 + 1] = r[col * 3 + 1] * scaling[col];
      m[col * 4 + 2] = r[col * 3 + 2] * scaling[col];
    }
    m[12] = translation[0];
    m[13] = translation[1];
    m[14] = translation[2];
    m[15] = 1;
    return m;
  }

  function fbxVector(props, name, fallback) {
    const value = props.get(name);
    if (!value || value.length < 3) return fallback;
    const vector = value.slice(0, 3).map(Number);
    return vector.every(Number.isFinite) ? vector : fallback;
  }

  function fbxModelLocalMatrix(model) {
    const props = fbxProperties70(model);
    const preRotation = fbxVector(props, "PreRotation", [0, 0, 0]);
    const local = mat4Multiply(
      mat4FromFbxTransform(fbxVector(props, "Lcl Translation", [0, 0, 0]), preRotation, [1, 1, 1]),
      mat4FromFbxTransform([0, 0, 0], fbxVector(props, "Lcl Rotation", [0, 0, 0]), fbxVector(props, "Lcl Scaling", [1, 1, 1])),
    );
    const geometric = mat4FromFbxTransform(
      fbxVector(props, "GeometricTranslation", [0, 0, 0]),
      fbxVector(props, "GeometricRotation", [0, 0, 0]),
      fbxVector(props, "GeometricScaling", [1, 1, 1]),
    );
    return { local, geometric };
  }

  // LayerElement* reader: values are addressed by polygon-vertex or by control
  // point (MappingInformationType), optionally through an index array.
  async function decodeFbxLayer(buffer, layer, valueName, indexName) {
    if (!layer) return null;
    const values = await decodeFbxArray(buffer, fbxChild(layer, valueName)?.props[0]);
    if (!values) return null;
    const reference = String(fbxChild(layer, "ReferenceInformationType")?.props[0] || "");
    const index = reference === "Direct" ? null : await decodeFbxArray(buffer, fbxChild(layer, indexName)?.props[0]);
    const byPolygonVertex = String(fbxChild(layer, "MappingInformationType")?.props[0] || "") === "ByPolygonVertex";
    return { values, index, byPolygonVertex };
  }

  function isFbxShadowName(name) {
    if (/shadow_?proxy|eyes?[_\s-]?shadow|hair[_\s-]?shadow/i.test(name)) return true;
    // `hs` abbreviates character hair-shadow meshes, but also occurs in
    // ordinary machine/region names. Require character context or an actual
    // terminal HS label; `hs_machine` must not hide a mechanical surface.
    return /(?:^|[_\s-])hs(?:[_\s\d-]|$)/i.test(name)
      && (/(?:^|[_\s-])(?:actor|npc|chr|character)(?:[_\s\d-]|$)/i.test(name)
        || /(?:^|[_\s-])hs(?:[_\s-]*\d+)?(?:[_-]lod\d+)?$/i.test(name));
  }

  // Bakes every Geometry "Mesh" into one indexed mesh in scene space, using
  // connected skin clusters for the stored skeleton pose, or its Model chain
  // for a rigid mesh. Vertices are emitted per polygon-vertex so UVs survive;
  // triangles use the owner Model's connected material slots.
  async function buildFbxMesh(tree, buffer) {
    const objects = tree.nodes.find((node) => node.name === "Objects");
    if (!objects) return null;
    const connections = tree.nodes.find((node) => node.name === "Connections");

    const models = new Map();
    const deformers = new Map();
    const materialNames = new Map();
    const geometries = [];
    for (const node of objects.children) {
      if (node.name === "Model") models.set(node.props[0], node);
      else if (node.name === "Deformer") deformers.set(node.props[0], node);
      else if (node.name === "Material") materialNames.set(node.props[0], String(node.props[1] || "").split("\u0000\u0001")[0]);
      else if (node.name === "Geometry" && node.props[2] === "Mesh") geometries.push(node);
    }

    const parentsOf = new Map();
    const childrenOf = new Map();
    const modelMaterials = new Map();
    for (const record of connections?.children || []) {
      if (record.name !== "C" || record.props[0] !== "OO") continue;
      const [, child, parent] = record.props;
      if (!parentsOf.has(child)) parentsOf.set(child, []);
      parentsOf.get(child).push(parent);
      if (!childrenOf.has(parent)) childrenOf.set(parent, []);
      childrenOf.get(parent).push(child);
      if (materialNames.has(child)) {
        if (!modelMaterials.has(parent)) modelMaterials.set(parent, []);
        modelMaterials.get(parent).push(materialNames.get(child));
      }
    }

    const worldCache = new Map();
    const worldMatrix = (id, depth = 0) => {
      if (worldCache.has(id)) return worldCache.get(id);
      const model = models.get(id);
      const { local } = fbxModelLocalMatrix(model);
      const parent = (parentsOf.get(id) || []).find((candidate) => models.has(candidate));
      const world = parent && depth < 256 ? mat4Multiply(worldMatrix(parent, depth + 1), local) : local;
      worldCache.set(id, world);
      return world;
    };

    const skinClusters = async (geometryId, vertexCount) => {
      const clusters = [];
      for (const skinId of childrenOf.get(geometryId) || []) {
        const skin = deformers.get(skinId);
        if (skin?.props[2] !== "Skin") continue;
        const skinningType = fbxChild(skin, "SkinningType")?.props[0];
        if (skinningType !== undefined && ![0, 1, "Rigid", "Linear"].includes(skinningType)) {
          throw new Error(`Unsupported FBX skinning type: ${skinningType}`);
        }
        for (const clusterId of childrenOf.get(skinId) || []) {
          const cluster = deformers.get(clusterId);
          if (cluster?.props[2] !== "Cluster") continue;
          const indexes = await decodeFbxArray(buffer, fbxChild(cluster, "Indexes")?.props[0]);
          const weights = await decodeFbxArray(buffer, fbxChild(cluster, "Weights")?.props[0]);
          if (!indexes?.length && !weights?.length) continue;
          const bone = (childrenOf.get(clusterId) || []).find((id) => models.has(id));
          const bind = await decodeFbxArray(buffer, fbxChild(cluster, "Transform")?.props[0]);
          const mode = String(fbxChild(cluster, "Mode")?.props[0] || "Normalize");
          if (!indexes || !weights || indexes.length !== weights.length || !bone || bind?.length !== 16
            || !Array.from(bind).every(Number.isFinite)) {
            throw new Error(`Invalid FBX skin cluster: ${clusterId}`);
          }
          if (!["Normalize", "Total1"].includes(mode)) throw new Error(`Unsupported FBX cluster mode: ${mode}`);
          for (let i = 0; i < indexes.length; i += 1) {
            if (!Number.isInteger(indexes[i]) || indexes[i] < 0 || indexes[i] >= vertexCount
              || !Number.isFinite(weights[i]) || weights[i] < 0) {
              throw new Error(`Invalid FBX skin influence: ${clusterId} at ${i}`);
            }
          }
          // The binary cluster's Transform is already mesh-to-bind-bone
          // (inverse(TransformLink) * meshBind), unlike the SDK getter's
          // meshBind matrix. Apply the current bone world matrix directly;
          // applying the mesh world matrix again would double its placement.
          clusters.push({ indexes, weights, mode, matrix: mat4Multiply(worldMatrix(bone), bind) });
        }
      }
      if (new Set(clusters.map((cluster) => cluster.mode)).size > 1) throw new Error("Mixed FBX cluster modes");
      return clusters;
    };

    const skinVertices = (vertices, clusters, meshWorld, geometric) => {
      if (!clusters.length) return null;
      const posed = new Float64Array(vertices.length);
      const weightSums = new Float64Array(vertices.length / 3);
      for (const { indexes, weights, matrix } of clusters) {
        const m = mat4Multiply(matrix, geometric);
        for (let i = 0; i < indexes.length; i += 1) {
          const cp = indexes[i], at = cp * 3, weight = weights[i];
          const x = vertices[at], y = vertices[at + 1], z = vertices[at + 2];
          posed[at] += weight * (m[0] * x + m[4] * y + m[8] * z + m[12]);
          posed[at + 1] += weight * (m[1] * x + m[5] * y + m[9] * z + m[13]);
          posed[at + 2] += weight * (m[2] * x + m[6] * y + m[10] * z + m[14]);
          weightSums[cp] += weight;
        }
      }
      for (let cp = 0; cp < weightSums.length; cp += 1) {
        const at = cp * 3, sum = weightSums[cp];
        if (sum > 0 && clusters[0].mode === "Normalize") {
          posed[at] /= sum; posed[at + 1] /= sum; posed[at + 2] /= sum;
        } else {
          // Total1 retains the uninfluenced fraction; an unweighted control
          // point in either mode keeps its ordinary mesh placement.
          const rest = sum > 0 ? 1 - sum : 1;
          const x = vertices[at], y = vertices[at + 1], z = vertices[at + 2], m = meshWorld;
          posed[at] += rest * (m[0] * x + m[4] * y + m[8] * z + m[12]);
          posed[at + 1] += rest * (m[1] * x + m[5] * y + m[9] * z + m[13]);
          posed[at + 2] += rest * (m[2] * x + m[6] * y + m[10] * z + m[14]);
        }
      }
      return posed;
    };

    // Prefabs carry every LOD and an untransformed shadow proxy beside the
    // render meshes; the viewer shows one LOD at a time and starts with the
    // shadow proxies off so copies do not overlap.
    const modelName = (id) => String(models.get(id)?.props[1] || "").split("\u0000\u0001")[0];
    const lodOf = (id) => {
      for (let current = id, depth = 0; current && depth < 256; depth += 1) {
        const match = modelName(current).match(/(?:^|[_-])lod(\d+)$/i);
        if (match) return Number(match[1]);
        current = (parentsOf.get(current) || []).find((candidate) => models.has(candidate));
      }
      return null;
    };
    const lodFamilyOf = (id) => {
      const chain = [];
      for (let current = id, depth = 0; current && depth < 256; depth += 1) {
        chain.unshift({ id: current, name: modelName(current) });
        current = (parentsOf.get(current) || []).find((candidate) => models.has(candidate));
      }
      const pattern = /(?:^|[_-])lod\d+$/i;
      const first = chain.findIndex((node) => pattern.test(node.name));
      if (first < 0) return null;
      // Keep the owning branch's identity: same-name sibling instances may
      // have different available LODs and must not suppress one another.
      return JSON.stringify([first ? chain[first - 1].id : 0,
        ...chain.slice(first).map((node) => node.name.replace(pattern, "_lod#").toLowerCase())]);
    };
    const isShadowPart = (id) => {
      for (let current = id, depth = 0; current && depth < 256; depth += 1) {
        if (isFbxShadowName(modelName(current))) return true;
        current = (parentsOf.get(current) || []).find((candidate) => models.has(candidate));
      }
      return false;
    };

    const parts = [];
    let totalVertices = 0;
    let faceCount = 0;
    let hasUvs = false;
    for (const geometry of geometries) {
      const vertices = await decodeFbxArray(buffer, fbxChild(geometry, "Vertices")?.props[0]);
      const polygonIndex = await decodeFbxArray(buffer, fbxChild(geometry, "PolygonVertexIndex")?.props[0]);
      if (!vertices || !polygonIndex || vertices.length < 9) continue;
      const vertexCount = Math.floor(vertices.length / 3);
      const uv = await decodeFbxLayer(buffer, fbxChild(geometry, "LayerElementUV"), "UV", "UVIndex");
      const materialLayer = fbxChild(geometry, "LayerElementMaterial");
      const polygonMaterials = await decodeFbxArray(buffer, fbxChild(materialLayer, "Materials")?.props[0]);
      const allSameMaterial = String(fbxChild(materialLayer, "MappingInformationType")?.props[0] || "") === "AllSame";
      const controlPoint = (pv) => (polygonIndex[pv] < 0 ? ~polygonIndex[pv] : polygonIndex[pv]);

      // Triangles as polygon-vertex indices, with each triangle's material slot.
      const triangles = [];
      const triangleSlots = [];
      let polygonStart = 0;
      let polygon = 0;
      for (let i = 0; i < polygonIndex.length; i += 1) {
        if (polygonIndex[i] >= 0) continue;
        faceCount += 1;
        const slot = polygonMaterials ? polygonMaterials[allSameMaterial ? 0 : polygon] || 0 : 0;
        const first = controlPoint(polygonStart);
        for (let k = polygonStart + 1; k + 1 <= i; k += 1) {
          const b = controlPoint(k);
          const c = controlPoint(k + 1);
          if (first === b || b === c || first === c) continue;
          if (first >= vertexCount || b >= vertexCount || c >= vertexCount) continue;
          triangles.push(polygonStart, k, k + 1);
          triangleSlots.push(slot);
        }
        polygonStart = i + 1;
        polygon += 1;
      }
      if (!triangles.length) continue;
      if (uv) hasUvs = true;

      // Every mesh object is kept so the viewer can toggle it; only the
      // lowest LOD outside the shadow proxy starts visible.
      const owners = (parentsOf.get(geometry.props[0]) || []).filter((id) => models.has(id));
      const clusters = await skinClusters(geometry.props[0], vertexCount);
      const placements = owners.length
        ? owners.map((id) => {
          const { geometric } = fbxModelLocalMatrix(models.get(id));
          return {
            object: id,
            transform: mat4Multiply(worldMatrix(id), geometric),
            geometric,
            materials: modelMaterials.get(id) || [],
          };
        })
        : [{ object: geometry.props[0], transform: null, materials: [] }];
      for (const { object, transform, geometric, materials } of placements) {
        const posed = transform ? skinVertices(vertices, clusters, transform, geometric) : null;
        parts.push({ object, vertices: posed || vertices, polygonIndex, controlPoint, uv, triangles, triangleSlots,
          transform: posed ? null : transform, materials });
        totalVertices += polygonIndex.length;
      }
    }
    if (!parts.length) return null;

    const meshObjects = [];
    const objectIndex = new Map();
    for (const { object } of parts) {
      if (objectIndex.has(object)) continue;
      objectIndex.set(object, meshObjects.length);
      meshObjects.push({
        id: object,
        name: models.has(object) ? modelName(object) : "Mesh",
        lod: models.has(object) ? lodOf(object) : null,
        lodFamily: models.has(object) ? lodFamilyOf(object) : null,
        kind: models.has(object) && isShadowPart(object) ? "shadow" : null,
        materials: new Set(),
      });
    }
    for (const { object, materials } of parts) {
      for (const material of materials) meshObjects[objectIndex.get(object)].materials.add(material);
    }
    // Effect parts (fx meshes or fx materials) start hidden like shadow proxies,
    // unless the prefab is nothing but effects.
    const vfxPattern = /(?:^|[_\s-])v?fx(?:part)?(?:[_\s\d-]|$)|effect/i;
    for (const object of meshObjects) {
      if (!object.kind && [...object.materials].some(isFbxShadowName)) {
        object.kind = "shadow";
      }
      if (!object.kind && (vfxPattern.test(object.name) || [...object.materials].some((name) => vfxPattern.test(name)))) {
        object.kind = "vfx";
      }
      delete object.materials;
    }
    const hasPlain = meshObjects.some((object) => !object.kind);
    const lodLevels = [...new Set(meshObjects.map((object) => object.lod).filter((lod) => lod !== null))].sort((a, b) => a - b);
    const bestByFamily = new Map();
    for (const object of meshObjects) {
      if (object.lod === null) continue;
      bestByFamily.set(object.lodFamily, Math.min(bestByFamily.get(object.lodFamily) ?? Infinity, object.lod));
    }
    const visibleLevels = [];
    for (const object of meshObjects) {
      object.defaultVisible = object.kind === "shadow" ? false : object.kind === "vfx" ? !hasPlain : true;
      object.bestLod = object.lod === null ? null : bestByFamily.get(object.lodFamily);
      if (object.defaultVisible && object.lod !== null) visibleLevels.push(object.bestLod);
    }
    // A low-detail-only body and a multi-LOD accessory are independent parts.
    // A single global LOD number used to hide the whole body. This is a stored
    // geometry inspection preset, not a claim about the game's LOD selection.
    const mixedLods = new Set(visibleLevels).size > 1;
    const lod = mixedLods ? "best" : visibleLevels.length ? visibleLevels.reduce((a, b) => Math.min(a, b)) : lodLevels[0] ?? null;
    for (const object of meshObjects) object.framed = object.defaultVisible && (object.lod === null || object.lod === (lod === "best" ? object.bestLod : lod));

    // Group triangles by object and material name so each group is one draw
    // call that can be hidden with its object.
    const groupKey = (object, material) => `${objectIndex.get(object)}\u0000${material}`;
    const groupCounts = new Map();
    for (const { object, triangleSlots, materials } of parts) {
      for (const slot of triangleSlots) {
        const key = groupKey(object, materials[slot] || "");
        groupCounts.set(key, (groupCounts.get(key) || 0) + 3);
      }
    }
    const groups = [];
    const groupCursor = new Map();
    let totalIndices = 0;
    for (const [key, count] of groupCounts) {
      const split = key.indexOf("\u0000");
      groups.push({ material: key.slice(split + 1), object: Number(key.slice(0, split)), start: totalIndices, count });
      groupCursor.set(key, totalIndices);
      totalIndices += count;
    }

    const positions = new Float32Array(totalVertices * 3);
    const uvs = hasUvs ? new Float32Array(totalVertices * 2) : null;
    const welds = new Uint32Array(totalVertices);
    const indices = new Uint32Array(totalIndices);
    let vertexBase = 0;
    let minX = Infinity, minY = Infinity, minZ = Infinity;
    let maxX = -Infinity, maxY = -Infinity, maxZ = -Infinity;
    for (const { object, vertices, polygonIndex, controlPoint, uv, triangles, triangleSlots, transform: m, materials } of parts) {
      const framed = meshObjects[objectIndex.get(object)].framed;
      const firstUse = new Int32Array(Math.floor(vertices.length / 3)).fill(-1);
      for (let pv = 0; pv < polygonIndex.length; pv += 1) {
        const cp = controlPoint(pv);
        const x = vertices[cp * 3];
        const y = vertices[cp * 3 + 1];
        const z = vertices[cp * 3 + 2];
        const out = (vertexBase + pv) * 3;
        if (m) {
          positions[out] = m[0] * x + m[4] * y + m[8] * z + m[12];
          positions[out + 1] = m[1] * x + m[5] * y + m[9] * z + m[13];
          positions[out + 2] = m[2] * x + m[6] * y + m[10] * z + m[14];
        } else {
          positions[out] = x;
          positions[out + 1] = y;
          positions[out + 2] = z;
        }
        if (framed) {
          minX = Math.min(minX, positions[out]); maxX = Math.max(maxX, positions[out]);
          minY = Math.min(minY, positions[out + 1]); maxY = Math.max(maxY, positions[out + 1]);
          minZ = Math.min(minZ, positions[out + 2]); maxZ = Math.max(maxZ, positions[out + 2]);
        }
        if (firstUse[cp] < 0) firstUse[cp] = pv;
        welds[vertexBase + pv] = vertexBase + firstUse[cp];
        if (uv) {
          const at = uv.byPolygonVertex ? pv : cp;
          const u = uv.index ? uv.index[at] : at;
          uvs[(vertexBase + pv) * 2] = uv.values[u * 2] || 0;
          uvs[(vertexBase + pv) * 2 + 1] = uv.values[u * 2 + 1] || 0;
        }
      }
      for (let t = 0; t < triangleSlots.length; t += 1) {
        const key = groupKey(object, materials[triangleSlots[t]] || "");
        let cursor = groupCursor.get(key);
        indices[cursor++] = vertexBase + triangles[t * 3];
        indices[cursor++] = vertexBase + triangles[t * 3 + 1];
        indices[cursor++] = vertexBase + triangles[t * 3 + 2];
        groupCursor.set(key, cursor);
      }
      vertexBase += polygonIndex.length;
    }
    const mesh = finalizeMesh(positions, indices, faceCount, meshObjects.length, welds);
    // Frame the objects shown by default, not hidden LODs or proxies.
    if (minX <= maxX) {
      mesh.center = [(minX + maxX) * 0.5, (minY + maxY) * 0.5, (minZ + maxZ) * 0.5];
      mesh.scale = 2 / (Math.max(maxX - minX, maxY - minY, maxZ - minZ) || 1);
      mesh.fitRadius = Math.hypot(maxX - minX, maxY - minY, maxZ - minZ) * mesh.scale * 0.5;
    }
    for (const object of meshObjects) {
      object.visible = object.defaultVisible;
      delete object.framed;
    }
    return Object.assign(mesh, { uvs, groups, objects: meshObjects, lods: lodLevels, lod, mixedLods });
  }

  function cleanFbxSampleName(value) {
    return String(value || "")
      .replace(/\u0000/g, " ")
      .replace(/\s+\u0001\S*$/, "")
      .replace(/^[A-Za-z]+::/, "")
      .replace(/\s+/g, " ")
      .trim();
  }

  function assetHref(relPath) {
    return exportFullHref(relPath, ASSET_STATE.sourceRoots, ASSET_STATE.exportRoot);
  }

  function countBy(arr, fn) {
    const out = {};
    for (const item of arr) {
      const key = fn(item);
      out[key] = (out[key] || 0) + 1;
    }
    return out;
  }

  // A Sprite crop has pixels but no file of its own.
  function formatAssetSize(entry) {
    return entry && entry.cropOf ? entry.pixelSize : formatBytes(entry ? entry.size : 0);
  }

  function formatBytes(bytes) {
    const units = ["B", "KB", "MB", "GB"];
    let value = Number(bytes || 0);
    let unitIndex = 0;
    while (value >= 1024 && unitIndex < units.length - 1) {
      value /= 1024;
      unitIndex += 1;
    }
    const digits = value >= 100 || unitIndex === 0 ? 0 : value >= 10 ? 1 : 2;
    return `${value.toFixed(digits)} ${units[unitIndex]}`;
  }

  function formatDuration(seconds) {
    const total = Math.max(0, Math.round(Number(seconds) || 0));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    if (h) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
    return `${m}:${String(s).padStart(2, "0")}`;
  }

  function clamp(value, min, max) {
    return Math.min(max, Math.max(min, value));
  }

  async function copyTextToClipboard(text) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_error) {
      return false;
    }
  }

  function init() {
    ASSET_STATE.previewBackground = resolveInitialPreviewBackground();
    setAssetUiLocale(resolveInitialUiLocale(), { refresh: false });
    syncDebugViewVisibility();
    bindViewTabs();
    bindAssetEvents();
    window.addEventListener("webui:ui-locale-changed", (event) => {
      setAssetUiLocale(event.detail && event.detail.locale);
    });
    window.addEventListener("webui:debug-changed", syncDebugViewVisibility);
    ensureAssetPanelToggle();
    window.WebUI.locateCurrent?.bind($("#asset-locate-current"), locateSelectedAsset);
    setActiveView(resolveViewFromHash(), { updateHash: false });
    Object.assign(window.WebUI, { setViewBusy, setShellStatus, clearShellStatus, setActiveView });
  }

  init();
})();
