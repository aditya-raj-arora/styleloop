// Login / signup page.
// Email + password form -> POST /auth/login or /auth/signup -> useAuth.setToken(jwt)
// -> redirect to wherever RequireAuth sent the user from (default: /dashboard).

import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import type { FormEvent } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { ApiError, login, signup } from "../api/client";
import { useAuth } from "../store/useAuth";

type Mode = "login" | "signup";

export default function Login() {
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const setToken = useAuth((state) => state.setToken);
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? "/dashboard";

  const mutation = useMutation({
    mutationFn: () => (mode === "login" ? login(email, password) : signup(email, password)),
    onSuccess: (token) => {
      setToken(token.access_token);
      navigate(from, { replace: true });
    },
  });

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    mutation.mutate();
  }

  return (
    <div className="h-screen flex flex-col justify-center items-center gap-8 px-6">
      <h1 className="text-4xl font-bold">VogueVault</h1>

      <form
        onSubmit={handleSubmit}
        className="w-full max-w-xs flex flex-col gap-4"
      >
        <div className="flex flex-col gap-1">
          <label htmlFor="email" className="text-sm text-gray-500">
            Email
          </label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="px-4 py-2 rounded-xl border border-gray-300"
          />
        </div>

        <div className="flex flex-col gap-1">
          <label htmlFor="password" className="text-sm text-gray-500">
            Password
          </label>
          <input
            id="password"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
            minLength={mode === "signup" ? 8 : undefined}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="px-4 py-2 rounded-xl border border-gray-300"
          />
        </div>

        <button
          type="submit"
          disabled={mutation.isPending}
          className="mt-4 px-6 py-3 bg-amber-400 rounded-xl font-semibold disabled:opacity-60"
        >
          {mutation.isPending ? "Please wait…" : mode === "login" ? "Login" : "Sign up"}
        </button>
      </form>

      {mutation.isError && (
        <p role="alert" className="text-red-500 text-sm">
          {mutation.error instanceof ApiError ? mutation.error.message : "Something went wrong."}
        </p>
      )}

      <p className="text-sm text-gray-500">
        {mode === "login" ? "Need an account? " : "Already have an account? "}
        <button
          type="button"
          onClick={() => setMode(mode === "login" ? "signup" : "login")}
          className="text-amber-500 font-semibold"
        >
          {mode === "login" ? "Sign up" : "Log in"}
        </button>
      </p>
    </div>
  );
}