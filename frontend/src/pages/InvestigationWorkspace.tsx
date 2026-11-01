import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, Bot, Check, Download } from "lucide-react";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, download, Row } from "../api";
import { TraceGraph } from "../components/TraceGraph";
import { Button } from "../components/ui/button";

import { Badge, ErrorBox, Loading, PageTitle } from "../components/common";
import { client } from "../query";
import { Proposals } from "./Responses";
export function InvestigationDetail() {
  const { id } = useParams(),
    [error, setError] = useState("");
  const { data: inv, error: queryError } = useQuery<Row>({
    queryKey: ["investigation", id],
    queryFn: () => api(`/investigations/${id}`),
    refetchInterval: 1500,
  });
  if (!inv) return queryError ? <ErrorBox error={queryError} /> : <Loading />;
  const result = inv.result || {},
    completed = inv.runs.filter((r: Row) => r.status === "completed").length;
  return (
    <>
      <PageTitle
        eyebrow={`INV-${String(id).padStart(4, "0")} · ${inv.mode.toUpperCase()} MODE`}
        title="Investigation workspace"
        subtitle={inv.incident.title}
      >
        <Badge>{inv.status}</Badge>
        <Button
          variant="outline"
          disabled={!result.trace}
          onClick={() =>
            download(
              `/investigations/${id}/report`,
              `traceback-${id}.pdf`,
            ).catch((e) => setError(e.message))
          }
        >
          <Download size={15} /> Download report
        </Button>
      </PageTitle>
      <ErrorBox error={error} />
      {inv.status === "failed" && (
        <div className="notice">
          <span>
            This attempt stopped safely. Previous events are retained.
          </span>
          <Button
            onClick={async () => {
              try {
                await api(`/investigations/${id}/retry`, { method: "POST" });
                client.invalidateQueries();
              } catch (e) {
                setError((e as Error).message);
              }
            }}
          >
            Retry investigation
          </Button>
        </div>
      )}
      <div className="notice">
        <Bot size={20} />
        {inv.mode === "demo"
          ? "Demo Mode · predetermined investigation workflow using real seeded database records. No live AI reasoning."
          : "Live AI Mode · model-selected controlled tools; supply chain links remain SQL-derived."}
      </div>
      <div className="panel progress-panel">
        <div className="panel-heading">
          <h2>Agent coordination</h2>
          <span>{completed} / 5 stages completed</span>
        </div>
        <div className="progress-track">
          <div style={{ width: `${completed * 20}%` }} />
        </div>
        <div className="agent-stages">
          {[
            "Incident Triage",
            "Evidence Intelligence",
            "Supply Chain Traceability",
            "Risk and Impact",
            "Response Planning",
          ].map((name, index) => {
            const run = inv.runs.find((r: Row) => r.agent === name);
            return (
              <div
                key={name}
                className={run?.status === "completed" ? "done" : ""}
              >
                <span>
                  {run?.status === "completed" ? (
                    <Check size={16} />
                  ) : (
                    index + 1
                  )}
                </span>
                <strong>{name}</strong>
                <small>{run?.status || "waiting"}</small>
              </div>
            );
          })}
        </div>
      </div>
      <div className="workspace-grid">
        <section className="panel">
          <div className="panel-heading">
            <h2>Investigation timeline</h2>
            <Badge>Persisted events</Badge>
          </div>
          <div className="activity-list">
            {inv.events.map((ev: Row) => (
              <div className="activity-item" key={ev.id}>
                <div className="activity-dot" />
                <div>
                  <small>{new Date(ev.created_at).toLocaleTimeString()}</small>
                  <p>{ev.message}</p>
                </div>
              </div>
            ))}
          </div>
        </section>
        <div>
          {inv.runs.map((run: Row) => (
            <section className="panel agent-result" key={run.id}>
              <h2>
                <Bot size={17} />
                {run.agent}
                <Badge>{run.status}</Badge>
              </h2>
              <p>
                {run.output.summary ||
                  run.output.error ||
                  "Working on evidence…"}
              </p>
              {run.output.evidence_references && (
                <details>
                  <summary>
                    {run.output.evidence_references.length} source references
                  </summary>
                  <p className="references">
                    {run.output.evidence_references.join(" · ")}
                  </p>
                </details>
              )}
            </section>
          ))}
        </div>
      </div>
      {result.trace && <TraceGraph trace={result.trace} />}
      <section className="panel">
        <div className="panel-heading">
          <h2>Evidence gaps & contradictions</h2>
          <Link to="/documents" className="text-link">
            Inspect source documents <ArrowRight size={14} />
          </Link>
        </div>
        {result.evidence?.findings?.map((f: Row, i: number) => (
          <div className="finding" key={i}>
            <Badge>{f.kind}</Badge>
            <div>
              <p>{f.detail}</p>
              <small>{f.references.join(" · ")}</small>
            </div>
          </div>
        ))}
        {!result.evidence?.findings?.length && (
          <div className="empty">No persisted evidence gaps yet.</div>
        )}
      </section>
      {result.risk && (
        <div className="notice">
          <AlertTriangle size={20} />
          <div>
            <strong>
              {result.risk.priority.toUpperCase()} review priority ·{" "}
              {result.risk.estimated_exposure_units.toLocaleString()}{" "}
              potentially exposed units
            </strong>
            <p>{result.risk.uncertainty}</p>
          </div>
        </div>
      )}
      <Proposals investigationId={Number(id)} embedded />
    </>
  );
}
