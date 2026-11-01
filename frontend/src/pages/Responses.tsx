import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { api, Row } from "../api";
import { DraftAction, ReviseAction } from "../components/Operations";
import { Button } from "../components/ui/button";

import { Badge, ErrorBox, PageTitle, useRecords } from "../components/common";
export function Proposals({
  investigationId,
  embedded = false,
}: {
  investigationId?: number;
  embedded?: boolean;
}) {
  const { data = [], error } = useRecords("proposals");
  const { data: me } = useQuery({
    queryKey: ["me"],
    queryFn: () => api("/me"),
  });
  const [message, setMessage] = useState(""),
    [comments, setComments] = useState<Record<number, string>>({}),
    [verified, setVerified] = useState<Record<number, boolean>>({}),
    [busy, setBusy] = useState<number | null>(null);
  const query = useQueryClient();
  async function decide(id: number, decision: string) {
    setBusy(id);
    try {
      await api(`/proposals/${id}/decision`, {
        method: "POST",
        body: JSON.stringify({
          decision,
          comment: comments[id] || "",
          verification_confirmed: verified[id] || false,
        }),
      });
      setMessage(
        "Decision recorded in the audit trail. Approved holds affect internal simulated records only.",
      );
      query.invalidateQueries();
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setBusy(null);
    }
  }
  const allowed = ["admin", "reviewer"].includes(me?.user.role);
  return (
    <>
      {!embedded && (
        <PageTitle
          title="Approval center"
          subtitle="Review evidence, challenge assumptions, and authorize simulated actions."
        />
      )}
      <DraftAction investigationId={investigationId} />
      <ErrorBox error={error} />
      {message && (
        <div role="status" className="notice">
          {message}
        </div>
      )}
      {data
        .filter(
          (p) => !investigationId || p.investigation_id === investigationId,
        )
        .map((p) => (
          <section className="panel proposal" key={p.id}>
            <div className="panel-heading">
              <h2>
                <ShieldCheck size={19} />
                {p.kind.replaceAll("_", " ")} · proposal {p.id}
              </h2>
              <Badge>{p.status}</Badge>
            </div>
            <p>{p.justification}</p>
            {p.revision_history?.length > 0 && (
              <details>
                <summary>
                  Revision history ({p.revision_history.length})
                </summary>
                {p.revision_history.map((r: Row, i: number) => (
                  <div key={i}>
                    <p>
                      {r.at} · reviewer {r.user_id}
                    </p>
                    <p>Previous: {r.previous}</p>
                    <p>Revised: {r.revised}</p>
                  </div>
                ))}
              </details>
            )}
            <p>
              <strong>Target batch record IDs:</strong>{" "}
              {p.target_batch_ids.join(", ") || "No validated targets"}
            </p>
            <details>
              <summary>
                {p.evidence.length} supporting source references
              </summary>
              <p className="references">{p.evidence.join(" · ")}</p>
            </details>
            <Link
              className="text-link"
              to={`/investigations/${p.investigation_id}`}
            >
              Review investigation <ArrowRight size={14} />
            </Link>
            {p.status === "pending" && (
              <>
                <label>
                  Reviewer justification
                  <textarea
                    placeholder="Explain the evidence supporting your decision (required)"
                    minLength={3}
                    maxLength={2000}
                    value={comments[p.id] || ""}
                    onChange={(e) =>
                      setComments({ ...comments, [p.id]: e.target.value })
                    }
                  />
                </label>
                {p.kind === "inventory_release" && (
                  <label className="checkbox-label">
                    <input
                      type="checkbox"
                      checked={verified[p.id] || false}
                      onChange={(e) =>
                        setVerified({ ...verified, [p.id]: e.target.checked })
                      }
                    />
                    I have verified the original source evidence and reviewed
                    outstanding gaps before authorizing this release.
                  </label>
                )}
                <div className="proposal-actions">
                  {[
                    ["approved", "Approve simulated action"],
                    ["rejected", "Reject"],
                    ["revision_requested", "Request revision"],
                  ].map(([decision, label]) => (
                    <Button
                      key={decision}
                      variant={decision === "approved" ? "default" : "outline"}
                      disabled={
                        !allowed ||
                        busy === p.id ||
                        (comments[p.id] || "").trim().length < 3 ||
                        (decision === "approved" &&
                          p.kind === "inventory_release" &&
                          !verified[p.id])
                      }
                      onClick={() => decide(p.id, decision)}
                    >
                      {label}
                    </Button>
                  ))}
                </div>
                {!allowed && (
                  <p className="muted">
                    A reviewer or administrator must make this decision.
                  </p>
                )}
              </>
            )}
            {p.status === "revision_requested" && <ReviseAction id={p.id} />}
          </section>
        ))}
      {!data.filter(
        (p) => !investigationId || p.investigation_id === investigationId,
      ).length && (
        <div className="panel empty">
          No action proposals. Complete an investigation to prepare
          evidence-backed recommendations.
        </div>
      )}
    </>
  );
}
