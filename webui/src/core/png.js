// Shared lossless PNG codec; preserves RGB beneath transparent pixels.
async function streamBytes(bytes, transform) {
  const stream = new Blob([bytes]).stream().pipeThrough(transform);
  return new Uint8Array(await new Response(stream).arrayBuffer());
}

async function decodePng(bytes) {
  const signature = [137, 80, 78, 71, 13, 10, 26, 10];
  if (signature.some((value, index) => bytes[index] !== value)) throw new Error("not a PNG");
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  const idat = [];
  let width = 0;
  let height = 0;
  let depth = 0;
  let color = -1;
  let interlace = 0;
  let palette = null;
  let transparency = null;
  for (let position = 8; position + 8 <= bytes.length;) {
    const length = view.getUint32(position);
    const kind = String.fromCharCode(...bytes.subarray(position + 4, position + 8));
    const body = bytes.subarray(position + 8, position + 8 + length);
    if (kind === "IHDR") {
      width = view.getUint32(position + 8);
      height = view.getUint32(position + 12);
      depth = body[8];
      color = body[9];
      interlace = body[12];
    } else if (kind === "PLTE") {
      palette = body;
    } else if (kind === "tRNS") {
      transparency = body;
    } else if (kind === "IDAT") {
      idat.push(body);
    } else if (kind === "IEND") {
      break;
    }
    position += 12 + length;
  }
  const channels = { 0: 1, 2: 3, 3: 1, 4: 2, 6: 4 }[color];
  if (depth !== 8 || interlace !== 0 || !channels) throw new Error(`unsupported PNG (depth ${depth}, color ${color})`);
  const raw = await streamBytes(new Blob(idat), new DecompressionStream("deflate"));
  const stride = width * channels;
  const lines = new Uint8Array(stride * height);
  let previous = new Uint8Array(stride);
  for (let y = 0, offset = 0; y < height; y += 1, offset += stride + 1) {
    const filter = raw[offset];
    const line = lines.subarray(y * stride, (y + 1) * stride);
    line.set(raw.subarray(offset + 1, offset + 1 + stride));
    if (filter === 1) {
      for (let x = channels; x < stride; x += 1) line[x] = (line[x] + line[x - channels]) & 255;
    } else if (filter === 2) {
      for (let x = 0; x < stride; x += 1) line[x] = (line[x] + previous[x]) & 255;
    } else if (filter === 3) {
      for (let x = 0; x < stride; x += 1) {
        const left = x >= channels ? line[x - channels] : 0;
        line[x] = (line[x] + ((left + previous[x]) >> 1)) & 255;
      }
    } else if (filter === 4) {
      for (let x = 0; x < stride; x += 1) {
        const left = x >= channels ? line[x - channels] : 0;
        const up = previous[x];
        const upLeft = x >= channels ? previous[x - channels] : 0;
        const estimate = left + up - upLeft;
        const toLeft = Math.abs(estimate - left);
        const toUp = Math.abs(estimate - up);
        const toUpLeft = Math.abs(estimate - upLeft);
        const predictor = toLeft <= toUp && toLeft <= toUpLeft ? left : (toUp <= toUpLeft ? up : upLeft);
        line[x] = (line[x] + predictor) & 255;
      }
    } else if (filter !== 0) {
      throw new Error(`unsupported PNG filter ${filter}`);
    }
    previous = line;
  }
  if (color === 6) return { width, height, data: lines };
  const data = new Uint8Array(width * height * 4);
  for (let pixel = 0; pixel < width * height; pixel += 1) {
    const at = pixel * channels;
    let r;
    let g;
    let b;
    let a = 255;
    if (color === 2) {
      r = lines[at]; g = lines[at + 1]; b = lines[at + 2];
    } else if (color === 0) {
      r = g = b = lines[at];
    } else if (color === 4) {
      r = g = b = lines[at]; a = lines[at + 1];
    } else {
      const index = lines[at];
      r = palette[index * 3]; g = palette[index * 3 + 1]; b = palette[index * 3 + 2];
      a = transparency && index < transparency.length ? transparency[index] : 255;
    }
    data[pixel * 4] = r; data[pixel * 4 + 1] = g; data[pixel * 4 + 2] = b; data[pixel * 4 + 3] = a;
  }
  return { width, height, data };
}

const CRC_TABLE = (() => {
  const table = new Uint32Array(256);
  for (let n = 0; n < 256; n += 1) {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
    table[n] = c >>> 0;
  }
  return table;
})();

function crc32(bytes) {
  let crc = 0xFFFFFFFF;
  for (let i = 0; i < bytes.length; i += 1) crc = CRC_TABLE[(crc ^ bytes[i]) & 255] ^ (crc >>> 8);
  return (crc ^ 0xFFFFFFFF) >>> 0;
}

function chunk(kind, body) {
  const out = new Uint8Array(12 + body.length);
  const view = new DataView(out.buffer);
  view.setUint32(0, body.length);
  for (let i = 0; i < 4; i += 1) out[4 + i] = kind.charCodeAt(i);
  out.set(body, 8);
  view.setUint32(8 + body.length, crc32(out.subarray(4, 8 + body.length)));
  return out;
}

async function encodePng(width, height, pixels) {
  const stride = width * 4;
  const raw = new Uint8Array((stride + 1) * height);
  for (let y = 0; y < height; y += 1) raw.set(pixels.subarray(y * stride, (y + 1) * stride), y * (stride + 1) + 1);
  const header = new Uint8Array(13);
  const view = new DataView(header.buffer);
  view.setUint32(0, width);
  view.setUint32(4, height);
  header.set([8, 6, 0, 0, 0], 8);
  const data = await streamBytes(raw, new CompressionStream("deflate"));
  return new Blob([
    new Uint8Array([137, 80, 78, 71, 13, 10, 26, 10]),
    chunk("IHDR", header),
    chunk("IDAT", data),
    chunk("IEND", new Uint8Array(0)),
  ], { type: "image/png" });
}
