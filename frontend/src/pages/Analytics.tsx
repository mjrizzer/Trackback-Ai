import { AlertTriangle, ArrowRight, Download, FileText } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { download } from "../api";
import { Button } from "../components/ui/button";

import { Badge, ErrorBox, PageTitle, useRecords } from "../components/common";
export function Reports() {
  const { data = [] } = useRecords("investigations");
  const [error, setError] = useState("");
  return (
    <>
      <PageTitle
        title="Investigation reports"
        subtitle="Evidence, reasoning, timeline, and approval history in one downloadable document."
      />
      <ErrorBox error={error} />
      <div className="document-grid">
        {data
          .filter((i) => ["awaiting_review", "completed"].includes(i.status))
          .map((i) => (
            <section className="panel report-card" key={i.id}>
              <FileText size={28} />
              <h2>Investigation {i.id}</h2>
              <p>
                Incident {i.incident_id} · {i.mode.toUpperCase()} mode
              </p>
              <Badge>{i.status}</Badge>
              <Link className="text-link" to={`/investigations/${i.id}`}>
                Open findings <ArrowRight size={14} />
              </Link>
              <Button
                onClick={() =>
                  download(
                    `/investigations/${i.id}/report`,
                    `traceback-${i.id}.pdf`,
                  ).catch((e) => setError(e.message))
                }
              >
                <Download size={15} /> Download PDF
              </Button>
            </section>
          ))}
      </div>
      {!data.length && (
        <div className="panel empty">
          Reports become available when an investigation is ready for review.
        </div>
      )}
    </>
  );
}
export function Analytics() {
  const { data = [] } = useRecords("investigations");
  const { data: findings = [] } = useRecords("findings");
  const chart = data
    .filter((i) => i.result.risk)
    .map((i) => ({
      name: `INV-${i.id}`,
      units: i.result.risk.estimated_exposure_units,
    }));
  return (
    <>
      <PageTitle
        title="Risk & impact analytics"
        subtitle="Trace-based potential exposure, with uncertainty made explicit."
      />
      <div className="notice">
        <AlertTriangle size={20} />
        Shipped unit counts indicate potential exposure. They do not confirm
        contamination or loss. Investigations may overlap; do not sum them as
        unique exposure.
      </div>
      <section className="panel">
        <div className="panel-heading">
          <h2>Potentially exposed units by investigation</h2>
        </div>
        {chart.length ? (
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={chart}>
              <CartesianGrid vertical={false} strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="units" fill="#397eec" radius={[5, 5, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        ) : (
          <div className="empty">
            Complete an investigation to calculate potential exposure.
          </div>
        )}
      </section>
      <section className="panel">
        <div className="panel-heading">
          <h2>Verification priorities</h2>
          <Badge>{findings.length} findings</Badge>
        </div>
        {findings.map((f) => (
          <div className="finding" key={f.id}>
            <Badge>{f.kind}</Badge>
            <div>
              <p>{f.detail}</p>
              <Link
                to={`/investigations/${f.investigation_id}`}
                className="text-link"
              >
                Review sources <ArrowRight size={14} />
              </Link>
            </div>
          </div>
        ))}
      </section>
    </>
  );
}
