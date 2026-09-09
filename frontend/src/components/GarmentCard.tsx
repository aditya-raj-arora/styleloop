import type { Garment } from "../api/client";

interface Props {
  garment: Garment;
}

// processed_url is null until the RQ worker finishes bg-removal + tagging —
// show the raw upload behind a "Processing…" overlay until it resolves.
export default function GarmentCard({ garment }: Props) {
  const isProcessing = garment.processed_url === null;
  const image = garment.processed_url ?? garment.image_url;

  return (
    <div className="relative rounded-3xl overflow-hidden bg-white/30 backdrop-blur-xl border border-white/30 shadow-lg transition-all duration-300 hover:scale-105">
      <img
        src={image}
        alt={garment.category ?? "Garment"}
        className={`w-full aspect-square object-cover ${isProcessing ? "opacity-60 blur-[2px]" : ""}`}
      />

      {isProcessing && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/20">
          <span className="px-3 py-1.5 rounded-full bg-white/90 text-sm font-medium text-gray-800">
            Processing…
          </span>
        </div>
      )}

      {!isProcessing && (garment.category || garment.colors?.length) && (
        <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/60 to-transparent">
          <p className="text-white text-sm capitalize">
            {[garment.category, garment.colors?.[0]].filter(Boolean).join(" · ")}
          </p>
        </div>
      )}
    </div>
  );
}
