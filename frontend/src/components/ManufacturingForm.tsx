import { useQuery, useQueryClient } from "@tanstack/react-query";
import { X } from "lucide-react";
import { useState } from "react";
import { api, Row } from "../api";
import { Button } from "./ui/button";

export function ManufacturingForm({
  kind,
  close,
}: {
  kind: string;
  close: () => void;
}) {
  const query = useQueryClient(),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);
  const sources = ["suppliers", "lots", "batches", "customers", "documents"];
  const { data = {} } = useQuery<Record<string, Row[]>>({
    queryKey: ["entry-options"],
    queryFn: async () =>
      Object.fromEntries(
        await Promise.all(
          sources.map(async (k) => [k, await api(`/records/${k}`)]),
        ),
      ),
  });
  const select = (label: string, name: string, collection: string) => (
    <label>
      {label}
      <select name={name} required>
        <option value="">Select a source record</option>
        {(data[collection] || []).map((r) => (
          <option key={r.id} value={r.id}>
            {r.code || r.name} {r.material || r.product || ""}
          </option>
        ))}
      </select>
    </label>
  );
  const text = (label: string, name: string, number = false) => (
    <label>
      {label}
      <input
        name={name}
        type={number ? "number" : "text"}
        min={number ? "0.001" : undefined}
        step={number ? "any" : undefined}
        required
        maxLength={number ? undefined : 100}
      />
    </label>
  );
  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    const raw = Object.fromEntries(new FormData(e.currentTarget));
    const body: Row = { ...raw };
    for (const key of [
      "supplier_id",
      "customer_id",
      "batch_id",
      "document_id",
      "lot_id",
      "quantity",
      "used_quantity",
    ])
      if (key in body) body[key] = Number(body[key]);
    if (kind === "batches") {
      body.materials = [{ lot_id: body.lot_id, quantity: body.used_quantity }];
      delete body.lot_id;
      delete body.used_quantity;
    }
    if (kind === "shipments") {
      body.items = [{ batch_id: body.batch_id, quantity: body.quantity }];
      delete body.batch_id;
      delete body.quantity;
    }
    try {
      await api(`/${kind}`, { method: "POST", body: JSON.stringify(body) });
      query.invalidateQueries();
      close();
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
        aria-labelledby="record-title"
      >
        <div className="panel-heading">
          <h2 id="record-title">
            Add{" "}
            {kind === "batches"
              ? "production batch"
              : kind === "lots"
                ? "material lot"
                : kind.replace(/s$/, "")}
          </h2>
          <Button variant="ghost" aria-label="Close" onClick={close}>
            <X size={18} />
          </Button>
        </div>
        <form onSubmit={submit}>
          {["suppliers", "customers"].includes(kind) && text("Name", "name")}
          {kind === "customers" && text("Region", "region")}
          {["lots", "batches", "shipments"].includes(kind) && (
            <label>
              Unique record code
              <input
                name="code"
                pattern="[A-Z0-9][A-Z0-9_-]{2,59}"
                required
                placeholder="Uppercase letters, numbers and hyphens"
              />
            </label>
          )}
          {kind === "lots" && (
            <>
              {select("Supplier", "supplier_id", "suppliers")}
              {text("Material", "material")}
              {text("Available quantity (kg)", "quantity", true)}
            </>
          )}
          {kind === "batches" && (
            <>
              {text("Product", "product")}
              {text("Finished units", "quantity", true)}
              {select("Consumed material lot", "lot_id", "lots")}
              {text("Material consumed (kg)", "used_quantity", true)}
              <p className="muted">
                Material is reserved when this batch is created. The API also
                supports multiple material lots per batch.
              </p>
            </>
          )}
          {kind === "shipments" && (
            <>
              {select("Customer", "customer_id", "customers")}
              {select("Released batch", "batch_id", "batches")}
              {text("Units to ship", "quantity", true)}
              <p className="muted">
                Held batches and quantities exceeding remaining units are
                blocked. Shipments are internal simulated records.
              </p>
            </>
          )}
          {kind === "inspections" && (
            <>
              {select("Production batch", "batch_id", "batches")}
              {select("Source document", "document_id", "documents")}
              {text("Test name", "test")}
              <label>
                Result
                <select name="result">
                  <option>pass</option>
                  <option>fail</option>
                </select>
              </label>
              <p className="muted">
                Reviewer permission required. Upload the original certificate
                first. The source must identify the batch and recorded result;
                review its full context.
              </p>
            </>
          )}
          {error && (
            <div role="alert" className="error">
              {error}
            </div>
          )}
          <Button type="submit" disabled={busy}>
            {busy ? "Saving…" : "Save validated record"}
          </Button>
        </form>
      </div>
    </div>
  );
}
