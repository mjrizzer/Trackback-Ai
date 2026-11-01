import {
  ArrowRight,
  Box,
  FlaskConical,
  GitBranch,
  ShieldCheck,
  Truck,
  Users,
} from "lucide-react";
import React, { useState } from "react";
import { api } from "../api";
import { Button } from "../components/ui/button";

import { ErrorBox } from "../components/common";
export function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [register, setRegister] = useState(false),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    const data = Object.fromEntries(new FormData(e.currentTarget));
    try {
      const result = await api(`/auth/${register ? "register" : "login"}`, {
        method: "POST",
        body: JSON.stringify(data),
      });
      sessionStorage.setItem("traceback-session", "1");
      onLogin();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="login">
      <section className="login-story">
        <div className="brand">
          <div className="brand-mark">
            <GitBranch />
          </div>
          traceback<span>AI</span>
        </div>
        <div>
          <div className="eyebrow">FROM INCIDENT TO INSIGHT</div>
          <h1>
            Every connection.
            <br />
            Every piece of evidence.
            <br />
            <em>One clear picture.</em>
          </h1>
          <p>
            Investigate industrial incidents with coordinated agents, verified
            supply chain records, and human oversight.
          </p>
          <div className="login-flow">
            <Box />
            <span />
            <FlaskConical />
            <span />
            <Truck />
            <span />
            <Users />
          </div>
        </div>
        <small>TRACEBACK AI / INDUSTRIAL INVESTIGATION PLATFORM</small>
      </section>
      <section className="login-form">
        <form onSubmit={submit}>
          <div className="eyebrow">YOUR INVESTIGATION WORKSPACE</div>
          <h1>{register ? "Create your workspace" : "Welcome back"}</h1>
          <p>
            {register
              ? "Start with a new, isolated organization."
              : "Sign in to your investigation workspace."}
          </p>
          {register && (
            <>
              <label>
                Full name
                <input name="name" required minLength={2} />
              </label>
              <label>
                Organization
                <input name="organization" required minLength={2} />
              </label>
            </>
          )}
          <label>
            Email address
            <input
              type="email"
              name="email"
              required
              defaultValue={register ? "" : "admin@novafoods.demo"}
            />
          </label>
          <label>
            Password
            <input
              name="password"
              type="password"
              required
              minLength={register ? 10 : 1}
              defaultValue={register ? "" : "NovaFoods!2026"}
            />
          </label>
          <ErrorBox error={error} />
          <Button disabled={busy} type="submit">
            {busy
              ? "Signing in…"
              : register
                ? "Create organization"
                : "Sign in to workspace"}
            <ArrowRight size={16} />
          </Button>
          <button
            type="button"
            className="text-button"
            onClick={() => {
              setRegister(!register);
              setError("");
            }}
          >
            {register
              ? "Already have an account? Sign in"
              : "Create a separate organization"}
          </button>
          <div className="demo-hint">
            <ShieldCheck size={20} />
            <div>
              <strong>Fictional demonstration environment</strong>
              <p>
                Demo credentials are prefilled. All operational actions are
                internal simulations.
              </p>
            </div>
          </div>
        </form>
      </section>
    </div>
  );
}
