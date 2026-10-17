// @vitest-environment jsdom
import { afterEach, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import PreviewDetails from "./PreviewDetails";
afterEach(cleanup);
it("RF-18 muestra horas por intervención y del período por tipo", () => {
  render(
    <PreviewDetails
      preview={{
        quote_id: "q",
        is_emission_valid: true,
        pending_emission_issues: [],
        calendar_summary: { group_interventions: { g: 3 } },
        pricing_summary: null,
        group_efforts: {
          g: {
            physical_sqm: 100,
            general: {
              surface_sqm: 100,
              total_hours_per_intervention: 2,
              assigned_workers: 2,
              duration_hours: 1,
              suggested_workers: 1,
              estimated_base_hours: 2,
            },
            specialized: {
              surface_sqm: 20,
              total_hours_per_intervention: 1,
              assigned_workers: 1,
              duration_hours: 1,
            },
          },
        },
      }}
    />,
  );
  expect(
    screen.getByText(/2 h por intervención · 6 h en el período/),
  ).toBeTruthy();
  expect(
    screen.getByText(/1 h por intervención · 3 h en el período/),
  ).toBeTruthy();
  expect(screen.getByText(/2 personas.*Base estimada: 2 h.*Sugerencia para todas las visitas del día: 1 personas/)).toBeTruthy();
});
