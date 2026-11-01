import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Play, ShieldCheck, X } from "lucide-react";
import React, { useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, Row } from "../api";
import { TraceGraph } from "../components/TraceGraph";
import { Button } from "../components/ui/button";

import {
  Badge,
  ErrorBox,
  Loading,
  PageTitle,
  useRecords,
} from "../components/common";
import { Documents } from "./Evidence";
export function IncidentForm({ close }: { close: () => void }) {
  const { data: lots = [] } = useRecords("lots"),
    { data: batches = [] } = useRecords("batches");
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const query = useQueryClient(),
    navigate = useNavigate();
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const raw = Object.fromEntries(new FormData(e.currentTarget));
    try {
      const incident = await api("/incidents", {
        method: "POST",
        body: JSON.stringify({
          ...raw,
          lot_id: raw.lot_id ? Number(raw.lot_id) : null,
          batch_id: raw.batch_id ? Number(raw.batch_id) : null,
        }),
      });
      query.invalidateQueries();
      close();
      navigate(`/incidents/${incident.id}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="modal-backdrop">
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="incident-title"
      >
        <div className="panel-heading">
          <h2 id="incident-title">Report an incident</h2>
          <Button variant="ghost" onClick={close} aria-label="Close">
            <X size={18} />
          </Button>
        </div>
        <form onSubmit={submit}>
          <label>
            Incident title
            <input
              name="title"
              minLength={5}
              maxLength={200}
              required
              placeholder="Describe the issue briefly"
            />
          </label>
          <div className="form-grid">
            <label>
              Category
              <select name="category">
                {[
                  "contamination",
                  "quality",
                  "shipment",
                  "records",
                  "other",
                ].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
            <label>
              Severity
              <select name="severity">
                {["medium", "low", "high", "critical"].map((x) => (
                  <option key={x}>{x}</option>
                ))}
              </select>
            </label>
          </div>
          <label>
            Description
            <textarea
              name="description"
              minLength={10}
              maxLength={8000}
              required
              rows={4}
              placeholder="What happened? Include relevant records, dates and observations."
            />
          </label>
          <div className="form-grid">
            <label>
              Material lot
              <select name="lot_id">
                <option value="">No lot selected</option>
                {lots.map((l) => (
                  <option key={l.id} value={l.id}>
                    {l.code} · {l.material}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Production batch
              <select name="batch_id">
                <option value="">No batch selected</option>
                {batches.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.code}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <ErrorBox error={error} />
          <Button type="submit" disabled={busy}>
            {busy ? "Creating…" : "Create incident"}
            <ArrowRight size={15} />
          </Button>
        </form>
      </div>
    </div>
  );
}

export function IncidentDetail() {
  const { id } = useParams(),
    { data: incidents = [] } = useRecords("incidents"),
    { data: investigations = [] } = useRecords("investigations");
  const incident = incidents.find((i) => i.id === Number(id));
  const { data: directIncident, error: incidentError } = useQuery<Row>({
    queryKey: ["incident", id],
    queryFn: () => api(`/incidents/${id}`),
  });
  const { data: trace } = useQuery({
    queryKey: ["trace", id],
    queryFn: () => api(`/incidents/${id}/trace`),
  });
  const [error, setError] = useState(""),
    [busy, setBusy] = useState(false),
    navigate = useNavigate(),
    query = useQueryClient();
  async function start() {
    setBusy(true);
    try {
      const inv = await api(`/incidents/${id}/investigate`, { method: "POST" });
      query.invalidateQueries();
      navigate(`/investigations/${inv.id}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (incidentError)
    return (
      <>
        <ErrorBox error={incidentError} />
        <Link to="/incidents" className="text-link">
          Return to incidents
        </Link>
      </>
    );
  if (!incident && !directIncident) return <Loading />;
  const activeIncident = incident || directIncident!;
  const inv = investigations.find((i) => i.incident_id === activeIncident.id);
  return (
    <>
      <PageTitle
        title={activeIncident.title}
        eyebrow={`INC-${String(id).padStart(4, "0")} · ${activeIncident.category}`}
        subtitle={activeIncident.description}
      >
        <Badge>{activeIncident.severity}</Badge>
        <Button onClick={start} disabled={busy}>
          <Play size={15} />
          {inv
            ? "Open investigation"
            : busy
              ? "Starting…"
              : "Start investigation"}
        </Button>
      </PageTitle>
      <ErrorBox error={error} />
      <div className="notice">
        <ShieldCheck size={18} />
        Investigations read verified records and draft proposed actions. Human
        approval is required for simulated inventory changes.
      </div>
      {trace && <TraceGraph trace={trace} />}
      <Documents incidentId={Number(id)} embedded />
    </>
  );
}
