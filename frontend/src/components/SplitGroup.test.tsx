// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import SplitGroup, { partitionGroup } from "./SplitGroup";
import { nuevoGrupo, type Recurso } from "../types/borrador";

afterEach(cleanup);
it("RF-05/RF-12 conserva espacios, superficie especializada y horas ajustadas", () => {
  const group = { ...nuevoGrupo(), units_count: "5", sqm_per_unit: "30" };
  group.specialized_work.custom_surface_sqm = "50";
  group.general_work.adjusted_hours_per_intervention = "7";
  const [left, right] = partitionGroup(group, 2);
  expect([left.units_count, right.units_count]).toEqual(["2", "3"]);
  expect([
    left.specialized_work.custom_surface_sqm,
    right.specialized_work.custom_surface_sqm,
  ]).toEqual(["20", "30"]);
  expect(
    Number(left.general_work.adjusted_hours_per_intervention) +
      Number(right.general_work.adjusted_hours_per_intervention),
  ).toBe(7);
  expect(group.units_count).toBe("5");
});
it("RF-20 exige asignación explícita y cancelar no aplica cambios", () => {
  const group = { ...nuevoGrupo(), units_count: "2" };
  const resource: Recurso = {
    resource_id: "r1",
    group_id: group.group_id,
    description: "Jabón",
    kind: "insumo",
    scope: "grupo",
    quantity: "1",
    unit_cost_usd: "2",
    unit: "litro",
  };
  const apply = vi.fn(),
    cancel = vi.fn();
  render(
    <SplitGroup
      group={group}
      resources={[resource]}
      onApply={apply}
      onCancel={cancel}
    />,
  );
  fireEvent.click(screen.getByText("Aplicar separación"));
  expect(apply).not.toHaveBeenCalled();
  expect(screen.getByRole("alert").textContent).toContain("cantidad positiva");
  fireEvent.change(screen.getByLabelText("Cantidad para grupo 1"), {
    target: { value: "0.4" },
  });
  fireEvent.change(screen.getByLabelText("Cantidad para grupo 2"), {
    target: { value: "0.6" },
  });
  fireEvent.click(screen.getByText("Aplicar separación"));
  const [groups, resources] = apply.mock.calls[0];
  expect(resources.map((r: Recurso) => r.quantity)).toEqual(["0.4", "0.6"]);
  expect(resources.map((r: Recurso) => r.group_id)).toEqual(
    groups.map((g: typeof group) => g.group_id),
  );
  apply.mockClear();
  fireEvent.click(screen.getByText("Cancelar separación"));
  expect(cancel).toHaveBeenCalledOnce();
  expect(apply).not.toHaveBeenCalled();
});
