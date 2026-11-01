import { useQuery } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { api } from "../api";
import { AccountSecurity, UserManagement } from "../components/Operations";

import { PageTitle } from "../components/common";
export function SettingsPage() {
  const { data } = useQuery({ queryKey: ["me"], queryFn: () => api("/me") });
  return (
    <>
      <PageTitle
        title="Workspace settings"
        subtitle="Organization identity, runtime configuration, and user access."
      />
      <section className="panel">
        <div className="panel-heading">
          <h2>Organization & AI runtime</h2>
          <ShieldCheck size={18} />
        </div>
        <div className="detail-grid">
          {data &&
            Object.entries({
              Organization: data.organization,
              "Signed in as": data.user.email,
              Role: data.user.role,
              "AI mode": data.mode,
              "Live credentials": data.live_ready
                ? "Configured on server"
                : "Not configured (Demo Mode needs no key)",
              Provider: data.provider,
              Model: data.model,
            }).map(([k, v]) => (
              <div key={k}>
                <span>{k}</span>
                <strong>{String(v)}</strong>
              </div>
            ))}
        </div>
        <div className="notice">
          AI credentials and model settings are configured on the backend
          through .env. API keys are never returned to the browser.
        </div>
      </section>
      {data?.user.role === "admin" && <UserManagement />}
      <AccountSecurity />
    </>
  );
}
