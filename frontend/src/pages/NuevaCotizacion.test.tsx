// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api/client";
import {
  nuevoBorrador,
  nuevoGrupo,
  type Propuesta,
  type VistaPrevia,
} from "../types/borrador";
import NuevaCotizacion from "./NuevaCotizacion";

const draft = { ...nuevoBorrador(), id: "q1" };
const invalid: VistaPrevia = {
  quote_id: "q1",
  is_emission_valid: false,
  pending_emission_issues: ["Falta dirección del servicio"],
  calendar_summary: null,
  group_efforts: {},
  pricing_summary: null,
};
const valid: VistaPrevia = {
  ...invalid,
  is_emission_valid: true,
  pending_emission_issues: [],
};

function openPage() {
  render(
    <MemoryRouter initialEntries={["/borradores/q1"]}>
      <Routes>
        <Route path="/borradores/:id" element={<NuevaCotizacion />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  localStorage.clear();
  vi.spyOn(api, "profiles").mockResolvedValue([]);
  vi.spyOn(api, "searchClients").mockResolvedValue([]);
  vi.spyOn(api, "getDraft").mockResolvedValue(draft);
  vi.spyOn(api, "currentProposal").mockResolvedValue(null);
  vi.spyOn(api, "history").mockResolvedValue([]);
  vi.spyOn(api, "saveDraft").mockImplementation(async (value) => value);
  vi.spyOn(api, "preview").mockResolvedValue(invalid);
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

describe("flujo manual D11", () => {
  it("bloquea emisión con pendientes y permite descargar tras una vista previa válida", async () => {
    const preview = vi.mocked(api.preview);
    const issue = vi.spyOn(api, "issue").mockResolvedValue({
      quote_id: "q1",
      code: "COT-1",
      issued_at: "2026-10-17",
      total_usd: "100.00",
      pdf_url: "/pdf",
    });
    openPage();
    await screen.findByText("Editar cotización");
    fireEvent.click(
      screen.getByRole("button", { name: "Guardar y actualizar vista previa" }),
    );
    expect(
      await screen.findByText("Falta dirección del servicio"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generar PDF" })).toBeDisabled();
    preview.mockResolvedValue(valid);
    fireEvent.click(
      screen.getByRole("button", { name: "Guardar y actualizar vista previa" }),
    );
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Generar PDF" })).toBeEnabled(),
    );
    fireEvent.click(screen.getByRole("button", { name: "Generar PDF" }));
    await waitFor(() => expect(issue).toHaveBeenCalledWith("q1"));
    expect(
      await screen.findByRole("link", { name: "Descargar PDF" }),
    ).toHaveAttribute("href", "/api/cotizaciones/q1/versiones/COT-1/pdf");
  });

  it("separa la cantidad sin duplicarla y distingue el cobro compartido", async () => {
    const group = { ...nuevoGrupo(), name: "Oficinas", units_count: "5" };
    vi.mocked(api.getDraft).mockResolvedValueOnce({
      ...draft,
      groups: [group],
    });
    openPage();
    await screen.findByText("Grupo: Oficinas");
    fireEvent.click(screen.getByRole("button", { name: "Separar cantidad" }));
    const quantities = screen.getAllByLabelText(
      "Cantidad de espacios",
    ) as HTMLInputElement[];
    expect(quantities.map((input) => input.value).sort()).toEqual(["2", "3"]);
    fireEvent.click(screen.getByRole("button", { name: "Añadir recurso" }));
    expect(
      screen.getByRole("option", { name: "Compartido: por jornada" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Del grupo: por intervención" }),
    ).toBeInTheDocument();
  });
});

describe("flujo asistido D12", () => {
  it("recupera revisión y texto del servidor, y exige confirmar cada envío", async () => {
    const saved: Propuesta = {
      id: 9,
      analysis: {
        status: "SUCCESS",
        message: "Revisión recuperada",
        fallback_to_manual: false,
      },
      review: {
        original_text: "Dos aulas de 40 m²",
        revisable_groups: [
          {
            id: "g",
            name: "Aulas recuperadas",
            can_be_confirmed: true,
            warnings: [],
            attributes: {
              quantity: {
                value: 2,
                condition: "human_corrected",
                source_fragment: "Dos aulas",
              },
            },
          },
        ],
        defective_groups: [],
        confirmed_groups: [],
        discarded_groups: [],
      },
    };
    localStorage.clear();
    vi.mocked(api.currentProposal).mockResolvedValue(saved);
    const analyze = vi.spyOn(api, "analyze").mockResolvedValue(saved);
    openPage();
    await screen.findByText("Aulas recuperadas");
    expect(screen.getByLabelText("Texto exacto")).toHaveValue(
      saved.review.original_text,
    );
    expect(
      screen.getByRole("button", { name: "Analizar descripción" }),
    ).toBeDisabled();
    fireEvent.click(screen.getByLabelText(/Confirmo este texto/));
    fireEvent.click(
      screen.getByRole("button", { name: "Analizar descripción" }),
    );
    await waitFor(() => expect(analyze).toHaveBeenCalledTimes(1));
    expect(screen.getByLabelText(/Confirmo este texto/)).not.toBeChecked();
    fireEvent.click(
      screen.getByRole("button", { name: "Analizar descripción" }),
    );
    expect(analyze).toHaveBeenCalledTimes(1);
    await waitFor(() =>
      expect(screen.getByLabelText(/Confirmo este texto/)).toBeEnabled(),
    );
    fireEvent.click(screen.getByLabelText(/Confirmo este texto/));
    fireEvent.click(
      screen.getByRole("button", { name: "Analizar descripción" }),
    );
    await waitFor(() => expect(analyze).toHaveBeenCalledTimes(2));
  });

  it("mantiene texto y formulario manual si Gemini falla", async () => {
    vi.spyOn(api, "analyze").mockRejectedValue(new Error("tiempo de espera"));
    openPage();
    await screen.findByText("Editar cotización");
    fireEvent.change(screen.getByLabelText("Texto exacto"), {
      target: { value: "Dos oficinas de 20 m²" },
    });
    fireEvent.click(screen.getByLabelText(/Confirmo este texto/));
    fireEvent.click(
      screen.getByRole("button", { name: "Analizar descripción" }),
    );
    expect(
      await screen.findByText(/Puede continuar manualmente/),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Texto exacto")).toHaveValue(
      "Dos oficinas de 20 m²",
    );
    expect(localStorage.getItem("mvp-web-text-q1")).toBe(
      "Dos oficinas de 20 m²",
    );
    fireEvent.click(screen.getByRole("button", { name: "Añadir grupo" }));
    expect(screen.getByLabelText("m² por unidad")).toBeInTheDocument();
  });

  it("separa propuestas defectuosas y conserva contradicciones en revisión", async () => {
    const partial: Propuesta = {
      id: 3,
      analysis: {
        status: "PARTIAL_SUCCESS",
        message: "Una propuesta revisable",
        fallback_to_manual: false,
      },
      review: {
        original_text: "Oficinas",
        revisable_groups: [
          {
            id: "g1",
            name: "Oficinas",
            can_be_confirmed: false,
            warnings: ["Resolver superficie"],
            attributes: {
              unit_area_m2: {
                value: null,
                condition: "contradictory",
                source_fragment: "20 o 30 m²",
                conflicting_values: [20, 30],
              },
            },
          },
        ],
        defective_groups: [{ defect_reasons: ["Sin nombre"], raw_data: {} }],
        confirmed_groups: [],
        discarded_groups: [],
      },
    };
    vi.spyOn(api, "analyze").mockResolvedValue(partial);
    openPage();
    await screen.findByText("Editar cotización");
    fireEvent.change(screen.getByLabelText("Texto exacto"), {
      target: { value: "Oficinas de 20 o 30 m²" },
    });
    fireEvent.click(screen.getByLabelText(/Confirmo este texto/));
    fireEvent.click(
      screen.getByRole("button", { name: "Analizar descripción" }),
    );
    expect(
      await screen.findByText(/Grupo defectuoso: Sin nombre/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Conflicto: \[20,30\]/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Confirmar grupo" }),
    ).toBeDisabled();
  });

  it("envía corrección humana y confirmación antes de incorporar un grupo", async () => {
    const group = {
      id: "p1",
      name: "Oficinas",
      can_be_confirmed: true,
      warnings: [],
      attributes: {
        unit_area_m2: {
          value: 20,
          condition: "explicit" as const,
          source_fragment: "20 m²",
        },
      },
    };
    const result: Propuesta = {
      id: 4,
      analysis: {
        status: "SUCCESS",
        message: "Revise la propuesta",
        fallback_to_manual: false,
      },
      review: {
        original_text: "Oficinas de 20 m²",
        revisable_groups: [group],
        defective_groups: [],
        confirmed_groups: [],
        discarded_groups: [],
      },
    };
    vi.spyOn(api, "analyze").mockResolvedValue(result);
    const review = vi
      .spyOn(api, "review")
      .mockResolvedValue({ review: result.review, draft });
    vi.spyOn(window, "prompt").mockReturnValue("25");
    openPage();
    await screen.findByText("Editar cotización");
    fireEvent.change(screen.getByLabelText("Texto exacto"), {
      target: { value: "Oficinas de 20 m²" },
    });
    fireEvent.click(screen.getByLabelText(/Confirmo este texto/));
    fireEvent.click(
      screen.getByRole("button", { name: "Analizar descripción" }),
    );
    await screen.findByText(/SUCCESS: Revise la propuesta/);
    expect(screen.queryByText("Grupo: Oficinas")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Corregir" }));
    await waitFor(() =>
      expect(review).toHaveBeenCalledWith("q1", 4, "corregir", {
        group_id: "p1",
        attribute_name: "unit_area_m2",
        new_value: 25,
      }),
    );
    fireEvent.click(screen.getByRole("button", { name: "Confirmar grupo" }));
    await waitFor(() =>
      expect(review).toHaveBeenCalledWith("q1", 4, "confirmar", {
        group_id: "p1",
      }),
    );
  });

  it("rechaza más de 50 000 puntos de código sin llamar a Gemini", async () => {
    const analyze = vi.spyOn(api, "analyze");
    openPage();
    await screen.findByText("Editar cotización");
    fireEvent.change(screen.getByLabelText("Texto exacto"), {
      target: { value: "😀".repeat(50001) },
    });
    fireEvent.click(screen.getByLabelText(/Confirmo este texto/));
    fireEvent.click(
      screen.getByRole("button", { name: "Analizar descripción" }),
    );
    expect(await screen.findByText(/supera 50 000 puntos/)).toBeInTheDocument();
    expect(analyze).not.toHaveBeenCalled();
  });
});
