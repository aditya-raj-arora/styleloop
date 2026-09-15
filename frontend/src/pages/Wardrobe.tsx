import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { Garment, GarmentState } from "../api/client";
import { getWardrobeAnalytics, listGarments, resetLaundry, setGarmentState } from "../api/client";
import GarmentCard from "../components/GarmentCard";
import Navbar from "../components/Navbar";
import WardrobeAnalyticsPanel from "../components/WardrobeAnalyticsPanel";
import WardrobeBackground from "../components/wardrobeBackground";
import { useIsNight } from "../hooks/useIsNight";

type Filter = "all" | GarmentState;

const _FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "clean", label: "Clean" },
  { value: "worn", label: "Worn" },
  { value: "laundry", label: "Laundry" },
];

export default function Wardrobe() {
  const [filter, setFilter] = useState<Filter>("all");
  const [showAnalytics, setShowAnalytics] = useState(false);
  const queryClient = useQueryClient();
  // WardrobeBackground goes dark at night (moon + stars) — this page's text
  // was hardcoded for its pale daytime gradients only, so it went nearly
  // unreadable after dark. Mirror the same day/night split here instead.
  const isNight = useIsNight();

  const { data: garments, isLoading, isError } = useQuery({
    queryKey: ["garments"],
    queryFn: listGarments,
    // Keep polling while anything is still processing (processed_url null);
    // stop once every garment has resolved, to avoid hammering the API forever.
    refetchInterval: (query) => {
      const garments = query.state.data;
      const stillProcessing = garments?.some((g) => g.processed_url === null);
      return stillProcessing ? 3000 : false;
    },
  });

  const sendToLaundry = useMutation({
    mutationFn: (id: number) => setGarmentState(id, "laundry"),
    onSuccess: (updated) => {
      queryClient.setQueryData<Garment[]>(["garments"], (existing) =>
        existing?.map((g) => (g.id === updated.id ? updated : g)),
      );
    },
  });

  const doLaundry = useMutation({
    mutationFn: resetLaundry,
    onSuccess: (reset) => {
      const resetIds = new Set(reset.map((g) => g.id));
      queryClient.setQueryData<Garment[]>(["garments"], (existing) =>
        existing?.map((g) => (resetIds.has(g.id) ? { ...g, state: "clean" } : g)),
      );
    },
  });

  const laundryCount = garments?.filter((g) => g.state === "laundry").length ?? 0;
  const visible = garments?.filter((g) => filter === "all" || g.state === filter);

  // Only fetched once the user actually opens the panel — it's not needed
  // for the grid itself and every field it needs is already derivable, but
  // computing it here would duplicate the backend's own definition of
  // "gap" and "most worn" instead of trusting one source of truth.
  const { data: analytics, isLoading: analyticsLoading } = useQuery({
    queryKey: ["garments", "analytics"],
    queryFn: getWardrobeAnalytics,
    enabled: showAnalytics,
  });

  return (
    <WardrobeBackground>
      <div className="p-4 sm:p-6 pb-24">
        <h1 className={`text-3xl sm:text-4xl font-bold ${isNight ? "text-white" : "text-gray-800"}`}>
          My Wardrobe
        </h1>

        <p className={`mt-2 mb-4 ${isNight ? "text-white/80" : "text-gray-600"}`}>
          {garments?.length
            ? `${garments.length} item${garments.length === 1 ? "" : "s"} in your closet.`
            : "Your uploaded clothes, all in one place."}
        </p>

        {garments && garments.length > 0 && (
          <button
            type="button"
            onClick={() => setShowAnalytics((shown) => !shown)}
            aria-expanded={showAnalytics}
            className={`mb-4 px-4 py-1.5 rounded-full text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 ${
              isNight
                ? "bg-white/20 text-white hover:bg-white/30 focus-visible:outline-white"
                : "bg-white/60 text-gray-700 hover:bg-white/90 focus-visible:outline-gray-800"
            }`}
          >
            {showAnalytics ? "Hide analytics ▲" : "Wardrobe analytics ▼"}
          </button>
        )}

        {showAnalytics && (
          <div aria-live="polite">
            {analyticsLoading && (
              <p className={`mb-6 ${isNight ? "text-white/80" : "text-gray-600"}`}>
                Crunching the numbers…
              </p>
            )}
            {analytics && <WardrobeAnalyticsPanel analytics={analytics} isNight={isNight} />}
          </div>
        )}

        {garments && garments.length > 0 && (
          <div
            className="flex flex-wrap items-center gap-2 mb-6"
            role="group"
            aria-label="Filter by laundry state"
          >
            {_FILTERS.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                onClick={() => setFilter(value)}
                aria-pressed={filter === value}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 ${
                  filter === value
                    ? "bg-gray-800 text-white focus-visible:outline-gray-800"
                    : isNight
                    ? "bg-white/20 text-white hover:bg-white/30 focus-visible:outline-white"
                    : "bg-white/60 text-gray-700 hover:bg-white/90 focus-visible:outline-gray-800"
                }`}
              >
                {label}
                {value === "laundry" && laundryCount > 0 && ` (${laundryCount})`}
              </button>
            ))}

            {laundryCount > 0 && (
              <button
                type="button"
                onClick={() => doLaundry.mutate()}
                disabled={doLaundry.isPending}
                className="w-full sm:w-auto sm:ml-auto px-4 py-1.5 rounded-full text-sm font-medium bg-blue-500 hover:bg-blue-600 text-white transition disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-800"
              >
                {doLaundry.isPending ? "Doing laundry…" : `Do Laundry (${laundryCount})`}
              </button>
            )}
          </div>
        )}

        <div aria-live="polite">
          {isLoading && (
            <p className={isNight ? "text-white/80" : "text-gray-600"}>Loading your wardrobe…</p>
          )}

          {isError && (
            <p role="alert" className={isNight ? "text-red-300" : "text-red-500"}>
              Couldn't load your wardrobe. Try refreshing.
            </p>
          )}

          {garments?.length === 0 && (
            <p className={isNight ? "text-white/80" : "text-gray-600"}>
              Nothing here yet — head to Upload to add your first garment.
            </p>
          )}

          {visible?.length === 0 && garments && garments.length > 0 && (
            <p className={isNight ? "text-white/80" : "text-gray-600"}>
              Nothing in "{filter}" right now.
            </p>
          )}
        </div>

        {visible && visible.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-4 sm:gap-5">
            {visible.map((garment) => (
              <GarmentCard
                key={garment.id}
                garment={garment}
                onSendToLaundry={(id) => sendToLaundry.mutate(id)}
                sendingToLaundry={sendToLaundry.isPending && sendToLaundry.variables === garment.id}
              />
            ))}
          </div>
        )}
      </div>

      <Navbar />
    </WardrobeBackground>
  );
}
