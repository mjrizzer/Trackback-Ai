import {
  ArrowRight,
  ChevronRight,
  FileSearch,
  Plus,
  Search,
  X,
} from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import { Row } from "../api";
import { ManufacturingForm } from "../components/ManufacturingForm";
import { Button } from "../components/ui/button";

import {
  Badge,
  ErrorBox,
  Loading,
  PageTitle,
  useRecords,
} from "../components/common";
import { nav } from "../navigation";
import { IncidentForm } from "./Incidents";
const columns: Record<string, string[]> = {
  suppliers: ["id", "name", "status"],
  lots: ["code", "material", "supplier_id", "quantity", "status"],
  batches: ["code", "product", "quantity", "produced_at", "status"],
  shipments: ["code", "customer_id", "shipped_at", "status"],
  incidents: ["id", "title", "category", "severity", "status"],
  investigations: ["id", "incident_id", "mode", "status", "created_at"],
  agents: ["agent", "investigation_id", "status", "started_at", "finished_at"],
  audit: ["id", "action", "detail", "user_id", "created_at"],
  users: ["name", "email", "role"],
  inspections: ["batch_id", "test", "result", "document_id", "observed_at"],
  customers: ["id", "name", "region"],
};
export function Records({ kind }: { kind: string }) {
  const { data, error } = useRecords(kind);
  const [search, setSearch] = useState(""),
    [showForm, setShowForm] = useState(
      kind === "incidents" && window.location.search.includes("new=1"),
    ),
    [selected, setSelected] = useState<Row | null>(null);
  const [showRecordForm, setShowRecordForm] = useState(false);
  const title = nav.find((n) => n.path === `/${kind}`)?.title || kind;
  if (!data) return error ? <ErrorBox error={error} /> : <Loading />;
  const filtered = data.filter((r) =>
    JSON.stringify(r).toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <>
      <PageTitle
        title={title.charAt(0).toUpperCase() + title.slice(1)}
        subtitle={`${data.length} organization records · searchable, source-backed operational data`}
      >
        {[
          "suppliers",
          "lots",
          "batches",
          "shipments",
          "customers",
          "inspections",
        ].includes(kind) && (
          <Button onClick={() => setShowRecordForm(true)}>
            <Plus size={16} />
            Add record
          </Button>
        )}
        {kind === "incidents" && (
          <Button onClick={() => setShowForm(true)}>
            <Plus size={16} /> Report incident
          </Button>
        )}
      </PageTitle>
      {kind === "investigations" && (
        <div className="notice">
          <FileSearch size={20} />
          Start an investigation from an incident record.
          <Link to="/incidents" className="text-link">
            Select incident <ArrowRight size={15} />
          </Link>
        </div>
      )}
      <section className="panel">
        <div className="table-toolbar">
          <div className="search-box">
            <Search size={16} />
            <input
              aria-label={`Search ${title}`}
              placeholder={`Search ${title.toLowerCase()}…`}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <span>{filtered.length} records</span>
        </div>
        <div className="table-scroll">
          <table>
            <thead>
              <tr>
                {(columns[kind] || ["id", "name", "status"]).map((c) => (
                  <th key={c}>{c.replaceAll("_", " ")}</th>
                ))}
                <th>Details</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row) => (
                <tr key={row.id}>
                  {(columns[kind] || ["id", "name", "status"]).map((c) => (
                    <td key={c}>
                      {[
                        "status",
                        "severity",
                        "mode",
                        "result",
                        "role",
                      ].includes(c) ? (
                        <Badge>{row[c]}</Badge>
                      ) : (
                        String(row[c] ?? "—")
                          .replace("T", " ")
                          .slice(0, c === "detail" ? 150 : 100)
                      )}
                    </td>
                  ))}
                  <td>
                    {["incidents", "investigations"].includes(kind) ? (
                      <Link className="text-link" to={`/${kind}/${row.id}`}>
                        Open <ArrowRight size={14} />
                      </Link>
                    ) : (
                      <Button variant="ghost" onClick={() => setSelected(row)}>
                        Inspect <ChevronRight size={14} />
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {!filtered.length && <div className="empty">No matching records.</div>}
      </section>
      {showForm && <IncidentForm close={() => setShowForm(false)} />}
      {showRecordForm && (
        <ManufacturingForm kind={kind} close={() => setShowRecordForm(false)} />
      )}
      {selected && (
        <div className="modal-backdrop">
          <div className="modal" role="dialog" aria-modal="true">
            <div className="panel-heading">
              <h2>
                Source record · {kind}:{selected.id}
              </h2>
              <Button
                variant="ghost"
                onClick={() => setSelected(null)}
                aria-label="Close"
              >
                <X size={18} />
              </Button>
            </div>
            <div className="detail-grid">
              {Object.entries(selected).map(([k, v]) => (
                <div key={k}>
                  <span>{k.replaceAll("_", " ")}</span>
                  <strong>
                    {typeof v === "object"
                      ? JSON.stringify(v)
                      : String(v ?? "—")}
                  </strong>
                </div>
              ))}
            </div>
            {kind === "agents" && <ToolCalls runId={selected.id} />}
          </div>
        </div>
      )}
    </>
  );
}
function ToolCalls({ runId }: { runId: number }) {
  const { data = [] } = useRecords("tool-calls");
  return (
    <div>
      <h3>Persisted tool calls</h3>
      {data
        .filter((t) => t.run_id === runId)
        .map((t) => (
          <details key={t.id}>
            <summary>{t.tool}</summary>
            <pre>{JSON.stringify(t.result, null, 2)}</pre>
          </details>
        ))}
    </div>
  );
}
