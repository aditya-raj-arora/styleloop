import type { Garment } from "../api/client";

interface Props {
  garment: Garment;
  // Optional — Upload.tsx's just-created preview card has nothing to do
  // yet, so state changes stay opt-in rather than every caller wiring a
  // mutation it doesn't need.
  onSendToLaundry?: (id: number) => void;
  sendingToLaundry?: boolean;
}

const _STATE_LABEL: Record<string, string> = {
  clean: "Clean",
  worn: "Worn",
  laundry: "In laundry",
};

// processed_url is null until the RQ worker finishes bg-removal + tagging —
// show the raw upload behind a "Processing…" overlay until it resolves.
export default function GarmentCard({ garment, onSendToLaundry, sendingToLaundry }: Props) {
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

      {!isProcessing && (
        <span className="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-white/90 text-xs font-medium text-gray-700">
          {_STATE_LABEL[garment.state] ?? garment.state}
        </span>
      )}

      {!isProcessing && (garment.category || garment.colors?.length) && (
        <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/60 to-transparent flex items-end justify-between gap-2">
          <p className="text-white text-sm capitalize">
            {[garment.category, garment.colors?.[0]].filter(Boolean).join(" · ")}
          </p>

          {onSendToLaundry && garment.state !== "laundry" && (
            <button
              type="button"
              onClick={() => onSendToLaundry(garment.id)}
              disabled={sendingToLaundry}
              aria-label={`Send ${garment.category ?? "this garment"} to laundry`}
              className="shrink-0 text-xs font-medium px-2 py-1 rounded-full bg-white/20 hover:bg-white/30 text-white transition disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
            >
              {sendingToLaundry ? "…" : "To laundry"}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
