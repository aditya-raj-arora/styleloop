import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { generateOutfit, getDailyOutfit, sendOutfitFeedback } from "../api/client";
import Navbar from "../components/Navbar";
import { useGeolocation } from "../hooks/useGeolocation";

// NOTE(Dev C): this page swipes on the *daily outfit* (GET /outfits/daily),
// not single garments, so it doesn't reuse GarmentCard — that component is
// typed to the real single-Garment API shape from the Sprint 1 upload
// pipeline. The contract only carries garment_ids (numbers), not a photo or
// title to render, so this is a plain summary card rather than a photo swipe
// until try-on (Sprint 4) gives us something to actually show.
function OutfitCard({ itemCount, score }: { itemCount: number; score: number | null }) {
  return (
    <div className="rounded-2xl overflow-hidden shadow-lg bg-black text-white p-8 flex flex-col items-center justify-center h-[420px] gap-2">
      <h2 className="text-3xl font-semibold">Today's Outfit</h2>
      <p className="text-white/70">
        {itemCount} item{itemCount === 1 ? "" : "s"}
        {score !== null && ` · score ${score.toFixed(2)}`}
      </p>
    </div>
  );
}

export default function Swipe() {
  const { coords, loading: locating } = useGeolocation();
  const queryClient = useQueryClient();

  const { data: outfit, isLoading } = useQuery({
    queryKey: ["outfits", "daily"],
    queryFn: () => getDailyOutfit(coords),
    enabled: !locating,
  });

  // Skip = "dislike" this suggestion, then regenerate a fresh one to swipe
  // on. Like = record the preference and keep today's outfit as-is (nothing
  // left to swipe to — a single daily suggestion, not a deck).
  const skip = useMutation({
    mutationFn: async (outfitId: number) => {
      await sendOutfitFeedback(outfitId, "dislike");
      return generateOutfit(coords);
    },
    onSuccess: (newOutfit) => {
      queryClient.setQueryData(["outfits", "daily"], newOutfit);
    },
  });

  const like = useMutation({
    mutationFn: (outfitId: number) => sendOutfitFeedback(outfitId, "like"),
  });

  const busy = skip.isPending || like.isPending;

  return (
    <>
      <div className="p-5">
        {(locating || isLoading) && <p className="text-center text-gray-600">Loading…</p>}

        {!locating && !isLoading && !outfit && (
          <p className="text-center text-gray-600">
            Nothing to show yet — add a few tagged clean garments first.
          </p>
        )}

        {outfit && (
          <>
            <OutfitCard itemCount={outfit.garment_ids.length} score={outfit.score} />

            <div className="flex justify-center gap-5 mt-6">
              <button
                onClick={() => skip.mutate(outfit.id)}
                disabled={busy}
                className="bg-red-500 px-6 py-2 rounded disabled:opacity-50"
              >
                Skip
              </button>

              <button
                onClick={() => like.mutate(outfit.id)}
                disabled={busy || like.isSuccess}
                className="bg-green-500 px-6 py-2 rounded disabled:opacity-50"
              >
                {like.isSuccess ? "Liked!" : "Like"}
              </button>
            </div>
          </>
        )}
      </div>

      <Navbar />
    </>
  );
}
