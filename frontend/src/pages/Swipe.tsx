import { useState } from "react";
import Navbar from "../components/Navbar";

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

const outfits = [
  {
    image: "https://picsum.photos/500/700?1",
    title: "Summer Fit"
  },
  {
    image: "https://picsum.photos/500/700?2",
    title: "Streetwear"
  },
  {
    image: "https://picsum.photos/500/700?3",
    title: "Formal"
  }
];

export default function Swipe() {
  const [index, setIndex] = useState(0);

  function next() {
    setIndex((index + 1) % outfits.length);
  }

  return (
    <>
      <div className="p-5">
        <MockOutfitCard
          image={outfits[index].image}
          title={outfits[index].title}
        />

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