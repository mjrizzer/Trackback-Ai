import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { api, Row } from "../api";
import { Button } from "./ui/button";

export function DraftAction({ investigationId }: { investigationId?: number }) {
  const { data = [] } = useQuery<Row[]>({
    queryKey: ["investigations"],
    queryFn: () => api("/records/investigations"),
  });
  const [open, setOpen] = useState(false),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  const query = useQueryClient();
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const raw = Object.fromEntries(new FormData(e.currentTarget));
    try {
      await api("/proposals", {
        method: "POST",
        body: JSON.stringify({
          ...raw,
          investigation_id: Number(raw.investigation_id),
        }),
      });
      query.invalidateQueries();
      setOpen(false);
      setMessage(
        "Proposal drafted. Human approval is required before any simulated action.",
      );
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel" style={{ padding: 20 }}>
      <div className="panel-heading" style={{ padding: "0 0 14px" }}>
        <h2>
          <ShieldCheck size={18} /> Human-supervised response planning
        </h2>
        <Button variant="outline" onClick={() => setOpen(!open)}>
          <Plus size={15} />
          {open ? "Close draft" : "Draft action"}
        </Button>
      </div>
      {message && (
        <div className="notice" role="status">
          {message}
        </div>
      )}
      {open && (
        <form onSubmit={submit}>
          <div className="form-grid">
            <label>
              Investigation
              <select
                name="investigation_id"
                defaultValue={investigationId}
                required
              >
                <option value="">Select completed findings</option>
                {data
                  .filter(
                    (i) =>
                      i.result.trace &&
                      (!investigationId || i.id === investigationId),
                  )
                  .map((i) => (
                    <option value={i.id} key={i.id}>
                      Investigation {i.id} · incident {i.incident_id}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              Proposed action
              <select name="kind">
                {[
                  "inventory_hold",
                  "inventory_release",
                  "supplier_escalation",
                  "customer_notification",
                  "corrective_assignment",
                ].map((k) => (
                  <option key={k} value={k}>
                    {k.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label>
            Justification or notification draft
            <textarea
              name="justification"
              minLength={10}
              maxLength={4000}
              required
              placeholder="Explain the intended action, responsible team, and supporting findings."
            />
          </label>
          <p className="muted" style={{ fontSize: 11 }}>
            Targets and evidence are taken from the selected investigation.
            Notifications and assignments remain internal drafts after approval;
            no external messages are sent.
          </p>
          <Button type="submit" disabled={busy}>
            Submit for human review
          </Button>
        </form>
      )}
    </section>
  );
}

export function ReviseAction({ id }: { id: number }) {
  const [message, setMessage] = useState(""),
    query = useQueryClient();
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const raw = Object.fromEntries(new FormData(e.currentTarget));
    try {
      await api(`/proposals/${id}/revise`, {
        method: "POST",
        body: JSON.stringify(raw),
      });
      query.invalidateQueries();
    } catch (e) {
      setMessage((e as Error).message);
    }
  }
  return (
    <form onSubmit={submit}>
      <label>
        Revised justification
        <textarea
          name="justification"
          minLength={10}
          maxLength={4000}
          required
          placeholder="Address the reviewer's request. The previous review remains in approval history."
        />
      </label>
      {message && <div className="error">{message}</div>}
      <Button type="submit">Resubmit for review</Button>
    </form>
  );
}

export function UserManagement() {
  const { data = [] } = useQuery<Row[]>({
      queryKey: ["users"],
      queryFn: () => api("/records/users"),
    }),
    { data: me } = useQuery({ queryKey: ["me"], queryFn: () => api("/me") });
  const [open, setOpen] = useState(false),
    [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false),
    query = useQueryClient();
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    setBusy(true);
    try {
      await api("/users", {
        method: "POST",
        body: JSON.stringify(Object.fromEntries(new FormData(form))),
      });
      query.invalidateQueries({ queryKey: ["users"] });
      form.reset();
      setOpen(false);
      setMessage("Workspace member created.");
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function role(id: number, value: string) {
    try {
      await api(`/users/${id}/role`, {
        method: "PATCH",
        body: JSON.stringify({ role: value }),
      });
      query.invalidateQueries({ queryKey: ["users"] });
      setMessage("Role updated and audited.");
    } catch (e) {
      setMessage((e as Error).message);
    }
  }
  return (
    <section className="panel">
      <div className="panel-heading">
        <h2>Workspace members</h2>
        <Button onClick={() => setOpen(!open)}>
          <Plus size={15} />
          {open ? "Close form" : "Add member"}
        </Button>
      </div>
      {message && (
        <div className="notice" role="status">
          {message}
        </div>
      )}
      {open && (
        <form onSubmit={submit} style={{ padding: "0 22px 22px" }}>
          <div className="form-grid">
            <label>
              Name
              <input name="name" required minLength={2} />
            </label>
            <label>
              Email
              <input name="email" type="email" required />
            </label>
            <label>
              Temporary password
              <input
                name="password"
                type="password"
                minLength={10}
                maxLength={128}
                required
              />
            </label>
            <label>
              Role
              <select name="role">
                <option>analyst</option>
                <option>reviewer</option>
                <option>admin</option>
              </select>
            </label>
          </div>
          <Button type="submit" disabled={busy}>
            Create member
          </Button>
        </form>
      )}
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Email</th>
              <th>Role</th>
            </tr>
          </thead>
          <tbody>
            {data.map((u) => (
              <tr key={u.id}>
                <td>{u.name}</td>
                <td>{u.email}</td>
                <td>
                  <select
                    aria-label={`Role for ${u.name}`}
                    value={u.role}
                    disabled={u.id === me?.user.id}
                    onChange={(e) => role(u.id, e.target.value)}
                  >
                    <option>analyst</option>
                    <option>reviewer</option>
                    <option>admin</option>
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function AccountSecurity() {
  const [message, setMessage] = useState(""),
    [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const raw = Object.fromEntries(new FormData(e.currentTarget));
    try {
      await api("/auth/password", {
        method: "POST",
        body: JSON.stringify(raw),
      });
      sessionStorage.removeItem("traceback-session");
      window.location.assign("/");
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel" style={{ padding: 22 }}>
      <h2>
        <ShieldCheck size={18} />
        Account security
      </h2>
      <p className="muted">
        Sessions use HttpOnly cookies. Changing your password signs out all
        existing sessions for this account.
      </p>
      <form onSubmit={submit}>
        <div className="form-grid">
          <label>
            Current password
            <input
              name="current_password"
              type="password"
              autoComplete="current-password"
              required
            />
          </label>
          <label>
            New password
            <input
              name="new_password"
              type="password"
              autoComplete="new-password"
              minLength={12}
              maxLength={128}
              required
            />
          </label>
        </div>
        {message && (
          <div className="error" role="alert">
            {message}
          </div>
        )}
        <Button type="submit" disabled={busy}>
          Change password and sign out
        </Button>
      </form>
    </section>
  );
}
