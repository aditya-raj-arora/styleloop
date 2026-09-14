// Drives the "Try it on" flow: kick off a render, poll until it's ready, and
// give up gracefully after a while — the backend's own per-garment render
// budget (services/tryon.py) can run close to a minute for a two-garment
// outfit, longer than a UI should silently spin, but the worker keeps going
// after we stop polling: the *next* "Try it on" click hits the cache
// instantly if it finished in the meantime, so "failed" here means "not yet
// — try again shortly," not "this outfit can never be rendered."
import { useCallback, useEffect, useState } from "react";

import { ApiError, getTryon, requestTryon } from "../api/client";

export type TryonStatus = "idle" | "pending" | "ready" | "failed";

interface TryonState {
  status: TryonStatus;
  imageUrl?: string;
  errorMessage?: string;
}

const _POLL_INTERVAL_MS = 2000;
const _MAX_POLL_ATTEMPTS = 15; // ~30s of polling before giving up for now

export function useTryon(outfitId: number | undefined) {
  const [state, setState] = useState<TryonState>({ status: "idle" });

  // A different outfit (regenerate, new day) invalidates whatever we were
  // showing or waiting on.
  useEffect(() => {
    setState({ status: "idle" });
  }, [outfitId]);

  const start = useCallback(async () => {
    if (outfitId === undefined) return;
    setState({ status: "pending" });
    try {
      const result = await requestTryon(outfitId);
      if (result.status === "ready" && result.rendered_url) {
        setState({ status: "ready", imageUrl: result.rendered_url });
      }
      // else stays "pending" — the poll effect below takes over.
    } catch (err) {
      setState({
        status: "failed",
        errorMessage: err instanceof ApiError ? err.message : "Couldn't start the render.",
      });
    }
  }, [outfitId]);

  useEffect(() => {
    if (state.status !== "pending" || outfitId === undefined) return;

    let cancelled = false;
    let attempts = 0;

    const interval = setInterval(async () => {
      attempts += 1;
      try {
        const result = await getTryon(outfitId);
        if (cancelled) return;
        if (result.status === "ready" && result.rendered_url) {
          setState({ status: "ready", imageUrl: result.rendered_url });
        } else if (attempts >= _MAX_POLL_ATTEMPTS) {
          setState({ status: "failed", errorMessage: "Taking longer than usual." });
        }
      } catch {
        if (!cancelled) {
          setState({ status: "failed", errorMessage: "Lost connection while rendering." });
        }
      }
    }, _POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [state.status, outfitId]);

  return { ...state, start };
}
