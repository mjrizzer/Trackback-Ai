import { useQueryClient } from "@tanstack/react-query";
import { Download, FileText, Search, Upload, X } from "lucide-react";
import React, { useState } from "react";
import { api, download, Row } from "../api";
import { Button } from "../components/ui/button";

import { ErrorBox, PageTitle, useRecords } from "../components/common";
export function Documents({
  incidentId,
  embedded = false,
}: {
  incidentId?: number;
  embedded?: boolean;
}) {
  const { data = [], error } = useRecords("documents");
  const [message, setMessage] = useState(""),
    [uploading, setUploading] = useState(false),
    [selected, setSelected] = useState<Row | null>(null),
    [search, setSearch] = useState("");
  const query = useQueryClient();
  async function upload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    if (incidentId) form.append("incident_id", String(incidentId));
    try {
      const response = await api("/documents", { method: "POST", body: form });
      setMessage(
        response.issues.length
          ? response.issues.join("; ")
          : "Document uploaded and text extracted. Stored as untrusted evidence.",
      );
      query.invalidateQueries({ queryKey: ["documents"] });
    } catch (e) {
      setMessage((e as Error).message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }
  const docs = data.filter(
    (d) =>
      (!incidentId || d.incident_id === incidentId) &&
      d.name.toLowerCase().includes(search.toLowerCase()),
  );
  return (
    <>
      {!embedded && (
        <PageTitle
          title="Evidence & documents"
          subtitle="Original source files, extracted text, and a verifiable chain of evidence."
        />
      )}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>
              <FileText size={18} />{" "}
              {embedded ? "Incident evidence" : "Document library"}
            </h2>
            <p>PDF and UTF-8 CSV · maximum 10 MB · no instructions executed</p>
          </div>
          <label className="btn primary upload-button">
            <Upload size={15} />
            {uploading ? "Extracting…" : "Upload evidence"}
            <input
              type="file"
              accept=".pdf,.csv"
              disabled={uploading}
              onChange={upload}
            />
          </label>
        </div>
        <ErrorBox error={error} />
        {message && (
          <div className="notice" role="status">
            {message}
          </div>
        )}
        <div className="table-toolbar">
          <div className="search-box">
            <Search size={15} />
            <input
              aria-label="Search documents"
              placeholder="Search source documents…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
          <span>{docs.length} files</span>
        </div>
        <div className="document-grid">
          {docs.map((d) => (
            <button
              className="document-card"
              key={d.id}
              onClick={async () => {
                try {
                  setSelected(await api(`/documents/${d.id}`));
                } catch (e) {
                  setMessage((e as Error).message);
                }
              }}
            >
              <div className="file-icon">
                <FileText size={22} />
              </div>
              <strong>{d.name}</strong>
              <small>evidence_documents:{d.id}</small>
              <span>
                {d.media_type === "application/pdf" ? "PDF" : "CSV"} ·{" "}
                {d.sha256.slice(0, 12)}…
              </span>
            </button>
          ))}
        </div>
        {!docs.length && (
          <div className="empty">
            Upload an original record to add evidence.
          </div>
        )}
      </section>
      {selected && (
        <div className="modal-backdrop">
          <div className="modal wide" role="dialog" aria-modal="true">
            <div className="panel-heading">
              <h2>{selected.name}</h2>
              <Button
                variant="ghost"
                onClick={() => setSelected(null)}
                aria-label="Close"
              >
                <X size={18} />
              </Button>
            </div>
            <p className="references">SHA-256: {selected.sha256}</p>
            <div className="notice">
              Untrusted source content · evidence only
            </div>
            <pre>{selected.text}</pre>
            <Button
              onClick={() =>
                download(
                  `/documents/${selected.id}/download`,
                  selected.name,
                ).catch((e) => setMessage(e.message))
              }
            >
              <Download size={15} /> Original file
            </Button>
          </div>
        </div>
      )}
    </>
  );
}
