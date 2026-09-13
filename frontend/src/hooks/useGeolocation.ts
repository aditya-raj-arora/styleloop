// Best-effort browser geolocation for weather-aware outfit generation.
//
// Never blocks the caller: on denial, unsupported browsers, or a slow GPS fix
// it just resolves to `undefined`, and the outfits API falls back to a fixed
// default city server-side (see backend/app/config.py's DEFAULT_LAT/LON).
import { useEffect, useState } from "react";

export interface Coords {
  lat: number;
  lon: number;
}

const _TIMEOUT_MS = 5000;

export function useGeolocation(): { coords: Coords | undefined; loading: boolean } {
  const [coords, setCoords] = useState<Coords | undefined>(undefined);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!("geolocation" in navigator)) {
      setLoading(false);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCoords({ lat: position.coords.latitude, lon: position.coords.longitude });
        setLoading(false);
      },
      () => setLoading(false), // denied/unavailable — fall back server-side
      { timeout: _TIMEOUT_MS },
    );
  }, []);

  return { coords, loading };
}
