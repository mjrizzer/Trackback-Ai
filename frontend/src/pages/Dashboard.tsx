import { useQuery } from "@tanstack/react-query";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bot,
  Box,
  ChevronRight,
  CircleDot,
  Plus,
  ShieldCheck,
  Truck,
} from "lucide-react";
import { Link } from "react-router-dom";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, Row } from "../api";

import {
  Badge,
  ErrorBox,
  Loading,
  PageTitle,
  useRecords,
} from "../components/common";
export function Dashboard() {
  const { data: d, error } = useQuery<Row>({
    queryKey: ["dashboard"],
    queryFn: () => api("/dashboard"),
    refetchInterval: 4000,
  });
  const { data: incidents = [] } = useRecords("incidents"),
    { data: investigations = [] } = useRecords("investigations");
  if (!d) return error ? <ErrorBox error={error} /> : <Loading />;
  const metrics = [
    ["Production batches", d.batches, Box, "Validated production records"],
    [
      "Open incidents",
      d.open_incidents,
      AlertTriangle,
      `${d.flagged_lots} material lots flagged`,
    ],
    [
      "Affected shipments",
      d.affected_shipments,
      Truck,
      "Potential exposure · verified links",
    ],
    [
      "Pending approvals",
      d.pending_approvals,
      ShieldCheck,
      "Human review required",
    ],
  ] as const;
  return (
    <>
      <PageTitle
        title="Operations overview"
        subtitle="A clear view of incidents, investigations, and supply chain exposure."
      >
        <Link to="/incidents?new=1" className="btn primary">
          <Plus size={16} /> Report incident
        </Link>
      </PageTitle>
      <div className="status-strip">
        <span className="live-dot" />
        <strong>Investigation workspace online</strong>
        <span>{d.active_investigations} active investigations</span>
        <div className="strip-end">
          <ShieldCheck size={14} /> Human oversight enabled
        </div>
      </div>
      <div className="metrics">
        {metrics.map(([label, value, Icon, note]) => (
          <div className="metric" key={label}>
            <div className="metric-top">
              <span>{label}</span>
              <Icon size={18} />
            </div>
            <strong>{value}</strong>
            <small>{note}</small>
          </div>
        ))}
      </div>
      <div className="dashboard-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Incident activity</h2>
              <p>Reported incidents by date · database records</p>
            </div>
            <Badge>Recorded history</Badge>
          </div>
          <div className="chart">
            <ResponsiveContainer width="100%" height={240}>
              <AreaChart data={d.trends}>
                <defs>
                  <linearGradient id="blue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#367ff0" stopOpacity={0.25} />
                    <stop offset="100%" stopColor="#367ff0" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 4" vertical={false} />
                <XAxis
                  dataKey="date"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v) => v.slice(5)}
                />
                <YAxis allowDecimals={false} width={30} />
                <Tooltip />
                <Area
                  type="monotone"
                  dataKey="incidents"
                  stroke="#367ff0"
                  strokeWidth={2.5}
                  fill="url(#blue)"
                  dot={{ r: 4 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </section>
        <section className="panel investigation-card">
          <div className="panel-heading">
            <h2>Investigation pipeline</h2>
            <Bot size={19} />
          </div>
          <div className="pipeline-number">
            {investigations.length}
            <span>total investigations</span>
          </div>
          {["queued", "running", "awaiting_review", "failed"].map((status) => (
            <div className="pipeline-row" key={status}>
              <span>
                <CircleDot size={13} />
                {status.replaceAll("_", " ")}
              </span>
              <strong>
                {investigations.filter((i) => i.status === status).length}
              </strong>
            </div>
          ))}
          <Link to="/investigations" className="text-link">
            Open investigation center <ArrowRight size={15} />
          </Link>
        </section>
      </div>
      <div className="dashboard-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Priority incidents</h2>
              <p>Investigate issues before their impact spreads</p>
            </div>
            <Link className="text-link" to="/incidents">
              View all <ChevronRight size={15} />
            </Link>
          </div>
          {incidents.slice(0, 4).map((i) => (
            <Link key={i.id} to={`/incidents/${i.id}`} className="incident-row">
              <div className={`incident-symbol ${i.severity}`}>
                <AlertTriangle size={18} />
              </div>
              <div className="grow">
                <small>
                  INC-{String(i.id).padStart(4, "0")} · {i.category}
                </small>
                <strong>{i.title}</strong>
                <span>{new Date(i.created_at).toLocaleDateString()}</span>
              </div>
              <Badge>{i.severity}</Badge>
              <ChevronRight size={16} />
            </Link>
          ))}
          {!incidents.length && (
            <div className="empty">
              No incidents reported. Your workspace is ready.
            </div>
          )}
        </section>
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Latest agent activity</h2>
              <p>Persisted investigation events</p>
            </div>
            <Activity size={18} />
          </div>
          <div className="activity-list">
            {d.activity.map((a: Row) => (
              <div className="activity-item" key={a.id}>
                <div className="activity-dot" />
                <div>
                  <p>{a.message}</p>
                  <small>{new Date(a.created_at).toLocaleString()}</small>
                </div>
              </div>
            ))}
            {!d.activity.length && (
              <div className="empty">
                <Bot size={30} />
                <p>Start an incident investigation to see the agents work.</p>
                <Link to="/incidents" className="text-link">
                  Choose an incident <ArrowRight size={15} />
                </Link>
              </div>
            )}
          </div>
        </section>
      </div>
      <div className="assurance">
        <ShieldCheck size={17} />
        <span>
          Evidence-backed findings. Deterministic traceability. Every sensitive
          action reviewed by a human.
        </span>
      </div>
    </>
  );
}
