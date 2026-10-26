/*
 * Sprite images from their textures.
 *
 * The export keeps a Unity Sprite as a crop document over its exported
 * Texture2D (scripts/game_data/sprite_crops.py, endfield.sprite-crop.v1), not
 * as a PNG. serve.py answers a request for game/Unity/Sprite/<name>.png with
 * that document (Content-Type SPRITE_CROP_TYPE), or with AnimeStudio's own PNG
 * when the export kept one. This worker turns the document into the image:
 * crop the texture, flip or rotate it, clear the pixels outside a Tight mesh
 * and drop the color of the fully transparent pixels the document lists. The
 * texture PNG is decoded here rather than through a canvas, so every pixel,
 * transparent ones included, equals AnimeStudio's rendering of the Sprite.
 */
"use strict";
importScripts("src/core/png.js?v=20261017-rgb-preview");

const SPRITE_CROP_TYPE = "application/vnd.endfield.sprite-crop+json";
const SPRITE_PATH = /^\/export_(?:full|data|previous)\/(?:.*\/)?Unity\/Sprite\/[^/]+\.png$/i;
const CACHE_LIMIT = 256;
const rendered = new Map();

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (event) => {
  const request = event.request;
  if (request.method !== "GET") return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin || !SPRITE_PATH.test(url.pathname)) return;
  event.respondWith(spriteResponse(url));
});

async function spriteResponse(url) {
  const response = await fetch(url.href, { credentials: "same-origin" });
  const type = (response.headers.get("Content-Type") || "").toLowerCase();
  if (!response.ok || !type.startsWith(SPRITE_CROP_TYPE)) return response;
  try {
    const text = await response.text();
    const crop = JSON.parse(text);
    const textureUrl = new URL(`../Texture2D/${encodeURIComponent(crop.texture.file)}`, url);
    const texture = await fetch(textureUrl.href, { credentials: "same-origin" });
    if (!texture.ok) return new Response(`Sprite texture ${crop.texture.file}: ${texture.status}`, { status: 404 });
    const key = `${url.href}\n${text}\n${texture.headers.get("Last-Modified") || ""}\n${texture.headers.get("Content-Length") || ""}`;
    let png = rendered.get(key);
    if (png) {
      rendered.delete(key);
    } else {
      png = await renderSprite(crop, await texture.blob());
    }
    rendered.set(key, png);
    while (rendered.size > CACHE_LIMIT) rendered.delete(rendered.keys().next().value);
    return new Response(png, {
      headers: { "Content-Type": "image/png", "Cache-Control": "no-cache", "X-Endfield-Sprite": "crop" },
    });
  } catch (error) {
    return new Response(`Sprite crop failed: ${error && error.message ? error.message : error}`, { status: 500 });
  }
}

async function renderSprite(crop, textureBlob) {
  let texture = null;
  if (!crop.scale) {
    try {
      texture = await decodePng(new Uint8Array(await textureBlob.arrayBuffer()));
    } catch (_error) {
      texture = null;
    }
  }
  if (!texture) {
    // A scaled Sprite, or a PNG this decoder does not read: let the browser
    // decode and resample. Visible pixels match; hidden color may not.
    texture = await canvasPixels(textureBlob, crop.scale);
  }
  const pixels = applyCrop(crop, texture);
  return encodePng(crop.width, crop.height, pixels);
}

async function canvasPixels(blob, scale) {
  const bitmap = await createImageBitmap(blob, { premultiplyAlpha: "none", colorSpaceConversion: "none" });
  const width = scale ? scale.width : bitmap.width;
  const height = scale ? scale.height : bitmap.height;
  const canvas = new OffscreenCanvas(width, height);
  const context = canvas.getContext("2d");
  context.drawImage(bitmap, 0, 0, width, height);
  bitmap.close();
  return { width, height, data: context.getImageData(0, 0, width, height).data };
}

function applyCrop(crop, texture) {
  const x0 = crop.crop.x;
  const y0 = crop.crop.y;
  const cutWidth = crop.crop.width;
  const cutHeight = crop.crop.height;
  const width = crop.width;
  const height = crop.height;
  if (x0 + cutWidth > texture.width || y0 + cutHeight > texture.height) {
    throw new Error(`crop leaves the ${texture.width}x${texture.height} texture`);
  }
  // The top-down cut pixel each result pixel (u, v) shows.
  const source = {
    none: (u, v) => [u, v],
    flipX: (u, v) => [cutWidth - 1 - u, v],
    flipY: (u, v) => [u, cutHeight - 1 - v],
    rotate180: (u, v) => [cutWidth - 1 - u, cutHeight - 1 - v],
    rotateCW90: (u, v) => [v, cutHeight - 1 - u],
    rotateCCW90: (u, v) => [cutWidth - 1 - v, u],
  }[crop.transform];
  if (!source) throw new Error(`unknown transform ${crop.transform}`);
  const out = new Uint8Array(width * height * 4);
  const data = texture.data;
  if (crop.transform === "none") {
    for (let v = 0; v < height; v += 1) {
      const start = ((y0 + v) * texture.width + x0) * 4;
      out.set(data.subarray(start, start + width * 4), v * width * 4);
    }
  } else {
    for (let v = 0; v < height; v += 1) {
      for (let u = 0; u < width; u += 1) {
        const [sx, sy] = source(u, v);
        const from = ((y0 + sy) * texture.width + x0 + sx) * 4;
        const to = (v * width + u) * 4;
        out[to] = data[from];
        out[to + 1] = data[from + 1];
        out[to + 2] = data[from + 2];
        out[to + 3] = data[from + 3];
      }
    }
  }
  for (const row of crop.clear || []) {
    for (let i = 1; i + 1 < row.length; i += 2) {
      const start = (row[0] * width + row[i]) * 4;
      out.fill(0, start, start + row[i + 1] * 4);
    }
  }
  for (const row of crop.zero || []) {
    for (let i = 1; i + 1 < row.length; i += 2) {
      for (let pixel = row[0] * width + row[i], end = pixel + row[i + 1]; pixel < end; pixel += 1) {
        if (out[pixel * 4 + 3] === 0) out.fill(0, pixel * 4, pixel * 4 + 4);
      }
    }
  }
  return out;
}
