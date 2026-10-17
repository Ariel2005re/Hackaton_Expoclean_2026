import type {
  Borrador,
  Cliente,
  HistorialItem,
  Perfil,
  Propuesta,
  Version,
  VistaPrevia,
} from "../types/borrador";

const base = "/api";
const indexKey = "mvp-web-draft-ids";

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${base}${path}`, init);
  if (!response.ok) {
    let detail = response.statusText;
    try {
      detail = JSON.stringify((await response.json()).detail ?? detail);
    } catch {
      /* empty error */
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return null as T;
  return response.json() as Promise<T>;
}

function json(method: string, data: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  };
}

const optional = (value: string): string | null =>
  value.trim() === "" ? null : value;
const integer = (value: string): number | string | null =>
  value.trim() === ""
    ? null
    : Number.isNaN(Number(value))
      ? value
      : Number(value);

export function serializeDraft(draft: Borrador): unknown {
  return {
    ...draft,
    client: { ...draft.client },
    service: {
      ...draft.service,
      period_type: draft.service.period_type || null,
    },
    groups: draft.groups.map((group) => ({
      ...group,
      units_count: integer(group.units_count),
      sqm_per_unit: optional(group.sqm_per_unit),
      visits_per_day: integer(group.visits_per_day),
      state: group.state || null,
      profile_id: group.profile_id || null,
      custom_state_factor: optional(group.custom_state_factor),
      general_work: serializeWork(group.general_work),
      specialized_work: serializeWork(group.specialized_work),
    })),
    resources: draft.resources.map((resource) => ({
      ...resource,
      quantity: optional(resource.quantity),
      unit_cost_usd: optional(resource.unit_cost_usd),
    })),
    margin_percentage: optional(draft.margin_percentage),
    discount_usd: draft.discount_usd || "0",
    tax_percentage: optional(draft.tax_percentage),
  };
}

function serializeWork(work: Borrador["groups"][number]["general_work"]) {
  return {
    ...work,
    assigned_workers: integer(work.assigned_workers),
    productivity_sqm_per_hour: optional(work.productivity_sqm_per_hour),
    hourly_rate_usd: optional(work.hourly_rate_usd),
    adjusted_hours_per_intervention: optional(
      work.adjusted_hours_per_intervention,
    ),
    custom_surface_sqm: optional(work.custom_surface_sqm ?? ""),
  };
}

function normalizeDraft(raw: Borrador): Borrador {
  const str = (value: unknown) => (value == null ? "" : String(value));
  return {
    ...raw,
    client: {
      name: raw.client?.name ?? "",
      service_address: raw.client?.service_address ?? "",
      identification: raw.client?.identification ?? "",
      email: raw.client?.email ?? "",
      phone: raw.client?.phone ?? "",
    },
    service: {
      infrastructure_type: raw.service?.infrastructure_type ?? "",
      cleaning_type: raw.service?.cleaning_type ?? "",
      start_date: raw.service?.start_date ?? "",
      period_type: raw.service?.period_type ?? "",
      start_time: (raw.service?.start_time ?? "").slice(0, 5),
      end_time: (raw.service?.end_time ?? "").slice(0, 5),
    },
    groups: (raw.groups ?? []).map((group) => ({
      ...group,
      name: group.name ?? "",
      units_count: str(group.units_count),
      sqm_per_unit: str(group.sqm_per_unit),
      service_days: group.service_days ?? [],
      visits_per_day: str(group.visits_per_day),
      state: group.state ?? "",
      profile_id: group.profile_id == null ? null : str(group.profile_id),
      custom_state_factor: str(group.custom_state_factor),
      zone: group.zone ?? "",
      tasks_description: group.tasks_description ?? "",
      general_work: normalizeWork(group.general_work),
      specialized_work: normalizeWork(group.specialized_work),
    })),
    resources: (raw.resources ?? []).map((resource) => ({
      ...resource,
      description: resource.description ?? "",
      quantity: str(resource.quantity),
      unit_cost_usd: str(resource.unit_cost_usd),
      unit: resource.unit ?? "",
    })),
    margin_percentage: str(raw.margin_percentage),
    discount_usd: str(raw.discount_usd),
    tax_percentage: str(raw.tax_percentage),
  };
}

function normalizeWork(work: Borrador["groups"][number]["general_work"]) {
  const source = work ?? { enabled: false };
  const str = (value: unknown) => (value == null ? "" : String(value));
  return {
    enabled: source.enabled ?? false,
    assigned_workers: str(source.assigned_workers ?? 1),
    productivity_sqm_per_hour: str(source.productivity_sqm_per_hour),
    hourly_rate_usd: str(source.hourly_rate_usd),
    adjusted_hours_per_intervention: str(
      source.adjusted_hours_per_intervention,
    ),
    custom_surface_sqm: str(source.custom_surface_sqm),
  };
}

function rememberDraft(id: string) {
  try {
    const ids = new Set<string>(
      JSON.parse(localStorage.getItem(indexKey) ?? "[]"),
    );
    ids.add(id);
    localStorage.setItem(indexKey, JSON.stringify([...ids]));
  } catch {
    /* unavailable storage does not block editing */
  }
}

export const api = {
  listDrafts: async () =>
    (await request<Borrador[]>("/cotizaciones/")).map(normalizeDraft),
  currentProposal: (id: string) =>
    request<Propuesta | null>(
      `/cotizaciones/${encodeURIComponent(id)}/propuestas/actual`,
    ),
  searchClients: (name: string) =>
    request<Cliente[]>(`/clientes/?nombre=${encodeURIComponent(name)}`),
  createClient: (client: Omit<Cliente, "id">) =>
    request<Cliente>("/clientes/", json("POST", client)),
  profiles: () => request<Perfil[]>("/config/perfiles"),
  company: () => request<Record<string, unknown> | null>("/config/empresa"),
  factors: () => request<Array<Record<string, unknown>>>("/config/factores"),
  rates: () => request<Array<Record<string, unknown>>>("/config/tarifas"),
  templates: () =>
    request<Array<Record<string, unknown>>>("/config/plantillas"),
  updateCompany: (value: unknown) =>
    request("/config/empresa", json("PUT", value)),
  updateProfile: (id: number, value: unknown) =>
    request(`/config/perfiles/${id}`, json("PUT", value)),
  createProfile: (value: unknown) =>
    request("/config/perfiles", json("POST", value)),
  updateFactor: (id: number, valor: number) =>
    request(`/config/factores/${id}`, json("PUT", { valor })),
  updateRate: (id: number, valor: number) =>
    request(`/config/tarifas/${id}`, json("PUT", { valor })),
  updateTemplate: (id: number, value: unknown) =>
    request(`/config/plantillas/${id}`, json("PUT", value)),
  createTemplate: (value: unknown) =>
    request("/config/plantillas", json("POST", value)),
  async saveDraft(draft: Borrador): Promise<Borrador> {
    const saved = await request<Borrador>(
      draft.id
        ? `/cotizaciones/${encodeURIComponent(draft.id)}`
        : "/cotizaciones/",
      json(draft.id ? "PUT" : "POST", serializeDraft(draft)),
    );
    if (saved.id) rememberDraft(saved.id);
    return normalizeDraft(saved);
  },
  getDraft: async (id: string) =>
    normalizeDraft(
      await request<Borrador>(`/cotizaciones/${encodeURIComponent(id)}`),
    ),
  localDraftIds: (): string[] => {
    try {
      return JSON.parse(localStorage.getItem(indexKey) ?? "[]");
    } catch {
      return [];
    }
  },
  preview: (id: string) =>
    request<VistaPrevia>(`/cotizaciones/${encodeURIComponent(id)}/preview`),
  analyze: (id: string, text: string) =>
    request<Propuesta>(
      `/cotizaciones/${encodeURIComponent(id)}/propuestas/analizar`,
      json("POST", {
        text,
        confirmed: true,
        personal_data_warning_acknowledged: true,
      }),
    ),
  proposal: (id: string, proposalId: number) =>
    request<Propuesta>(
      `/cotizaciones/${encodeURIComponent(id)}/propuestas/${proposalId}`,
    ),
  review: (id: string, proposalId: number, action: string, payload: unknown) =>
    request<{ review: Propuesta["review"]; draft: Borrador }>(
      `/cotizaciones/${encodeURIComponent(id)}/propuestas/${proposalId}/${action}`,
      json("POST", payload),
    ),
  issue: (id: string) =>
    request<Version>(
      `/cotizaciones/${encodeURIComponent(id)}/versiones`,
      json("POST", {}),
    ),
  history: (query: string) =>
    request<HistorialItem[]>(`/historial?query=${encodeURIComponent(query)}`),
  pdfUrl: (id: string, code: string) =>
    `${base}/cotizaciones/${encodeURIComponent(id)}/versiones/${encodeURIComponent(code)}/pdf`,
};
