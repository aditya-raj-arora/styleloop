import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";

import {
  ApiError,
  generateOutfit,
  getCurrentUser,
  getDailyOutfit,
  listGarments,
  uploadBasePhoto,
  wearOutfit,
} from "../api/client";
import AnimatedBackground from "../components/AnimatedBackground";
import Navbar from "../components/Navbar";
import OnboardingChecklist from "../components/OnboardingChecklist";
import { useGeolocation } from "../hooks/useGeolocation";
import { useTryon } from "../hooks/useTryon";

export default function Dashboard() {
  const { coords, loading: locating } = useGeolocation();
  const queryClient = useQueryClient();
  const photoInputRef = useRef<HTMLInputElement>(null);

  const { data: user } = useQuery({ queryKey: ["me"], queryFn: getCurrentUser });

  const uploadPhoto = useMutation({
    mutationFn: uploadBasePhoto,
    onSuccess: (updatedUser) => {
      queryClient.setQueryData(["me"], updatedUser);
    },
  });

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

  const noWardrobeYet = error instanceof ApiError && error.status === 422;

  // Only needed to drive the first-run checklist below — don't fetch it
  // once the user already has a daily outfit.
  const { data: garments, isLoading: garmentsLoading } = useQuery({
    queryKey: ["garments"],
    queryFn: listGarments,
    enabled: noWardrobeYet,
  });

  const tryon = useTryon(outfit?.id);

  function handlePhotoChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) uploadPhoto.mutate(file);
    event.target.value = ""; // allow re-selecting the same file later
  }

  const hour = new Date().getHours();

  const greeting =
    hour >= 5 && hour < 12
      ? "Good Morning ☀️"
      : hour >= 12 && hour < 17
      ? "Good Afternoon 🌞"
      : hour >= 17 && hour < 20
      ? "Good Evening 🌇"
      : "Good Night 🌙";

  return (
    <AnimatedBackground>

      <div className="p-5 sm:p-8 pb-24">

        <h1 className="text-3xl sm:text-5xl font-bold text-white">
          {greeting}
        </h1>

        <p className="text-white/80 mt-2">
          Welcome back to VogueVault
        </p>

        <input
          ref={photoInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          className="hidden"
          onChange={handlePhotoChange}
          aria-label="Choose a photo of yourself for virtual try-on"
        />
        <div className="mt-3 flex flex-wrap items-center gap-2 text-sm max-w-[65%] sm:max-w-md">
          <span className="text-white/70">
            {user?.base_photo_url
              ? "📷 Try-on photo saved."
              : "📷 Add a photo of yourself to try outfits on."}
          </span>
          <button
            type="button"
            onClick={() => photoInputRef.current?.click()}
            disabled={uploadPhoto.isPending}
            className="text-amber-300 font-medium underline disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white rounded"
          >
            {uploadPhoto.isPending ? "Uploading…" : user?.base_photo_url ? "Update" : "Upload"}
          </button>
        </div>

        <div
          className="mt-8 sm:mt-12 min-h-[320px] sm:min-h-[400px] rounded-3xl border-2 border-dashed border-white/40 flex flex-col justify-center items-center gap-4 p-6 text-center"
          aria-live="polite"
        >

          {(locating || isLoading) && (
            <p className="text-white/70">Putting today's outfit together…</p>
          )}

          {!locating && noWardrobeYet && (
            <OnboardingChecklist
              garments={garments}
              garmentsLoading={garmentsLoading}
              hasBasePhoto={Boolean(user?.base_photo_url)}
            />
          )}

          {!locating && isError && !noWardrobeYet && (
            <p role="alert" className="text-white/70">
              Couldn't load today's outfit. Try refreshing.
            </p>
          )}

          {!locating && outfit && (
            <>
              <h2 className="text-2xl text-white">Today's Outfit</h2>
              <p className="text-white/60 text-sm">
                {outfit.garment_ids.length} item{outfit.garment_ids.length === 1 ? "" : "s"}
                {outfit.score !== null && ` · score ${outfit.score.toFixed(2)}`}
              </p>

              <div className="flex flex-wrap justify-center gap-3 mt-2">
                <button
                  type="button"
                  onClick={() => regenerate.mutate()}
                  disabled={regenerate.isPending}
                  className="bg-white/20 hover:bg-white/30 text-white px-5 py-2 rounded-full transition disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
                >
                  {regenerate.isPending ? "Regenerating…" : "Regenerate"}
                </button>
                <button
                  type="button"
                  onClick={() => wear.mutate(outfit.id)}
                  disabled={wear.isPending}
                  className="bg-green-500 hover:bg-green-600 text-white px-5 py-2 rounded-full transition disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
                >
                  {wear.isPending ? "Marking worn…" : "Wore this"}
                </button>

                {user?.base_photo_url && tryon.status === "idle" && (
                  <button
                    type="button"
                    onClick={() => tryon.start()}
                    className="bg-purple-500 hover:bg-purple-600 text-white px-5 py-2 rounded-full transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-white"
                  >
                    Try it on
                  </button>
                )}
              </div>

              {wear.isSuccess && (
                <p className="text-white/70 text-xs mt-1">Logged — enjoy!</p>
              )}

              {tryon.status === "pending" && (
                <p className="text-white/70 text-sm mt-2">Rendering on your photo…</p>
              )}

              {tryon.status === "ready" && tryon.imageUrl && (
                <img
                  src={tryon.imageUrl}
                  alt="This outfit rendered on your photo"
                  className="mt-3 max-h-72 rounded-2xl shadow-lg"
                />
              )}

              {tryon.status === "failed" && (
                <div className="mt-2 text-center">
                  <p role="alert" className="text-white/70 text-sm">
                    {tryon.errorMessage ?? "Couldn't render right now."}
                  </p>
                  <button
                    type="button"
                    onClick={() => tryon.start()}
                    className="text-amber-300 text-sm font-medium underline mt-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-white rounded"
                  >
                    Try again
                  </button>
                </div>
              )}
            </>
          )}

        </div>

      </div>

      <Navbar />

    </AnimatedBackground>
  );
}
