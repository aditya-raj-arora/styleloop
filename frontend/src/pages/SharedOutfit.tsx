import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";

import { ApiError, getSharedOutfit } from "../api/client";
import AnimatedBackground from "../components/AnimatedBackground";

// Public, unauthenticated view of a shared outfit (GET /outfits/shared/:token
// — no Bearer token required or sent for anything the viewer needs to see).
// Reachable by anyone with the link; a revoked or never-issued token 404s.
export default function SharedOutfit() {
  const { token } = useParams<{ token: string }>();

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ["shared-outfit", token],
    queryFn: () => getSharedOutfit(token!),
    enabled: Boolean(token),
    retry: false,
  });

  const notFound = error instanceof ApiError && error.status === 404;

  return (
    <AnimatedBackground>
      <div className="p-5 sm:p-8 pb-16 max-w-2xl mx-auto">
        <Link to="/" className="text-white/70 text-sm hover:text-white transition">
          ← VogueVault
        </Link>

        <h1 className="text-3xl sm:text-4xl font-bold text-white mt-3">
          Shared Outfit
        </h1>

        <div className="mt-8 min-h-[240px]" aria-live="polite">
          {isLoading && <p className="text-white/70">Loading outfit…</p>}

          {notFound && (
            <>
              <h2 className="text-xl text-white">Link not found</h2>
              <p className="text-white/60 text-sm mt-2 max-w-sm">
                This share link has expired, been revoked, or never existed.
              </p>
            </>
          )}

          {isError && !notFound && (
            <p role="alert" className="text-white/70">
              Couldn't load this outfit. Try refreshing.
            </p>
          )}

          {data && (
            <>
              <p className="text-white/60 text-sm mb-4">
                {new Date(data.generated_for).toLocaleDateString(undefined, {
                  weekday: "long",
                  month: "long",
                  day: "numeric",
                })}
                {data.score !== null && ` · score ${data.score.toFixed(2)}`}
              </p>

              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 sm:gap-5">
                {data.garments.map((garment, i) => (
                  <div
                    key={i}
                    className="relative rounded-3xl overflow-hidden bg-white/30 backdrop-blur-xl border border-white/30 shadow-lg"
                  >
                    <img
                      src={garment.processed_url ?? garment.image_url}
                      alt={garment.category ?? "Garment"}
                      className="w-full aspect-square object-cover"
                    />
                    {(garment.category || garment.colors?.length) && (
                      <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/60 to-transparent">
                        <p className="text-white text-sm capitalize">
                          {[garment.category, garment.colors?.[0]].filter(Boolean).join(" · ")}
                        </p>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              <p className="text-white/50 text-xs mt-8 text-center">
                Made with VogueVault —{" "}
                <Link to="/" className="underline hover:text-white/80">
                  build your own wardrobe
                </Link>
              </p>
            </>
          )}
        </div>
      </div>
    </AnimatedBackground>
  );
}
