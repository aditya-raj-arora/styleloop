// Thin fetch wrapper around the StyleLoop API.
//
// `Garment` mirrors the FROZEN CONTRACT defined by the backend at
// backend/app/schemas/garment.py::GarmentOut. Keep these in lockstep.

import { useAuth } from "../store/useAuth";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Garment {
  id: number;
  user_id: number;
  image_url: string;
  processed_url: string | null;
  category: string | null;
  colors: string[] | null;
  pattern: string | null;
  fabric: string | null;
  fabric_confidence: number | null;
  season: string | null;
  formality: string | null;
  state: string;
  wear_count: number;
  last_worn_at: string | null;
  created_at: string;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function apiFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  const token = useAuth.getState().token;
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) {
    // JWT is sent as `Authorization: Bearer <token>`.
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${BASE_URL}${path}`, { ...init, headers });
  if (!response.ok) {
    throw new ApiError(response.status, `Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}
