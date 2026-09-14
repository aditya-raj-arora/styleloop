// Thin fetch wrapper around the VogueVault API.
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

// Mirrors backend/app/schemas/auth.py.
export interface Token {
  access_token: string;
  token_type: string;
}

// Mirrors backend/app/schemas/auth.py::UserOut. `base_photo_url` is an
// already-presigned download URL (or null until POST /auth/me/photo);
// `base_photo_version` is the virtual try-on cache key's version component.
export interface User {
  id: number;
  email: string;
  base_photo_url: string | null;
  base_photo_version: number;
  created_at: string;
}

// Mirrors backend/app/schemas/outfit.py::OutfitOut — the Sprint 2 GET
// /outfits/daily contract. Dashboard/Swipe mock data is shaped against this
// now (Sprint 1) so swapping in the real endpoint later is a data-source
// change, not a type rework. Note garment_ids is just ids, not embedded
// Garment objects — rendering an outfit's actual photos needs a follow-up
// fetch (or a richer response) once the real endpoint exists.
export interface Outfit {
  id: number;
  user_id: number;
  garment_ids: number[];
  score: number | null;
  generated_for: string;
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

async function _handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let detail = `Request failed: ${response.status}`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      // Non-JSON error body — fall back to the generic message above.
    }
    if (response.status === 401) {
      // Token is missing/expired/invalid — the persisted token now outlives
      // a refresh, so without this the user would sit "logged in" while
      // every request silently 401s. Clear it so RequireAuth sends them
      // back to login instead.
      useAuth.getState().clear();
    }
    throw new ApiError(response.status, detail);
  }
  return (await response.json()) as T;
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
  return _handleResponse<T>(response);
}

// Like apiFetch, but for multipart/form-data bodies — never set Content-Type
// manually for these; the browser must generate it (it includes the boundary).
export async function apiUpload<T>(path: string, form: FormData): Promise<T> {
  const token = useAuth.getState().token;
  const headers = new Headers();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${BASE_URL}${path}`, { method: "POST", headers, body: form });
  return _handleResponse<T>(response);
}

export function signup(email: string, password: string): Promise<Token> {
  return apiFetch<Token>("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function login(email: string, password: string): Promise<Token> {
  return apiFetch<Token>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function getCurrentUser(): Promise<User> {
  return apiFetch<User>("/auth/me");
}

// Sets (or replaces) the virtual try-on base photo. Bumps base_photo_version
// server-side, which invalidates old cached try-on renders.
export function uploadBasePhoto(file: File): Promise<User> {
  const form = new FormData();
  form.append("file", file);
  return apiUpload<User>("/auth/me/photo", form);
}

// --- Garments ---

export function listGarments(): Promise<Garment[]> {
  return apiFetch<Garment[]>("/garments");
}

export function getGarment(id: number): Promise<Garment> {
  return apiFetch<Garment>(`/garments/${id}`);
}

export function uploadGarment(file: File): Promise<Garment> {
  const form = new FormData();
  form.append("file", file);
  return apiUpload<Garment>("/garments", form);
}

export interface TagUpdate {
  category?: string | null;
  colors?: string[] | null;
  pattern?: string | null;
  fabric?: string | null;
  season?: string | null;
  formality?: string | null;
}

export function updateGarmentTags(id: number, tags: TagUpdate): Promise<Garment> {
  return apiFetch<Garment>(`/garments/${id}/tags`, {
    method: "PATCH",
    body: JSON.stringify(tags),
  });
}

export type GarmentState = "clean" | "worn" | "laundry";

export function setGarmentState(id: number, state: GarmentState): Promise<Garment> {
  return apiFetch<Garment>(`/garments/${id}/state`, {
    method: "POST",
    body: JSON.stringify({ state }),
  });
}

// Bulk "do laundry": every 'laundry'-state garment goes back to 'clean' in
// one call. Returns the garments that were reset (empty array if there
// weren't any).
export function resetLaundry(): Promise<Garment[]> {
  return apiFetch<Garment[]>("/garments/laundry/reset", { method: "POST" });
}

// --- Outfits (rotation engine, Sprint 2) ---
//
// `lat`/`lon` come from the browser's geolocation (see useGeolocation); the
// backend falls back to a fixed default city when omitted, so both are
// optional here too.

function _coordsQuery(coords?: { lat: number; lon: number }): string {
  if (!coords) return "";
  return `?lat=${coords.lat}&lon=${coords.lon}`;
}

export function getDailyOutfit(coords?: { lat: number; lon: number }): Promise<Outfit> {
  return apiFetch<Outfit>(`/outfits/daily${_coordsQuery(coords)}`);
}

export function generateOutfit(coords?: { lat: number; lon: number }): Promise<Outfit> {
  return apiFetch<Outfit>(`/outfits/generate${_coordsQuery(coords)}`, { method: "POST" });
}

export type FeedbackAction = "like" | "dislike" | "skip";

export function sendOutfitFeedback(id: number, action: FeedbackAction): Promise<{ status: string }> {
  return apiFetch<{ status: string }>(`/outfits/${id}/feedback`, {
    method: "POST",
    body: JSON.stringify({ action }),
  });
}

export function wearOutfit(id: number): Promise<{ status: string; garment_ids: number[] }> {
  return apiFetch<{ status: string; garment_ids: number[] }>(`/outfits/${id}/wear`, {
    method: "POST",
  });
}

// --- Virtual try-on (Sprint 4) ---
//
// Mirrors backend/app/schemas/tryon.py::TryonOut. `rendered_url` is a
// presigned download URL, set only once `status` is "ready". A cache hit on
// POST returns "ready" immediately; a miss enqueues generation and returns
// "pending" — poll GET until it flips (or give up after a while and fall
// back to the flat outfit view — generation can fail silently server-side).
export interface TryonResult {
  status: "pending" | "ready";
  rendered_url: string | null;
}

export function requestTryon(outfitId: number): Promise<TryonResult> {
  return apiFetch<TryonResult>(`/outfits/${outfitId}/tryon`, { method: "POST" });
}

export function getTryon(outfitId: number): Promise<TryonResult> {
  return apiFetch<TryonResult>(`/outfits/${outfitId}/tryon`);
}
