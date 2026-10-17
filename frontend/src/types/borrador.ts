export const DIAS_SEMANA = [
  "lunes",
  "martes",
  "miércoles",
  "jueves",
  "viernes",
  "sábado",
  "domingo",
] as const;
export type DiaSemana = (typeof DIAS_SEMANA)[number];
export type Periodo = "semanal" | "quincenal" | "mensual";
export type Estado = "bueno" | "regular" | "malo";

export interface Cliente {
  id: number;
  tipo: string | null;
  nombre: string | null;
  ruc: string | null;
  direccion: string | null;
  telefono: string | null;
  correo: string | null;
}

export interface ClienteBorrador {
  name: string;
  service_address: string;
  identification?: string;
  email?: string;
  phone?: string;
}

export interface Servicio {
  infrastructure_type: string;
  cleaning_type: string;
  start_date: string;
  period_type: Periodo | "";
  start_time: string;
  end_time: string;
}

export interface Trabajo {
  enabled: boolean;
  assigned_workers: string;
  productivity_sqm_per_hour: string;
  hourly_rate_usd: string;
  adjusted_hours_per_intervention: string;
  custom_surface_sqm?: string;
}

export interface Grupo {
  group_id: string;
  name: string;
  units_count: string;
  sqm_per_unit: string;
  service_days: DiaSemana[];
  visits_per_day: string;
  state: Estado | "";
  profile_id: string | null;
  custom_state_factor: string;
  zone: string;
  tasks_description: string;
  general_work: Trabajo;
  specialized_work: Trabajo;
  provenance?: Record<string, unknown>;
}

export interface Recurso {
  resource_id: string;
  description: string;
  kind: "insumo" | "herramienta";
  scope: "grupo" | "compartido";
  group_id: string | null;
  quantity: string;
  unit_cost_usd: string;
  unit: string;
}

export interface Borrador {
  id?: string;
  cliente_id: number | null;
  client: ClienteBorrador;
  service: Servicio;
  groups: Grupo[];
  resources: Recurso[];
  margin_percentage: string;
  discount_usd: string;
  tax_percentage: string;
}

export interface Perfil {
  id: number;
  nombre: string;
  m2_por_hora: number | null;
  unidad: string | null;
  fuente: string;
  valor_original: number | null;
  unidad_original: string | null;
  fuente_url: string | null;
  es_ejemplo: boolean;
}

export interface VistaPrevia {
  quote_id: string;
  is_emission_valid: boolean;
  pending_emission_issues: string[];
  calendar_summary: Record<string, unknown> | null;
  group_efforts: Record<string, unknown>;
  pricing_summary: Record<string, unknown> | null;
}

export interface Version {
  quote_id: string;
  code: string;
  issued_at: string;
  total_usd: string;
  pdf_url: string;
}

export interface HistorialItem {
  quote_id: string;
  code: string;
  issued_at: string;
  client: string;
  service_address: string;
  scope: string;
  total: string;
}

export interface AtributoPropuesto {
  value: unknown;
  condition:
    "explicit" | "derived" | "absent" | "contradictory" | "human_corrected";
  source_fragment?: string | null;
  operation?: string | null;
  origin_values?: Record<string, unknown> | null;
  conflicting_values?: unknown[] | null;
}

export interface GrupoPropuesto {
  id: string;
  name: string;
  quantity?: number | null;
  can_be_confirmed: boolean;
  warnings: string[];
  attributes: Record<string, AtributoPropuesto>;
}

export interface Revision {
  original_text: string;
  revisable_groups: GrupoPropuesto[];
  defective_groups: {
    defect_reasons: string[];
    raw_data: Record<string, unknown>;
  }[];
  confirmed_groups: GrupoPropuesto[];
  discarded_groups: GrupoPropuesto[];
}

export interface Propuesta {
  id: number;
  analysis: { status: string; message: string; fallback_to_manual: boolean };
  review: Revision;
}

export function nuevoTrabajo(): Trabajo {
  return {
    enabled: false,
    assigned_workers: "1",
    productivity_sqm_per_hour: "",
    hourly_rate_usd: "",
    adjusted_hours_per_intervention: "",
    custom_surface_sqm: "",
  };
}

export function nuevoGrupo(): Grupo {
  return {
    group_id: crypto.randomUUID(),
    name: "",
    units_count: "",
    sqm_per_unit: "",
    service_days: [],
    visits_per_day: "1",
    state: "",
    profile_id: null,
    custom_state_factor: "",
    zone: "",
    tasks_description: "",
    general_work: nuevoTrabajo(),
    specialized_work: nuevoTrabajo(),
  };
}

export function nuevoBorrador(): Borrador {
  return {
    cliente_id: null,
    client: { name: "", service_address: "" },
    service: {
      infrastructure_type: "",
      cleaning_type: "",
      start_date: "",
      period_type: "",
      start_time: "",
      end_time: "",
    },
    groups: [],
    resources: [],
    margin_percentage: "",
    discount_usd: "0",
    tax_percentage: "",
  };
}
