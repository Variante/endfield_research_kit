// 3D scene viewer for the Map page.
//
// Assembles a level from `data/map_recovery/scene3d/<level>/`, which
// `scripts/webui/map/build_map_scene3d.py` publishes from InitChunkData draw
// references (component 18 object-to-world matrix, components 68-74
// material/mesh StringPathHash pairs).  Meshes and textures are read straight
// from the export's decoded Unity OBJ/PNG files.  Chunks stream by distance;
// the level's global chunk is always resident.
//
// Evidence: matrix and hash framing are exact, the draw-ref column roles are
// structuralOnly, and each mesh/material carries its own resolution tier
// (exact asset-map PathID, conditional unique name, unresolved).  Shading is
// an HGRP-style approximation (base colour, MRO, normal map, sun + sky
// ambient), not the retail lighting pipeline.  The draw-ref layout follows the
// 0BSD endfield-noclip project (https://github.com/mary-ext/endfield-noclip).
(function () {
  "use strict";

  const DATA_ROOT = "data/map_recovery/scene3d";
  const LOAD_RADIUS_CHUNKS = 2; // 5x5 cells of 128 m; dense dungeon cells carry ~6k draws
  const UNLOAD_RADIUS_CHUNKS = 3;
  const MAX_FETCHES = 6;
  const TIER_COLORS = {
    exact: [0.25, 0.75, 0.4],
    conditional: [0.95, 0.68, 0.2],
    unresolved: [0.85, 0.25, 0.25],
    none: [0.55, 0.55, 0.6],
  };

  const S = {
    host: null,
    gl: null,
    canvas: null,
    levels: [],
    level: null,
    levelId: "",
    chunks: new Map(), // key -> {row, state, instances}
    meshes: new Map(), // meshIdx -> {state, groups, refs}
    textures: new Map(), // rel -> {tex, state}
    batches: null,
    fetches: 0,
    queue: [],
    camera: { pos: [0, 50, 0], yaw: 0, pitch: -0.3, speed: 40 },
    keys: new Set(),
    mode: "shaded",
    running: false,
    generation: 0,
    stats: { drawn: 0, triangles: 0 },
  };

  // ---------------------------------------------------------------- math
  function perspective(fovy, aspect, near, far) {
    const f = 1 / Math.tan(fovy / 2);
    const nf = 1 / (near - far);
    return [f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) * nf, -1, 0, 0, 2 * far * near * nf, 0];
  }
  function cameraBasis(cam) {
    const cp = Math.cos(cam.pitch);
    const fwd = [Math.sin(cam.yaw) * cp, Math.sin(cam.pitch), -Math.cos(cam.yaw) * cp];
    const right = [Math.cos(cam.yaw), 0, Math.sin(cam.yaw)];
    const up = [
      right[1] * fwd[2] - right[2] * fwd[1],
      right[2] * fwd[0] - right[0] * fwd[2],
      right[0] * fwd[1] - right[1] * fwd[0],
    ];
    return { fwd, right, up };
  }
  function viewMatrix(cam) {
    const { fwd, right, up } = cameraBasis(cam);
    const p = cam.pos;
    const dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
    return [
      right[0], up[0], -fwd[0], 0,
      right[1], up[1], -fwd[1], 0,
      right[2], up[2], -fwd[2], 0,
      -dot(right, p), -dot(up, p), dot(fwd, p), 1,
    ];
  }
  function det3(m) {
    return m[0] * (m[5] * m[10] - m[6] * m[9]) - m[4] * (m[1] * m[10] - m[2] * m[9]) + m[8] * (m[1] * m[6] - m[2] * m[5]);
  }

  // ---------------------------------------------------------------- GL
  const VS = `#version 300 es
  layout(location=0) in vec3 aPos;
  layout(location=1) in vec3 aNormal;
  layout(location=2) in vec2 aUv;
  layout(location=3) in vec4 aM0;
  layout(location=4) in vec4 aM1;
  layout(location=5) in vec4 aM2;
  layout(location=6) in vec4 aM3;
  uniform mat4 uView;
  uniform mat4 uProj;
  out vec3 vWorld;
  out vec3 vNormal;
  out vec2 vUv;
  void main() {
    mat4 m = mat4(aM0, aM1, aM2, aM3);
    vec4 w = m * vec4(aPos, 1.0);
    vWorld = w.xyz;
    vNormal = mat3(m) * aNormal;
    vUv = aUv;
    gl_Position = uProj * uView * w;
  }`;

  const FS = `#version 300 es
  precision highp float;
  in vec3 vWorld;
  in vec3 vNormal;
  in vec2 vUv;
  uniform sampler2D uBase;
  uniform sampler2D uMro;
  uniform sampler2D uNormalMap;
  uniform sampler2D uEmissive;
  uniform int uHas; // 1 base, 2 mro, 4 normal, 8 emissive
  uniform vec4 uBaseColor;
  uniform vec3 uEmissiveColor;
  uniform vec4 uST;
  uniform float uBrighter;
  uniform float uTintCover;
  uniform float uMetallic;
  uniform vec2 uRoughness;
  uniform float uNormalScale;
  uniform float uClip;
  uniform int uMode; // 0 shaded, 1 tier, 2 normals, 3 unlit
  uniform vec3 uTierColor;
  uniform vec3 uEye;
  uniform vec3 uSun;
  out vec4 outColor;

  vec3 toLinear(vec3 c) { return pow(c, vec3(2.2)); }
  vec3 toSrgb(vec3 c) { return pow(c, vec3(1.0 / 2.2)); }

  void main() {
    vec2 uv = vUv * uST.xy + uST.zw;
    vec3 n = normalize(vNormal);
    if (!gl_FrontFacing) n = -n;
    vec4 base = vec4(1.0);
    if ((uHas & 1) != 0) base = texture(uBase, uv);
    if (uClip > 0.0 && base.a < uClip) discard;
    if ((uHas & 4) != 0 && uMode == 0) {
      vec3 dp1 = dFdx(vWorld), dp2 = dFdy(vWorld);
      vec2 du1 = dFdx(uv), du2 = dFdy(uv);
      vec3 t = dp1 * du2.y - dp2 * du1.y;
      vec3 b = dp2 * du1.x - dp1 * du2.x;
      float len = max(length(t), length(b));
      if (len > 1e-8) {
        vec2 nm = texture(uNormalMap, uv).rg * 2.0 - 1.0;
        nm *= uNormalScale;
        float nz = sqrt(max(0.0, 1.0 - dot(nm, nm)));
        n = normalize(normalize(t) * nm.x + normalize(b) * nm.y + n * nz);
      }
    }
    if (uMode == 2) { outColor = vec4(n * 0.5 + 0.5, 1.0); return; }
    vec3 albedo = toLinear(base.rgb) * uBaseColor.rgb;
    albedo = mix(clamp(albedo * uBrighter, 0.0, 1.0), uBaseColor.rgb, uTintCover);
    float alpha = base.a * uBaseColor.a;
    if (uMode == 1) {
      float l = 0.55 + 0.45 * max(dot(n, uSun), 0.0);
      outColor = vec4(uTierColor * l, 1.0);
      return;
    }
    // _EmissiveColor alone is a multiplier (often white); only an emissive map emits.
    vec3 emissive = vec3(0.0);
    if ((uHas & 8) != 0) emissive = uEmissiveColor * toLinear(texture(uEmissive, uv).rgb);
    if (uMode == 3) { outColor = vec4(toSrgb(albedo + emissive), alpha); return; }
    float metal = uMetallic, rough = mix(uRoughness.x, uRoughness.y, 0.5), ao = 1.0;
    if ((uHas & 2) != 0) {
      vec3 mro = texture(uMro, uv).rgb;
      metal = mro.r * uMetallic;
      rough = mix(uRoughness.x, uRoughness.y, mro.g);
      ao = mro.b;
    }
    rough = clamp(rough, 0.04, 1.0);
    vec3 v = normalize(uEye - vWorld);
    vec3 l = uSun;
    vec3 h = normalize(v + l);
    float nl = max(dot(n, l), 0.0);
    float nv = max(dot(n, v), 1e-3);
    float nh = max(dot(n, h), 0.0);
    float a = rough * rough;
    float a2 = a * a;
    float d = nh * nh * (a2 - 1.0) + 1.0;
    float D = a2 / (3.14159 * d * d);
    float k = a * 0.5;
    float G = (nl / (nl * (1.0 - k) + k)) * (nv / (nv * (1.0 - k) + k));
    vec3 f0 = mix(vec3(0.04), albedo, metal);
    vec3 F = f0 + (1.0 - f0) * pow(1.0 - max(dot(h, v), 0.0), 5.0);
    vec3 spec = D * G * F / max(4.0 * nl * nv, 1e-3);
    vec3 diffuse = (1.0 - F) * (1.0 - metal) * albedo / 3.14159;
    vec3 sunColor = vec3(1.0, 0.96, 0.9) * 3.0;
    float sky = n.y * 0.5 + 0.5;
    vec3 ambient = mix(vec3(0.16, 0.15, 0.14), vec3(0.32, 0.36, 0.42), sky) * albedo * ao;
    vec3 color = (diffuse + spec) * sunColor * nl + ambient + emissive;
    color = color / (1.0 + color);
    outColor = vec4(toSrgb(color), alpha);
  }`;

  function compile(gl, type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      throw new Error(gl.getShaderInfoLog(shader) || "shader compile failed");
    }
    return shader;
  }

  function createGl(canvas) {
    const gl = canvas.getContext("webgl2", { antialias: true });
    if (!gl) return null;
    const program = gl.createProgram();
    gl.attachShader(program, compile(gl, gl.VERTEX_SHADER, VS));
    gl.attachShader(program, compile(gl, gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
      throw new Error(gl.getProgramInfoLog(program) || "program link failed");
    }
    const u = {};
    for (const name of [
      "uView", "uProj", "uBase", "uMro", "uNormalMap", "uEmissive", "uHas", "uBaseColor", "uEmissiveColor",
      "uST", "uBrighter", "uTintCover", "uMetallic", "uRoughness", "uNormalScale", "uClip", "uMode",
      "uTierColor", "uEye", "uSun",
    ]) u[name] = gl.getUniformLocation(program, name);
    const white = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, white);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([255, 255, 255, 255]));
    return { gl, program, u, white };
  }

  // ---------------------------------------------------------------- OBJ
  // AnimeStudio writes one `g <Name>` vertex block followed by one
  // `g <Name>_<k>` face group per submesh, with X negated and the winding
  // reversed, so faces stay counter-clockwise in the mirrored frame.
  function parseObj(text) {
    const pos = [], nor = [], uv = [];
    const groups = [];
    let current = null;
    const lines = text.split("\n");
    for (let i = 0; i < lines.length; i += 1) {
      const line = lines[i];
      const c0 = line.charCodeAt(0), c1 = line.charCodeAt(1);
      if (c0 === 118) { // v
        const p = line.split(/\s+/);
        if (c1 === 32) pos.push(+p[1], +p[2], +p[3]);
        else if (c1 === 110) nor.push(+p[1], +p[2], +p[3]);
        else if (c1 === 116) uv.push(+p[1], +p[2]);
      } else if (c0 === 103 && c1 === 32) { // g
        const name = line.slice(2).trim();
        const match = /_(\d+)$/.exec(name);
        current = { submesh: match ? Number(match[1]) : groups.length, faces: [] };
        groups.push(current);
      } else if (c0 === 102 && c1 === 32) { // f
        if (!current) { current = { submesh: 0, faces: [] }; groups.push(current); }
        const p = line.trim().split(/\s+/);
        for (let k = 2; k + 1 < p.length; k += 1) current.faces.push(p[1], p[k], p[k + 1]);
      }
    }
    const faceGroups = groups.filter((g) => g.faces.length);
    // Index submeshes by their order among face groups, which matches the
    // renderer's submesh index for AnimeStudio OBJ output.
    const remap = new Map();
    const outPos = [], outNor = [], outUv = [];
    const submeshes = [];
    const indices = [];
    for (let gi = 0; gi < faceGroups.length; gi += 1) {
      const start = indices.length;
      for (const token of faceGroups[gi].faces) {
        let index = remap.get(token);
        if (index === undefined) {
          const parts = token.split("/");
          const vi = (parseInt(parts[0], 10) - 1) * 3;
          const ti = parts[1] ? (parseInt(parts[1], 10) - 1) * 2 : -1;
          const ni = parts[2] ? (parseInt(parts[2], 10) - 1) * 3 : -1;
          index = outPos.length / 3;
          outPos.push(pos[vi], pos[vi + 1], pos[vi + 2]);
          if (ni >= 0) outNor.push(nor[ni], nor[ni + 1], nor[ni + 2]);
          else outNor.push(0, 1, 0);
          if (ti >= 0) outUv.push(uv[ti], uv[ti + 1]);
          else outUv.push(0, 0);
          remap.set(token, index);
        }
        indices.push(index);
      }
      submeshes.push({ start, count: indices.length - start });
    }
    return {
      positions: new Float32Array(outPos),
      normals: new Float32Array(outNor),
      uvs: new Float32Array(outUv),
      indices: outPos.length / 3 > 65535 ? new Uint32Array(indices) : new Uint16Array(indices),
      submeshes,
    };
  }

  function exportHref(rel) {
    return `/export_full/game/${String(rel).split("/").map(encodeURIComponent).join("/")}`;
  }

  // ---------------------------------------------------------------- loading
  function pump() {
    while (S.fetches < MAX_FETCHES && S.queue.length) {
      const job = S.queue.shift();
      S.fetches += 1;
      job().catch(() => {}).finally(() => {
        S.fetches -= 1;
        S.batches = null;
        pump();
      });
    }
  }

  function requestMesh(meshIdx) {
    let entry = S.meshes.get(meshIdx);
    if (entry) return entry;
    const info = S.level.meshes[meshIdx];
    entry = { state: "pending", info, refs: 0 };
    S.meshes.set(meshIdx, entry);
    if (!info || !info.rel) { entry.state = "missing"; return entry; }
    const generation = S.generation;
    S.queue.push(async () => {
      const response = await fetch(exportHref(info.rel));
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      const parsed = parseObj(await response.text());
      if (generation !== S.generation || !S.gl) return;
      const { gl } = S.gl;
      const vao = gl.createVertexArray();
      gl.bindVertexArray(vao);
      const buffers = [];
      const attrib = (loc, data, size) => {
        const buffer = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
        gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
        gl.enableVertexAttribArray(loc);
        gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0);
        buffers.push(buffer);
      };
      attrib(0, parsed.positions, 3);
      attrib(1, parsed.normals, 3);
      attrib(2, parsed.uvs, 2);
      const ibo = gl.createBuffer();
      gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
      gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, parsed.indices, gl.STATIC_DRAW);
      buffers.push(ibo);
      const instanceBuffer = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, instanceBuffer);
      for (let k = 0; k < 4; k += 1) {
        gl.enableVertexAttribArray(3 + k);
        gl.vertexAttribPointer(3 + k, 4, gl.FLOAT, false, 64, k * 16);
        gl.vertexAttribDivisor(3 + k, 1);
      }
      buffers.push(instanceBuffer);
      gl.bindVertexArray(null);
      Object.assign(entry, {
        state: "ready",
        vao,
        buffers,
        instanceBuffer,
        indexType: parsed.indices instanceof Uint32Array ? gl.UNSIGNED_INT : gl.UNSIGNED_SHORT,
        indexBytes: parsed.indices.BYTES_PER_ELEMENT,
        submeshes: parsed.submeshes,
      });
    });
    pump();
    return entry;
  }

  function requestTexture(rel) {
    let entry = S.textures.get(rel);
    if (entry) return entry;
    entry = { state: "pending", tex: null };
    S.textures.set(rel, entry);
    const generation = S.generation;
    S.queue.push(() => new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => {
        if (generation !== S.generation || !S.gl) { resolve(); return; }
        const { gl } = S.gl;
        const tex = gl.createTexture();
        gl.bindTexture(gl.TEXTURE_2D, tex);
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
        gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, image);
        gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
        gl.generateMipmap(gl.TEXTURE_2D);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
        gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
        entry.tex = tex;
        entry.state = "ready";
        resolve();
      };
      image.onerror = () => { entry.state = "missing"; reject(new Error(rel)); };
      image.src = exportHref(rel);
    }));
    pump();
    return entry;
  }

  function chunkUrl(key) {
    return `${DATA_ROOT}/${encodeURIComponent(S.levelId)}/chunks/${encodeURIComponent(key)}.json`;
  }

  function loadChunk(row) {
    const record = { row, state: "pending", instances: [] };
    S.chunks.set(row.key, record);
    const generation = S.generation;
    fetch(chunkUrl(row.key))
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((data) => {
        if (generation !== S.generation || S.chunks.get(row.key) !== record) return;
        record.instances = data.instances || [];
        record.state = "ready";
        for (const inst of record.instances) {
          for (const [meshIdx] of inst.d) {
            const mesh = requestMesh(meshIdx);
            mesh.refs += 1;
          }
        }
        S.batches = null;
      })
      .catch(() => { record.state = "failed"; });
  }

  function unloadChunk(key) {
    const record = S.chunks.get(key);
    if (!record) return;
    S.chunks.delete(key);
    for (const inst of record.instances) {
      for (const [meshIdx] of inst.d) {
        const mesh = S.meshes.get(meshIdx);
        if (mesh) mesh.refs -= 1;
      }
    }
    S.batches = null;
  }

  function streamChunks() {
    if (!S.level) return;
    const size = S.level.chunkSize || 128;
    const cx = Math.floor(-S.camera.pos[0] / size);
    const cz = Math.floor(S.camera.pos[2] / size);
    for (const row of S.level.chunks) {
      const resident = S.chunks.has(row.key);
      if (row.x === null || row.x === undefined) {
        if (!resident) loadChunk(row);
        continue;
      }
      const dist = Math.max(Math.abs(row.x - cx), Math.abs(row.z - cz));
      if (!resident && dist <= LOAD_RADIUS_CHUNKS) loadChunk(row);
      else if (resident && dist > UNLOAD_RADIUS_CHUNKS) unloadChunk(row.key);
    }
  }

  // Groups resident instances by mesh/submesh/material and mirror sign so
  // each batch is one instanced draw with a consistent front-face winding.
  function buildBatches() {
    const map = new Map();
    for (const record of S.chunks.values()) {
      if (record.state !== "ready") continue;
      for (const inst of record.instances) {
        const mirrored = det3(inst.m) < 0;
        for (const [meshIdx, submesh, matIdx] of inst.d) {
          const key = `${meshIdx}:${submesh}:${matIdx}:${mirrored ? 1 : 0}`;
          let batch = map.get(key);
          if (!batch) {
            batch = { meshIdx, submesh, matIdx, mirrored, matrices: [] };
            map.set(key, batch);
          }
          batch.matrices.push(inst.m);
        }
      }
    }
    const batches = [...map.values()];
    for (const batch of batches) {
      const data = new Float32Array(batch.matrices.length * 16);
      batch.matrices.forEach((m, i) => data.set(m, i * 16));
      batch.data = data;
      batch.count = batch.matrices.length;
      const mat = S.level.materials[batch.matIdx] || null;
      batch.material = mat;
      batch.transparent = Boolean(mat && mat.blend);
      batch.queue = mat && mat.queue ? mat.queue : 2000;
      if (mat && mat.textures) for (const t of Object.values(mat.textures)) if (t && t.rel) requestTexture(t.rel);
    }
    batches.sort((a, b) => (a.transparent - b.transparent) || (a.queue - b.queue));
    return batches;
  }

  // ---------------------------------------------------------------- draw
  function bindMaterial(ctx, mat, batch) {
    const { gl, u, white } = ctx;
    let has = 0;
    const slot = (unit, name, bit, uniform) => {
      const t = mat && mat.textures && mat.textures[name];
      const entry = t && t.rel ? S.textures.get(t.rel) : null;
      gl.activeTexture(gl.TEXTURE0 + unit);
      if (entry && entry.state === "ready") { gl.bindTexture(gl.TEXTURE_2D, entry.tex); has |= bit; }
      else gl.bindTexture(gl.TEXTURE_2D, white);
      gl.uniform1i(uniform, unit);
    };
    slot(0, "base", 1, u.uBase);
    slot(1, "mro", 2, u.uMro);
    slot(2, "normal", 4, u.uNormalMap);
    slot(3, "emissive", 8, u.uEmissive);
    gl.uniform1i(u.uHas, has);
    const baseColor = (mat && mat.baseColor) || [1, 1, 1, 1];
    gl.uniform4f(u.uBaseColor, baseColor[0], baseColor[1], baseColor[2], baseColor[3] ?? 1);
    const em = (mat && mat.emissiveColor) || [0, 0, 0];
    gl.uniform3f(u.uEmissiveColor, em[0], em[1], em[2]);
    const st = (mat && mat.textures && mat.textures.base && mat.textures.base.st) || [1, 1, 0, 0];
    gl.uniform4f(u.uST, st[0], st[1], st[2], st[3]);
    const num = (key, fallback) => (mat && Number.isFinite(mat[key]) ? mat[key] : fallback);
    gl.uniform1f(u.uBrighter, num("BaseColorBrighterScale", 1));
    gl.uniform1f(u.uTintCover, num("BaseColorTintCover", 0));
    gl.uniform1f(u.uMetallic, num("Metallic", 1));
    gl.uniform2f(u.uRoughness, num("RoughnessMin", 0), num("RoughnessMax", 1));
    gl.uniform1f(u.uNormalScale, num("NormalScale", 1));
    gl.uniform1f(u.uClip, mat && mat.clip ? (Number(mat.clip) || 0.5) : 0);
    const meshTier = (S.level.meshes[batch.meshIdx] || {}).tier || "none";
    const matTier = mat ? mat.tier || "none" : "none";
    const tier = meshTier === "exact" && matTier === "exact" ? "exact"
      : meshTier === "unresolved" ? "unresolved" : (mat ? "conditional" : "none");
    const color = TIER_COLORS[tier];
    gl.uniform3f(u.uTierColor, color[0], color[1], color[2]);
    const cull = mat ? (Number.isFinite(mat.CullMode) ? mat.CullMode : 2) : 2;
    if (cull === 0 || S.mode === "tier") gl.disable(gl.CULL_FACE);
    else {
      gl.enable(gl.CULL_FACE);
      // Unity CullMode 1 = front, 2 = back; a mirrored instance flips winding.
      gl.cullFace(cull === 1 ? gl.FRONT : gl.BACK);
      gl.frontFace(batch.mirrored ? gl.CW : gl.CCW);
    }
    if (batch.transparent && S.mode !== "tier") {
      gl.enable(gl.BLEND);
      const blend = mat.blend;
      gl.blendFunc(unityBlend(gl, blend[0]), unityBlend(gl, blend[1]));
      gl.depthMask(false);
    } else {
      gl.disable(gl.BLEND);
      gl.depthMask(true);
    }
  }

  function unityBlend(gl, value) {
    return [gl.ZERO, gl.ONE, gl.DST_COLOR, gl.SRC_COLOR, gl.ONE_MINUS_DST_COLOR, gl.SRC_ALPHA,
      gl.ONE_MINUS_SRC_COLOR, gl.DST_ALPHA, gl.ONE_MINUS_DST_ALPHA, gl.SRC_ALPHA_SATURATE,
      gl.ONE_MINUS_SRC_ALPHA][value] ?? gl.ONE;
  }

  function frame() {
    if (!S.running) return;
    requestAnimationFrame(frame);
    const ctx = S.gl;
    if (!ctx) return;
    step();
    streamChunks();
    const { gl, program, u } = ctx;
    const canvas = S.canvas;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = Math.max(1, Math.floor(canvas.clientWidth * dpr));
    const h = Math.max(1, Math.floor(canvas.clientHeight * dpr));
    if (canvas.width !== w || canvas.height !== h) { canvas.width = w; canvas.height = h; }
    // Redraw only when the view, the mode or the resident set changed, so an
    // idle viewer (or a software rasteriser) does not re-render every frame.
    const cam = S.camera;
    const signature = `${cam.pos.join(",")}|${cam.yaw}|${cam.pitch}|${S.mode}|${w}x${h}`;
    const viewChanged = signature !== S.lastSignature;
    if (S.batches && !viewChanged) return;
    // Streaming completions only invalidate batches; coalesce those rebuilds so a
    // burst of loads does not rebuild and redraw the whole resident set per load.
    const now = performance.now();
    if (!viewChanged && now - (S.lastDraw || 0) < 500) return;
    S.lastDraw = now;
    S.lastSignature = signature;
    gl.viewport(0, 0, w, h);
    gl.clearColor(0.46, 0.55, 0.64, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.useProgram(program);
    gl.uniformMatrix4fv(u.uProj, false, perspective(Math.PI / 3, w / h, 0.3, 8000));
    gl.uniformMatrix4fv(u.uView, false, viewMatrix(S.camera));
    gl.uniform3f(u.uEye, ...S.camera.pos);
    const sun = [0.35, 0.8, 0.45];
    const len = Math.hypot(...sun);
    gl.uniform3f(u.uSun, sun[0] / len, sun[1] / len, sun[2] / len);
    gl.uniform1i(u.uMode, { shaded: 0, tier: 1, normals: 2, unlit: 3 }[S.mode] ?? 0);
    if (!S.batches) S.batches = buildBatches();
    let drawn = 0, triangles = 0;
    for (const batch of S.batches) {
      const mesh = S.meshes.get(batch.meshIdx);
      if (!mesh || mesh.state !== "ready") continue;
      const sub = mesh.submeshes[batch.submesh] || (mesh.submeshes.length === 1 ? mesh.submeshes[0] : null);
      if (!sub || !sub.count) continue;
      bindMaterial(ctx, batch.material, batch);
      gl.bindVertexArray(mesh.vao);
      gl.bindBuffer(gl.ARRAY_BUFFER, mesh.instanceBuffer);
      gl.bufferData(gl.ARRAY_BUFFER, batch.data, gl.DYNAMIC_DRAW);
      gl.drawElementsInstanced(gl.TRIANGLES, sub.count, mesh.indexType, sub.start * mesh.indexBytes, batch.count);
      drawn += batch.count;
      triangles += (sub.count / 3) * batch.count;
    }
    gl.bindVertexArray(null);
    gl.depthMask(true);
    S.stats.drawn = drawn;
    S.stats.triangles = triangles;
    updateHud();
  }

  let lastStep = 0;
  function step() {
    const now = performance.now();
    const dt = lastStep ? Math.min((now - lastStep) / 1000, 0.1) : 0;
    lastStep = now;
    if (!S.keys.size) return;
    const { fwd, right } = cameraBasis(S.camera);
    const speed = S.camera.speed * (S.keys.has("shift") ? 4 : 1) * dt;
    const move = (v, s) => { for (let i = 0; i < 3; i += 1) S.camera.pos[i] += v[i] * s; };
    if (S.keys.has("w")) move(fwd, speed);
    if (S.keys.has("s")) move(fwd, -speed);
    if (S.keys.has("d")) move(right, speed);
    if (S.keys.has("a")) move(right, -speed);
    if (S.keys.has("e")) S.camera.pos[1] += speed;
    if (S.keys.has("q")) S.camera.pos[1] -= speed;
  }

  // ---------------------------------------------------------------- UI
  function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(attrs)) {
      if (key === "text") node.textContent = value;
      else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value);
    }
    for (const child of children) node.append(child);
    return node;
  }

  function updateHud() {
    const hud = S.host && S.host.querySelector(".ms3d-stats");
    if (!hud || !S.level) return;
    let ready = 0;
    for (const mesh of S.meshes.values()) if (mesh.state === "ready") ready += 1;
    const chunks = [...S.chunks.values()].filter((c) => c.state === "ready").length;
    const p = S.camera.pos;
    // Positions are shown in Unity world coordinates (X un-mirrored).
    hud.textContent = `chunks ${chunks}/${S.level.chunks.length} · meshes ${ready}/${S.meshes.size}`
      + ` · instances ${S.stats.drawn} · tris ${Math.round(S.stats.triangles / 1000)}k`
      + ` · pos ${(-p[0]).toFixed(0)}, ${p[1].toFixed(0)}, ${p[2].toFixed(0)}`
      + (S.queue.length ? ` · loading ${S.queue.length}` : "");
  }

  function evidenceText(level) {
    const stats = level.stats || {};
    const ev = level.evidence || {};
    const parts = Object.entries(ev).map(([key, value]) => `${key}: ${typeof value === "string" ? value : JSON.stringify(value)}`);
    const counts = Object.entries(stats).map(([key, value]) => `${key} ${typeof value === "object" ? JSON.stringify(value) : value}`);
    return [...parts, ...counts].join("\n");
  }

  function resetGpu() {
    S.generation += 1;
    if (S.gl) {
      const { gl } = S.gl;
      for (const mesh of S.meshes.values()) {
        if (mesh.vao) gl.deleteVertexArray(mesh.vao);
        for (const buffer of mesh.buffers || []) gl.deleteBuffer(buffer);
      }
      for (const tex of S.textures.values()) if (tex.tex) gl.deleteTexture(tex.tex);
    }
    S.meshes.clear();
    S.textures.clear();
    S.chunks.clear();
    S.queue.length = 0;
    S.batches = null;
  }

  async function selectLevel(levelId) {
    resetGpu();
    S.levelId = levelId;
    S.level = null;
    const response = await fetch(`${DATA_ROOT}/${encodeURIComponent(levelId)}/index.json`);
    if (!response.ok) throw new Error(`scene3d index HTTP ${response.status}`);
    const level = await response.json();
    if (S.levelId !== levelId) return;
    S.level = level;
    // Start above the densest streamed chunk, else the global chunk centre.
    const streamed = level.chunks.filter((c) => c.x !== null && c.x !== undefined);
    const pick = streamed.sort((a, b) => b.draws - a.draws)[0] || level.chunks[0];
    if (pick && pick.bounds) {
      const [lo, hi] = pick.bounds;
      const centre = [(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, (lo[2] + hi[2]) / 2];
      const radius = Math.min(200, Math.max(20, Math.hypot(hi[0] - lo[0], hi[2] - lo[2]) / 2));
      S.camera.pos = [centre[0], centre[1] + radius * 0.6, centre[2] + radius];
      S.camera.yaw = 0;
      S.camera.pitch = -0.45;
    }
    const info = S.host.querySelector(".ms3d-evidence");
    if (info) info.textContent = evidenceText(level);
  }

  function bindInput(canvas) {
    let drag = null;
    canvas.addEventListener("pointerdown", (event) => {
      drag = { x: event.clientX, y: event.clientY };
      canvas.setPointerCapture(event.pointerId);
      canvas.focus();
    });
    canvas.addEventListener("pointermove", (event) => {
      if (!drag) return;
      S.camera.yaw += (event.clientX - drag.x) * 0.004;
      S.camera.pitch = Math.max(-1.55, Math.min(1.55, S.camera.pitch - (event.clientY - drag.y) * 0.004));
      drag = { x: event.clientX, y: event.clientY };
    });
    canvas.addEventListener("pointerup", () => { drag = null; });
    canvas.addEventListener("wheel", (event) => {
      event.preventDefault();
      S.camera.speed = Math.max(2, Math.min(2000, S.camera.speed * (event.deltaY < 0 ? 1.2 : 1 / 1.2)));
    }, { passive: false });
    canvas.addEventListener("keydown", (event) => {
      const key = event.key.toLowerCase();
      if ("wasdqe".includes(key) || key === "shift") { S.keys.add(key); event.preventDefault(); }
    });
    canvas.addEventListener("keyup", (event) => S.keys.delete(event.key.toLowerCase()));
    canvas.addEventListener("blur", () => S.keys.clear());
  }

  async function open(preferredLevel) {
    const mapView = document.getElementById("map-view");
    if (!mapView) return;
    if (!S.host) {
      const levelSelect = el("select", { class: "ms3d-level", "aria-label": "Level" });
      const modeSelect = el("select", { class: "ms3d-mode", "aria-label": "Shading" });
      for (const [value, label] of [["shaded", "Shaded (HGRP approx.)"], ["unlit", "Albedo"], ["tier", "Evidence tier"], ["normals", "Normals"]]) {
        modeSelect.append(el("option", { value, text: label }));
      }
      modeSelect.addEventListener("change", () => { S.mode = modeSelect.value; });
      levelSelect.addEventListener("change", () => selectLevel(levelSelect.value).catch(showError));
      const canvas = el("canvas", { class: "ms3d-canvas", tabindex: "0" });
      S.host = el("div", { class: "ms3d-overlay" }, [
        canvas,
        el("div", { class: "ms3d-bar" }, [
          el("strong", { text: "3D scene" }),
          levelSelect,
          modeSelect,
          el("span", { class: "ms3d-stats" }),
          el("button", { type: "button", class: "ms3d-close", text: "Close", onclick: close }),
        ]),
        el("div", { class: "ms3d-help", text: "Drag to look · WASD move · Q/E down/up · Shift fast · wheel speed" }),
        el("div", { class: "ms3d-legend" }, Object.entries(TIER_COLORS).map(([tier, c]) => el("span", {
          style: `--tier: rgb(${c.map((v) => Math.round(v * 255)).join(",")})`,
          text: tier,
        }))),
        el("pre", { class: "ms3d-evidence" }),
      ]);
      mapView.append(S.host);
      S.canvas = canvas;
      try {
        S.gl = createGl(canvas);
      } catch (error) {
        showError(error);
      }
      if (!S.gl) showError(new Error("WebGL2 unavailable"));
      bindInput(canvas);
    }
    S.host.hidden = false;
    const response = await fetch(`${DATA_ROOT}/index.json`);
    if (!response.ok) { showError(new Error("No scene3d data; run build_map_scene3d")); return; }
    const catalog = await response.json();
    S.levels = (catalog.levels || []).map((row) => (typeof row === "string" ? row : row.level));
    const select = S.host.querySelector(".ms3d-level");
    select.replaceChildren(...S.levels.map((id) => el("option", { value: id, text: id })));
    const levelId = S.levels.includes(preferredLevel) ? preferredLevel : (S.levelId && S.levels.includes(S.levelId) ? S.levelId : S.levels[0]);
    select.value = levelId || "";
    if (levelId && levelId !== S.levelId) await selectLevel(levelId).catch(showError);
    if (!S.running) { S.running = true; lastStep = 0; requestAnimationFrame(frame); }
    S.canvas.focus();
  }

  function close() {
    S.running = false;
    S.keys.clear();
    if (S.host) S.host.hidden = true;
  }

  function showError(error) {
    const info = S.host && S.host.querySelector(".ms3d-evidence");
    if (info) info.textContent = `Error: ${error && error.message ? error.message : error}`;
  }

  function installLauncher() {
    const mapView = document.getElementById("map-view");
    if (!mapView || mapView.querySelector(".ms3d-launch")) return;
    const button = el("button", { type: "button", class: "ms3d-launch", text: "3D scene", title: "Open the InitChunkData 3D scene viewer" });
    const params = new URLSearchParams(location.search);
    button.addEventListener("click", () => {
      open(params.get("scene3d") || params.get("map") || "").catch(showError);
    });
    mapView.append(button);
    // `?scene3d=<level>#map` deep-links straight into the viewer.
    if (params.get("scene3d")) open(params.get("scene3d")).catch(showError);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", installLauncher);
  else installLauncher();

  window.WebUI = window.WebUI || {};
  window.WebUI.mapScene3d = { open, close, _parseObj: parseObj };
})();
