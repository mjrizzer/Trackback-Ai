// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { TraceGraph } from "./TraceGraph";
afterEach(cleanup);
describe("source-backed graph", () => {
  it("shows a meaningful empty state", () => {
    render(<TraceGraph trace={{ nodes: [], edges: [] }} />);
    expect(screen.getByText(/No linked records/)).toBeInTheDocument();
  });
  it("opens the selected source record and its edge reference", () => {
    render(
      <TraceGraph
        trace={{
          nodes: [
            {
              id: "lot:1",
              kind: "lot",
              label: "RM-042",
              record: { code: "RM-042", material: "Oat flour" },
            },
            {
              id: "batch:1",
              kind: "batch",
              label: "PB-001",
              record: { code: "PB-001" },
            },
          ],
          edges: [
            {
              source: "lot:1",
              target: "batch:1",
              reference: "batch_material_usage:1",
            },
          ],
        }}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "RM-042" }));
    expect(screen.getByText("Oat flour")).toBeInTheDocument();
    expect(
      screen.getByText(/Supporting references: batch_material_usage:1/),
    ).toBeInTheDocument();
  });
});
