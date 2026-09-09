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
    <main>
      <h1>{mode === "login" ? "Log in" : "Sign up"}</h1>
      <form onSubmit={handleSubmit}>
        <div>
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <div>
          <label htmlFor="password">Password</label>
          <input
            id="password"
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
            minLength={mode === "signup" ? 8 : undefined}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
        </div>
        <button type="submit" disabled={mutation.isPending}>
          {mutation.isPending ? "Please wait…" : mode === "login" ? "Log in" : "Sign up"}
        </button>
      </form>

      {mutation.isError && (
        <p role="alert">
          {mutation.error instanceof ApiError ? mutation.error.message : "Something went wrong."}
        </p>
      )}

      <p>
        {mode === "login" ? "Need an account? " : "Already have an account? "}
        <button
          type="button"
          onClick={() => setMode(mode === "login" ? "signup" : "login")}
        >
          {mode === "login" ? "Sign up" : "Log in"}
        </button>
      </p>
    </main>
  );
}
