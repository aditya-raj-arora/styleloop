// A minimal valid 1x1 red PNG, inlined so specs don't need a fixture file on
// disk — Playwright's setInputFiles accepts an in-memory buffer directly.
const _PNG_BASE64 =
  "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==";

export function testImageFile(name = "garment.png") {
  return {
    name,
    mimeType: "image/png",
    buffer: Buffer.from(_PNG_BASE64, "base64"),
  };
}
