// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, serializeDraft } from "./client";
import { nuevoBorrador, nuevoGrupo } from "../types/borrador";

beforeEach(() => {
  localStorage.clear();
  vi.restoreAllMocks();
});

describe("contrato integrado RF-01–RF-05, RF-12–RF-13, RF-20, RF-22", () => {
  it("envía dirección del servicio y magnitudes con unidades correctas", () => {
    const draft = nuevoBorrador();
    draft.client.service_address = "Quito";
    draft.service.period_type = "mensual";
    const group = nuevoGrupo();
    group.units_count = "3";
    group.sqm_per_unit = "45.5";
    group.visits_per_day = "2";
    group.specialized_work = {
      ...group.specialized_work,
      enabled: true,
      custom_surface_sqm: "20",
    };
    draft.groups = [group];
    const sent = serializeDraft(draft) as Record<string, any>;
    expect(sent.client.service_address).toBe("Quito");
    expect(sent.service.period_type).toBe("mensual");
    expect(sent.groups[0].units_count).toBe(3);
    expect(sent.groups[0].sqm_per_unit).toBe("45.5");
    expect(sent.groups[0].visits_per_day).toBe(2);
    expect(sent.groups[0].specialized_work.custom_surface_sqm).toBe("20");
    group.units_count = "dato inválido";
    expect(
      (serializeDraft(draft) as Record<string, any>).groups[0].units_count,
    ).toBe("dato inválido");
  });

  it("crea y recupera un borrador incompleto sin obligar a emitir", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: "q1", ...nuevoBorrador() }),
      })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: "q1", ...nuevoBorrador() }),
      });
    vi.stubGlobal("fetch", fetcher);
    await api.saveDraft(nuevoBorrador());
    expect(api.localDraftIds()).toEqual(["q1"]);
    await api.getDraft("q1");
    expect(fetcher.mock.calls[0][0]).toBe("/api/cotizaciones/");
    expect(fetcher.mock.calls[1][0]).toBe("/api/cotizaciones/q1");
    vi.unstubAllGlobals();
  });
});
