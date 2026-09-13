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

export interface User {
  id: number;
  email: string;
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
