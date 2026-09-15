import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { ApiError, getPackingList } from "../api/client";
import AnimatedBackground from "../components/AnimatedBackground";
import Navbar from "../components/Navbar";
import { useGeolocation } from "../hooks/useGeolocation";

const _CATEGORY_LABEL: Record<string, string> = {
  top: "Tops",
  bottom: "Bottoms",
  dress: "Dresses",
  outerwear: "Outerwear",
  shoes: "Shoes",
};

function _todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function _daysFromNowIso(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() + days);
  return d.toISOString().slice(0, 10);
}

export default function PackingList() {
  const { coords, loading: locating } = useGeolocation();
  const [startDate, setStartDate] = useState(_todayIso());
  const [endDate, setEndDate] = useState(_daysFromNowIso(3));
  // Only becomes a "live" query once the user submits the form — a packing
  // list shouldn't fire on every keystroke while dates are still being picked.
  const [submitted, setSubmitted] = useState(false);

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["packing-list", startDate, endDate],
    queryFn: () => getPackingList(startDate, endDate, coords),
    enabled: false,
  });

  const noWardrobeYet = error instanceof ApiError && error.status === 422;
  const invalidRange = error instanceof ApiError && error.status === 400;

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitted(true);
    refetch();
  }

  return (
    <AnimatedBackground>
      <div className="p-5 sm:p-8 pb-24">
        <h1 className="text-3xl sm:text-5xl font-bold text-white">Pack for a Trip</h1>
        <p className="text-white/80 mt-2">Weather-aware, sized to how long you're away.</p>

        <form
          onSubmit={handleSubmit}
          className="mt-6 flex flex-wrap items-end gap-3 max-w-lg"
        >
          <label className="flex flex-col text-sm text-white/80">
            Leaving
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="mt-1 rounded-lg px-3 py-1.5 bg-white/10 text-white border border-white/30 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
            />
          </label>
          <label className="flex flex-col text-sm text-white/80">
            Returning
            <input
              type="date"
              value={endDate}
              min={startDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="mt-1 rounded-lg px-3 py-1.5 bg-white/10 text-white border border-white/30 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
            />
          </label>
          <button
            type="submit"
            disabled={locating || isLoading}
            className="bg-white/20 hover:bg-white/30 text-white px-5 py-2 rounded-full transition disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
          >
            {isLoading ? "Packing…" : "Generate"}
          </button>
        </form>

        <div className="mt-8" aria-live="polite">
          {!submitted && (
            <p className="text-white/60 text-sm">Pick your dates and generate a packing list.</p>
          )}

          {submitted && isLoading && <p className="text-white/70">Checking the forecast…</p>}

          {submitted && noWardrobeYet && (
            <p className="text-white/70">
              Not enough clean, tagged garments yet — upload and tag a few first.
            </p>
          )}

          {submitted && invalidRange && (
            <p role="alert" className="text-white/70">
              {(error as ApiError).message}
            </p>
          )}

          {submitted && isError && !noWardrobeYet && !invalidRange && (
            <p role="alert" className="text-white/70">
              Couldn't build a packing list. Try again.
            </p>
          )}

          {data && (
            <div className="max-w-2xl">
              <p className="text-white/70 text-sm mb-1">
                {data.num_days} day{data.num_days === 1 ? "" : "s"}
                {data.weather.temp_min_c !== null && data.weather.temp_max_c !== null && (
                  <> · {Math.round(data.weather.temp_min_c)}–{Math.round(data.weather.temp_max_c)}°C</>
                )}
                {data.weather.days_with_forecast < data.num_days && (
                  <> · forecast only covers {data.weather.days_with_forecast} of those days</>
                )}
              </p>

              <div className="flex flex-wrap gap-2 mb-6">
                {data.needs_outerwear && (
                  <span className="px-3 py-1 rounded-full text-xs bg-blue-500/30 text-blue-100 border border-blue-400/40">
                    🧥 Bring a layer
                  </span>
                )}
                {data.needs_rain_gear && (
                  <span className="px-3 py-1 rounded-full text-xs bg-cyan-500/30 text-cyan-100 border border-cyan-400/40">
                    ☔ Rain expected
                  </span>
                )}
              </div>

              {data.categories.length === 0 && (
                <p className="text-white/60 text-sm">Nothing to pack yet.</p>
              )}

              <div className="space-y-6">
                {data.categories.map((cat) => (
                  <div key={cat.category}>
                    <h2 className="text-white text-lg font-medium mb-2">
                      {_CATEGORY_LABEL[cat.category] ?? cat.category}
                      {cat.short_by > 0 && (
                        <span className="ml-2 text-amber-300 text-xs font-normal">
                          short {cat.short_by} — you don't have enough clean, tagged{" "}
                          {(_CATEGORY_LABEL[cat.category] ?? cat.category).toLowerCase()}
                        </span>
                      )}
                    </h2>
                    {cat.garments.length > 0 && (
                      <div className="grid grid-cols-3 sm:grid-cols-4 gap-3">
                        {cat.garments.map((g) => (
                          <img
                            key={g.id}
                            src={g.processed_url ?? g.image_url}
                            alt={g.category ?? "Garment"}
                            className="w-full aspect-square object-cover rounded-2xl border border-white/30"
                          />
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <Navbar />
    </AnimatedBackground>
  );
}
