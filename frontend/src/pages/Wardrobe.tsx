import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import type { Garment, GarmentState } from "../api/client";
import { listGarments, resetLaundry, setGarmentState } from "../api/client";
import GarmentCard from "../components/GarmentCard";
import Navbar from "../components/Navbar";
import WardrobeBackground from "../components/wardrobeBackground";

type Filter = "all" | GarmentState;

const _FILTERS: { value: Filter; label: string }[] = [
  { value: "all", label: "All" },
  { value: "clean", label: "Clean" },
  { value: "worn", label: "Worn" },
  { value: "laundry", label: "Laundry" },
];

export default function Wardrobe() {
  const [filter, setFilter] = useState<Filter>("all");
  const queryClient = useQueryClient();

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

  return (
    <WardrobeBackground>
      <div className="p-6 pb-24">
        <h1 className="text-4xl font-bold text-gray-800">My Wardrobe</h1>

        <p className="text-gray-600 mt-2 mb-4">
          {garments?.length
            ? `${garments.length} item${garments.length === 1 ? "" : "s"} in your closet.`
            : "Your uploaded clothes, all in one place."}
        </p>

        {garments && garments.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 mb-6">
            {_FILTERS.map(({ value, label }) => (
              <button
                key={value}
                type="button"
                onClick={() => setFilter(value)}
                className={`px-4 py-1.5 rounded-full text-sm font-medium transition ${
                  filter === value
                    ? "bg-gray-800 text-white"
                    : "bg-white/60 text-gray-700 hover:bg-white/90"
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
                className="ml-auto px-4 py-1.5 rounded-full text-sm font-medium bg-blue-500 hover:bg-blue-600 text-white transition disabled:opacity-50"
              >
                {doLaundry.isPending ? "Doing laundry…" : `Do Laundry (${laundryCount})`}
              </button>
            )}
          </div>
        )}

        {isLoading && <p className="text-gray-600">Loading your wardrobe…</p>}

        {isError && (
          <p className="text-red-500">Couldn't load your wardrobe. Try refreshing.</p>
        )}

        {garments?.length === 0 && (
          <p className="text-gray-600">
            Nothing here yet — head to Upload to add your first garment.
          </p>
        )}

        {visible?.length === 0 && garments && garments.length > 0 && (
          <p className="text-gray-600">Nothing in "{filter}" right now.</p>
        )}

        {visible && visible.length > 0 && (
          <div className="grid grid-cols-2 gap-5">
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
