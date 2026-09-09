// GarmentCard — stub.
// Renders one garment from the frozen Garment contract. Shows a placeholder while
// processed_url is null (worker still processing bg-removal + tagging).

import type { Garment } from "../api/client";

export default function GarmentCard({ garment }: { garment: Garment }) {
  const imageSrc = garment.processed_url ?? garment.image_url;
  return (
    <article>
      {/* TODO(Frontend): real card layout, tag chips, state badge, wear count. */}
      <img src={imageSrc} alt={garment.category ?? "garment"} />
      <p>{garment.processed_url ? garment.category ?? "Untagged" : "Processing…"}</p>
    </article>
  );
}
