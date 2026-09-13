import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiError, generateOutfit, getDailyOutfit, wearOutfit } from "../api/client";
import AnimatedBackground from "../components/AnimatedBackground";
import Navbar from "../components/Navbar";
import { useGeolocation } from "../hooks/useGeolocation";

export default function Dashboard() {
  const { coords, loading: locating } = useGeolocation();
  const queryClient = useQueryClient();

  // Wait for the (best-effort, capped) geolocation attempt to settle before
  // asking for today's outfit, so the very first request already carries
  // real coordinates instead of firing once without them and again after.
  const {
    data: outfit,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ["outfits", "daily"],
    queryFn: () => getDailyOutfit(coords),
    enabled: !locating,
  });

  const regenerate = useMutation({
    mutationFn: () => generateOutfit(coords),
    onSuccess: (newOutfit) => {
      queryClient.setQueryData(["outfits", "daily"], newOutfit);
    },
  });

  const wear = useMutation({
    mutationFn: (outfitId: number) => wearOutfit(outfitId),
    onSuccess: () => {
      // The worn garments are no longer 'clean', so both the wardrobe grid
      // and tomorrow's candidate pool need to reflect that.
      queryClient.invalidateQueries({ queryKey: ["garments"] });
    },
  });

  const hour = new Date().getHours();

  const greeting =
    hour >= 5 && hour < 12
      ? "Good Morning ☀️"
      : hour >= 12 && hour < 17
      ? "Good Afternoon 🌞"
      : hour >= 17 && hour < 20
      ? "Good Evening 🌇"
      : "Good Night 🌙";

  const noWardrobeYet = error instanceof ApiError && error.status === 422;

  return (
    <AnimatedBackground>

      <div className="p-8 pb-24">

        <h1 className="text-5xl font-bold text-white">
          {greeting}
        </h1>

        <p className="text-white/80 mt-2">
          Welcome back to VogueVault
        </p>

        <div className="mt-12 min-h-[400px] rounded-3xl border-2 border-dashed border-white/40 flex flex-col justify-center items-center gap-4 p-6 text-center">

          {(locating || isLoading) && (
            <p className="text-white/70">Putting today's outfit together…</p>
          )}

          {!locating && noWardrobeYet && (
            <>
              <h2 className="text-2xl text-white">No outfit yet</h2>
              <p className="text-white/60 text-sm max-w-xs">
                Upload and tag a few clean garments (at least a top + bottom, or a
                dress) and today's suggestion will show up here.
              </p>
            </>
          )}

          {!locating && isError && !noWardrobeYet && (
            <p className="text-white/70">Couldn't load today's outfit. Try refreshing.</p>
          )}

          {!locating && outfit && (
            <>
              <h2 className="text-2xl text-white">Today's Outfit</h2>
              <p className="text-white/60 text-sm">
                {outfit.garment_ids.length} item{outfit.garment_ids.length === 1 ? "" : "s"}
                {outfit.score !== null && ` · score ${outfit.score.toFixed(2)}`}
              </p>

              <div className="flex gap-3 mt-2">
                <button
                  onClick={() => regenerate.mutate()}
                  disabled={regenerate.isPending}
                  className="bg-white/20 hover:bg-white/30 text-white px-5 py-2 rounded-full transition"
                >
                  {regenerate.isPending ? "Regenerating…" : "Regenerate"}
                </button>
                <button
                  onClick={() => wear.mutate(outfit.id)}
                  disabled={wear.isPending}
                  className="bg-green-500 hover:bg-green-600 text-white px-5 py-2 rounded-full transition"
                >
                  {wear.isPending ? "Marking worn…" : "Wore this"}
                </button>
              </div>

              {wear.isSuccess && (
                <p className="text-white/70 text-xs mt-1">Logged — enjoy!</p>
              )}
            </>
          )}

        </div>

      </div>

      <Navbar />

    </AnimatedBackground>
  );
}
