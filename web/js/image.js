/** Reduce las fotos grandes antes de subirlas: una foto de 12 MP (4-8 MB) pasa a ~1-2 MB sin perder
 *  precisión útil (3000 px en el lado largo = ~10 px/mm sobre una hoja A4, lo que usa el servidor). */
const MAX_SIDE = 3000;
const MAX_BYTES = 2.5e6;
const QUALITY = 0.9;

export async function prepareImage(blob, maxSide = MAX_SIDE) {
  if (!blob?.type?.startsWith("image/")) return blob;
  let bmp;
  try { bmp = await createImageBitmap(blob, { imageOrientation: "from-image" }); } catch { return blob; }
  const long = Math.max(bmp.width, bmp.height);
  if (long <= maxSide && blob.size <= MAX_BYTES) { bmp.close?.(); return blob; }
  const k = Math.min(1, maxSide / long);
  const w = Math.round(bmp.width * k), h = Math.round(bmp.height * k);
  const canvas = "OffscreenCanvas" in self ? new OffscreenCanvas(w, h) : Object.assign(document.createElement("canvas"), { width: w, height: h });
  canvas.getContext("2d").drawImage(bmp, 0, 0, w, h);
  bmp.close?.();
  const out = canvas.convertToBlob
    ? await canvas.convertToBlob({ type: "image/jpeg", quality: QUALITY })
    : await new Promise((r) => canvas.toBlob(r, "image/jpeg", QUALITY));
  return out && out.size < blob.size ? out : blob;
}
