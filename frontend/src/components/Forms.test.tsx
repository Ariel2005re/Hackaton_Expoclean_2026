// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GroupEditor, ServiceForm } from "./Forms";
import { nuevoBorrador, nuevoGrupo } from "../types/borrador";

describe("captura manual RF-03–RF-05, RF-12–RF-13", () => {
  it("permite un horario nocturno dentro del mismo día y advierte si cruza medianoche", () => {
    const service = nuevoBorrador().service;
    const onChange = vi.fn();
    const view = render(
      <ServiceForm
        value={{ ...service, start_time: "20:00", end_time: "23:00" }}
        onChange={onChange}
      />,
    );
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    view.rerender(
      <ServiceForm
        value={{ ...service, start_time: "23:00", end_time: "02:00" }}
        onChange={onChange}
      />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("posterior al inicio");
  });

  it("muestra m² por unidad, visitas por día, estados correctos y superficie especializada condicional", () => {
    const group = nuevoGrupo();
    const onChange = vi.fn();
    const view = render(
      <GroupEditor
        group={group}
        profiles={[]}
        onChange={onChange}
        onRemove={vi.fn()}
        onSplit={vi.fn()}
      />,
    );
    expect(screen.getByLabelText("m² por unidad")).toBeInTheDocument();
    expect(
      screen.getByLabelText("Visitas por día de servicio"),
    ).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "Malo" })).toBeInTheDocument();
    expect(
      screen.queryByText(/Confirme la superficie especializada/),
    ).not.toBeInTheDocument();
    fireEvent.click(screen.getAllByLabelText("Incluir este trabajo")[1]);
    const specialized = { ...group.specialized_work, enabled: true };
    view.rerender(
      <GroupEditor
        group={{ ...group, specialized_work: specialized }}
        profiles={[]}
        onChange={onChange}
        onRemove={vi.fn()}
        onSplit={vi.fn()}
      />,
    );
    expect(
      screen.getByText(/Confirme la superficie especializada/),
    ).toBeInTheDocument();
  });
});
