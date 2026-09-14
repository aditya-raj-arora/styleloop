// Shared day/night clock for the time-themed page backgrounds
// (WardrobeBackground, AnimatedBackground) — same >=20 or <5 cutoff both
// already used, now in one place so page content can match its background's
// night mode instead of assuming an always-light (or always-dark) ground.
import { useEffect, useState } from "react";

function _isNight(hour: number): boolean {
  return hour >= 20 || hour < 5;
}

export function useIsNight(): boolean {
  const [isNight, setIsNight] = useState(() => _isNight(new Date().getHours()));

  useEffect(() => {
    const timer = setInterval(() => {
      setIsNight(_isNight(new Date().getHours()));
    }, 60000);

    return () => clearInterval(timer);
  }, []);

  return isNight;
}
