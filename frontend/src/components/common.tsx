import { useQuery } from "@tanstack/react-query";
import React from "react";
import { api, Row } from "../api";
export function useRecords(kind: string) {
  return useQuery<Row[]>({
    queryKey: [kind],
    queryFn: () => api(`/records/${kind}`),
    refetchInterval: 5000,
  });
}
export function Badge({ children }: { children: React.ReactNode }) {
  const text = String(children || "");
  return (
    <span
      className={`badge ${/critical|fail|conflict|rejected/.test(text) ? "red" : /high|pending|review|missing|held/.test(text) ? "amber" : /pass|approved|completed|released|delivered/.test(text) ? "green" : "blue"}`}
    >
      {text.replaceAll("_", " ")}
    </span>
  );
}
export function ErrorBox({ error }: { error: unknown }) {
  return error ? (
    <div role="alert" className="error">
      {error instanceof Error ? error.message : String(error)}
    </div>
  ) : null;
}
export function Loading() {
  return (
    <div className="loading">
      <span /> Loading records…
    </div>
  );
}
export function PageTitle({
  eyebrow,
  title,
  subtitle,
  children,
}: {
  eyebrow?: string;
  title: string;
  subtitle: string;
  children?: React.ReactNode;
}) {
  const { data: workspace } = useQuery({
    queryKey: ["me"],
    queryFn: () => api("/me"),
  });
  return (
    <div className="page-title">
      <div>
        <div className="eyebrow">
          {(
            eyebrow ||
            `${workspace?.organization || "WORKSPACE"} · OPERATIONS INTELLIGENCE`
          ).toUpperCase()}
        </div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="title-actions">{children}</div>
    </div>
  );
}
