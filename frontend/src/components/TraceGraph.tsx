import { Download, Network } from "lucide-react";
import { useState } from "react";
import { Row, exportJson } from "../api";
import { Button } from "./ui/button";
export function TraceGraph({ trace }: { trace: Row }) {
  const [selected, setSelected] = useState<string>("");
  const [downstream, setDownstream] = useState(false);
  const kinds = ["supplier", "lot", "batch", "shipment", "customer"];
  const nodes: Row[] = trace.nodes || [],
    edges: Row[] = trace.edges || [];
  const linked = new Set([
    selected,
    ...edges
      .filter((e) => e.source === selected || e.target === selected)
      .flatMap((e) => [e.source, e.target]),
  ]);
  if (downstream && selected) {
    linked.clear();
    linked.add(selected);
    let changed = true;
    while (changed) {
      changed = false;
      for (const edge of edges)
        if (linked.has(edge.source) && !linked.has(edge.target)) {
          linked.add(edge.target);
          changed = true;
        }
    }
  }
  const positions = new Map(
    nodes.map((n) => [
      n.id,
      {
        x: 100 + kinds.indexOf(n.kind) * 210,
        y:
          65 +
          nodes
            .filter((a) => a.kind === n.kind)
            .findIndex((a) => a.id === n.id) *
            66,
      },
    ]),
  );
  const height = Math.max(
    230,
    ...kinds.map((k) => nodes.filter((n) => n.kind === k).length * 66 + 60),
  );
  const node = nodes.find((n) => n.id === selected);
  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h2>
            <Network size={18} /> Verified supply chain
          </h2>
          <p>SQL relationships · select a node to inspect its source record</p>
        </div>
        <Button
          variant="outline"
          onClick={() => exportJson(trace, "traceability.json")}
        >
          <Download size={15} /> Export
        </Button>
      </div>
      {!nodes.length ? (
        <div className="empty">
          No linked records. Add a material lot or batch to the incident.
        </div>
      ) : (
        <>
          <div className="graph-scroll">
            <svg
              role="img"
              aria-label="Supply chain traceability graph"
              width="1050"
              height={height}
            >
              <defs>
                <marker
                  id="arrow"
                  markerWidth="6"
                  markerHeight="6"
                  refX="5"
                  refY="3"
                  orient="auto"
                >
                  <path d="M0,0 L6,3 L0,6" fill="#7595b5" />
                </marker>
              </defs>
              {kinds.map((k, i) => (
                <text
                  key={k}
                  x={100 + i * 210}
                  y="20"
                  textAnchor="middle"
                  className="graph-label"
                >
                  {k.toUpperCase()}
                </text>
              ))}
              {edges.map((e, i) => {
                const a = positions.get(e.source),
                  b = positions.get(e.target);
                if (!a || !b) return null;
                return (
                  <path
                    key={i}
                    d={`M${a.x + 73},${a.y} C${a.x + 110},${a.y} ${b.x - 110},${b.y} ${b.x - 76},${b.y}`}
                    fill="none"
                    stroke={
                      selected &&
                      (e.source === selected || e.target === selected)
                        ? "#2878ef"
                        : "#c0cfdf"
                    }
                    strokeWidth="1.5"
                    markerEnd="url(#arrow)"
                  >
                    <title>{e.reference}</title>
                  </path>
                );
              })}
              {nodes.map((n) => {
                const p = positions.get(n.id)!;
                return (
                  <g
                    key={n.id}
                    role="button"
                    tabIndex={0}
                    aria-label={n.label}
                    onClick={() => setSelected(n.id)}
                    onKeyDown={(e) => e.key === "Enter" && setSelected(n.id)}
                    className={`graph-node ${selected && !linked.has(n.id) ? "dim" : ""}`}
                  >
                    <rect
                      x={p.x - 74}
                      y={p.y - 19}
                      width="148"
                      height="38"
                      rx="8"
                      fill={selected === n.id ? "#dceafe" : "var(--surface)"}
                      stroke={selected === n.id ? "#2878ef" : "#9bb0c6"}
                    />
                    <text x={p.x} y={p.y + 4} textAnchor="middle">
                      {n.label.length > 21
                        ? n.label.slice(0, 19) + "…"
                        : n.label}
                    </text>
                  </g>
                );
              })}
            </svg>
          </div>
          {node && (
            <div className="node-details">
              <h3>
                {node.label} <small>{node.id}</small>
              </h3>
              <Button
                variant="outline"
                onClick={() => setDownstream(!downstream)}
              >
                {downstream
                  ? "Show adjacent records"
                  : "Highlight downstream impact"}
              </Button>
              <div className="detail-grid">
                {Object.entries(node.record).map(([key, value]) => (
                  <div key={key}>
                    <span>{key.replaceAll("_", " ")}</span>
                    <strong>{String(value ?? "—")}</strong>
                  </div>
                ))}
              </div>
              <p>
                Supporting references:{" "}
                {edges
                  .filter((e) => e.source === node.id || e.target === node.id)
                  .map((e) => e.reference)
                  .join(", ")}
              </p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
