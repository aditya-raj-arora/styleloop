import { useState } from "react";
import Navbar from "../components/Navbar";
import type { Outfit } from "../api/client";

// NOTE(Dev C): this page swipes on *outfits* (mock for now — Sprint 2 wires
// GET /outfits/daily), not single garments, so it doesn't reuse GarmentCard —
// that component is now typed to the real single-Garment API shape from the
// Sprint 1 upload pipeline. Swap this local card for real outfit data when
// the rotation engine lands.
function MockOutfitCard({ image, title }: { image: string; title: string }) {
  return (
    <div className="rounded-2xl overflow-hidden shadow-lg">
      <img src={image} alt={title} className="w-full h-[420px] object-cover" />
      <div className="p-4 bg-black text-white">
        <h2>{title}</h2>
      </div>
    </div>
  );
}

// Mock data shaped against the real Outfit contract (see api/client.ts) so
// swapping this for GET /outfits/daily later is a data-source change, not a
// type rework. The contract only carries garment_ids (numbers), not photos
// or a title — display-only mock metadata for rendering lives in
// _MOCK_DISPLAY below, keyed by outfit id, since the real endpoint doesn't
// have an equivalent field yet.
const _MOCK_OUTFITS: Outfit[] = [
  { id: 1, user_id: 1, garment_ids: [101, 102], score: 2.4, generated_for: "2026-09-14", created_at: "2026-09-14T06:00:00Z" },
  { id: 2, user_id: 1, garment_ids: [103, 104, 105], score: 1.9, generated_for: "2026-09-14", created_at: "2026-09-14T06:00:00Z" },
  { id: 3, user_id: 1, garment_ids: [106, 107], score: 1.7, generated_for: "2026-09-14", created_at: "2026-09-14T06:00:00Z" },
];

const _MOCK_DISPLAY: Record<number, { image: string; title: string }> = {
  1: { image: "https://picsum.photos/500/700?1", title: "Summer Fit" },
  2: { image: "https://picsum.photos/500/700?2", title: "Streetwear" },
  3: { image: "https://picsum.photos/500/700?3", title: "Formal" },
};

export default function Swipe() {
  const [index, setIndex] = useState(0);

  function next() {
    setIndex((index + 1) % _MOCK_OUTFITS.length);
  }

  const outfit = _MOCK_OUTFITS[index];
  const display = _MOCK_DISPLAY[outfit.id];

  return (
    <>
      <div className="p-5">
        <MockOutfitCard image={display.image} title={display.title} />

        <div className="flex justify-center gap-5 mt-6">
          <button
            onClick={next}
            className="bg-red-500 px-6 py-2 rounded"
          >
            Skip
          </button>

          <button
            onClick={next}
            className="bg-green-500 px-6 py-2 rounded"
          >
            Like
          </button>
        </div>
      </div>

      <Navbar />
    </>
  );
}
