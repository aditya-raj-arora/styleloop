import type { Garment, WardrobeAnalytics } from "../api/client";

interface Props {
  analytics: WardrobeAnalytics;
  isNight: boolean;
}

function GarmentChip({ garment, sublabel }: { garment: Garment; sublabel: string }) {
  const image = garment.processed_url ?? garment.image_url;
  return (
    <li className="flex items-center gap-2 shrink-0">
      <img
        src={image}
        alt={garment.category ?? "Garment"}
        className="w-10 h-10 rounded-xl object-cover border border-white/30"
      />
      <span className="text-xs whitespace-nowrap">{sublabel}</span>
    </li>
  );
}

// Sprint 6 — wardrobe analytics: what gets worn, what's sitting unused, and
// which essential categories (top/bottom/dress/outerwear/shoes) the closet
// has nothing clean+tagged in. Collapsed by default on Wardrobe.tsx so it
// doesn't compete with the grid on a first load.
export default function WardrobeAnalyticsPanel({ analytics, isNight }: Props) {
  const textClass = isNight ? "text-white" : "text-gray-800";
  const subTextClass = isNight ? "text-white/70" : "text-gray-600";
  const cardClass = isNight
    ? "bg-white/10 border-white/20"
    : "bg-white/60 border-white/40";

  return (
    <div className={`rounded-2xl border p-4 mb-6 ${cardClass}`}>
      <div className="grid grid-cols-3 gap-3 text-center mb-4">
        <div>
          <p className={`text-2xl font-bold ${textClass}`}>{analytics.total_garments}</p>
          <p className={`text-xs ${subTextClass}`}>Total</p>
        </div>
        <div>
          <p className={`text-2xl font-bold ${textClass}`}>{analytics.clean_count}</p>
          <p className={`text-xs ${subTextClass}`}>Clean</p>
        </div>
        <div>
          <p className={`text-2xl font-bold ${textClass}`}>{analytics.laundry_count}</p>
          <p className={`text-xs ${subTextClass}`}>In laundry</p>
        </div>
      </div>

      {analytics.category_gaps.length > 0 && (
        <div className="mb-4">
          <p className={`text-sm font-medium mb-1.5 ${textClass}`}>Wardrobe gaps</p>
          <div className="flex flex-wrap gap-1.5">
            {analytics.category_gaps.map((category) => (
              <span
                key={category}
                className={`px-2.5 py-1 rounded-full text-xs capitalize bg-amber-500/20 border border-amber-500/40 ${
                  isNight ? "text-amber-300" : "text-amber-700"
                }`}
              >
                No {category}
              </span>
            ))}
          </div>
        </div>
      )}

      {analytics.most_worn.length > 0 && (
        <div className="mb-4">
          <p className={`text-sm font-medium mb-1.5 ${textClass}`}>Most worn</p>
          <ul className="flex gap-3 overflow-x-auto pb-1">
            {analytics.most_worn.map((g) => (
              <GarmentChip
                key={g.id}
                garment={g}
                sublabel={`${g.wear_count}× worn`}
              />
            ))}
          </ul>
        </div>
      )}

      {analytics.never_worn.length > 0 && (
        <div>
          <p className={`text-sm font-medium mb-1.5 ${textClass}`}>Never worn</p>
          <ul className="flex gap-3 overflow-x-auto pb-1">
            {analytics.never_worn.map((g) => (
              <GarmentChip key={g.id} garment={g} sublabel={g.category ?? "untagged"} />
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
