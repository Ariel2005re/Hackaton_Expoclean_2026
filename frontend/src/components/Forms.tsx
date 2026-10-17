import {
  DIAS_SEMANA,
  nuevoTrabajo,
  type Borrador,
  type Grupo,
  type Perfil,
  type Recurso,
  type Trabajo,
} from "../types/borrador";

type Change<T> = (value: T) => void;

export function ServiceForm({
  value,
  onChange,
}: {
  value: Borrador["service"];
  onChange: Change<Borrador["service"]>;
}) {
  const set = (key: keyof Borrador["service"], data: string) =>
    onChange({ ...value, [key]: data });
  const badHours = Boolean(
    value.start_time && value.end_time && value.end_time <= value.start_time,
  );
  return (
    <fieldset className="form-section">
      <legend>Servicio</legend>
      <div className="form-grid">
        <label>
          Tipo de infraestructura
          <input
            value={value.infrastructure_type}
            onChange={(e) => set("infrastructure_type", e.target.value)}
          />
        </label>
        <label>
          Tipo de limpieza
          <input
            value={value.cleaning_type}
            onChange={(e) => set("cleaning_type", e.target.value)}
          />
        </label>
        <label>
          Fecha de inicio
          <input
            type="date"
            value={value.start_date}
            onChange={(e) => set("start_date", e.target.value)}
          />
        </label>
        <label>
          Período
          <select
            value={value.period_type}
            onChange={(e) => set("period_type", e.target.value)}
          >
            <option value="">Seleccione…</option>
            <option value="semanal">Semanal</option>
            <option value="quincenal">Quincenal</option>
            <option value="mensual">Mensual</option>
          </select>
        </label>
        <label>
          Hora de inicio
          <input
            type="time"
            value={value.start_time}
            onChange={(e) => set("start_time", e.target.value)}
          />
        </label>
        <label>
          Hora de fin
          <input
            type="time"
            value={value.end_time}
            onChange={(e) => set("end_time", e.target.value)}
          />
        </label>
      </div>
      {badHours && (
        <p role="alert" className="pendientes-list">
          La hora de fin debe ser posterior al inicio, dentro del mismo día.
        </p>
      )}
    </fieldset>
  );
}

function WorkForm({
  title,
  value,
  onChange,
  specialized,
}: {
  title: string;
  value: Trabajo;
  onChange: Change<Trabajo>;
  specialized?: boolean;
}) {
  const set = (key: keyof Trabajo, data: string | boolean) =>
    onChange({ ...value, [key]: data });
  return (
    <fieldset className="trabajo-subseccion">
      <legend>{title}</legend>
      <label className="check">
        <input
          type="checkbox"
          checked={value.enabled}
          onChange={(e) => set("enabled", e.target.checked)}
        />{" "}
        Incluir este trabajo
      </label>
      {value.enabled && (
        <div className="form-grid">
          {specialized && (
            <label>
              Superficie especializada total por intervención (m²)
              <input
                inputMode="decimal"
                value={value.custom_surface_sqm ?? ""}
                onChange={(e) => set("custom_surface_sqm", e.target.value)}
              />
            </label>
          )}
          <label>
            Personas asignadas
            <input
              inputMode="numeric"
              value={value.assigned_workers}
              onChange={(e) => set("assigned_workers", e.target.value)}
            />
          </label>
          <label>
            Rendimiento (m²/hora de trabajo)
            <input
              inputMode="decimal"
              value={value.productivity_sqm_per_hour}
              onChange={(e) => set("productivity_sqm_per_hour", e.target.value)}
              placeholder="Usar perfil de empresa"
            />
          </label>
          <label>
            Tarifa (USD/hora de trabajo)
            <input
              inputMode="decimal"
              value={value.hourly_rate_usd}
              onChange={(e) => set("hourly_rate_usd", e.target.value)}
              placeholder="Usar tarifa de empresa"
            />
          </label>
          <label>
            Horas totales ajustadas por intervención
            <input
              inputMode="decimal"
              value={value.adjusted_hours_per_intervention}
              onChange={(e) =>
                set("adjusted_hours_per_intervention", e.target.value)
              }
              placeholder="Usar horas calculadas"
            />
          </label>
        </div>
      )}
      {specialized && value.enabled && !value.custom_surface_sqm?.trim() && (
        <p className="pendientes-list">
          Confirme la superficie especializada para emitir.
        </p>
      )}
    </fieldset>
  );
}

export function GroupEditor({
  group,
  profiles,
  onChange,
  onRemove,
  onSplit,
}: {
  group: Grupo;
  profiles: Perfil[];
  onChange: Change<Grupo>;
  onRemove: () => void;
  onSplit: () => void;
}) {
  const set = (key: keyof Grupo, data: unknown) =>
    onChange({ ...group, [key]: data });
  const toggleDay = (day: (typeof DIAS_SEMANA)[number]) =>
    set(
      "service_days",
      group.service_days.includes(day)
        ? group.service_days.filter((d) => d !== day)
        : [...group.service_days, day],
    );
  return (
    <fieldset className="form-section">
      <legend>Grupo: {group.name || "sin nombre"}</legend>
      <div className="form-grid">
        <label>
          Nombre
          <input
            value={group.name}
            onChange={(e) => set("name", e.target.value)}
          />
        </label>
        <label>
          Cantidad de espacios
          <input
            inputMode="numeric"
            value={group.units_count}
            onChange={(e) => set("units_count", e.target.value)}
          />
        </label>
        <label>
          m² por unidad
          <input
            inputMode="decimal"
            value={group.sqm_per_unit}
            onChange={(e) => set("sqm_per_unit", e.target.value)}
          />
        </label>
        <label>
          Visitas por día de servicio
          <input
            inputMode="numeric"
            value={group.visits_per_day}
            onChange={(e) => set("visits_per_day", e.target.value)}
          />
        </label>
        <label>
          Estado
          <select
            value={group.state}
            onChange={(e) => set("state", e.target.value)}
          >
            <option value="">Seleccione…</option>
            <option value="bueno">Bueno</option>
            <option value="regular">Regular</option>
            <option value="malo">Malo</option>
          </select>
        </label>
        <label>
          Perfil de referencia
          <select
            value={group.profile_id ?? ""}
            onChange={(e) => set("profile_id", e.target.value || null)}
          >
            <option value="">Seleccione…</option>
            {profiles.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nombre}
              </option>
            ))}
          </select>
        </label>
        <label>
          Factor de estado personalizado
          <input
            inputMode="decimal"
            value={group.custom_state_factor}
            onChange={(e) => set("custom_state_factor", e.target.value)}
            placeholder="Usar factor de empresa"
          />
        </label>
        <label>
          Zona
          <input
            value={group.zone}
            onChange={(e) => set("zone", e.target.value)}
          />
        </label>
        <label className="full">
          Tareas
          <textarea
            value={group.tasks_description}
            onChange={(e) => set("tasks_description", e.target.value)}
          />
        </label>
      </div>
      <div className="field-group">
        <span>Días de servicio por semana</span>
        <div className="dias-grid">
          {DIAS_SEMANA.map((day) => (
            <label className="dia-checkbox" key={day}>
              <input
                type="checkbox"
                checked={group.service_days.includes(day)}
                onChange={() => toggleDay(day)}
              />
              {day}
            </label>
          ))}
        </div>
      </div>
      <WorkForm
        title="Trabajo general"
        value={group.general_work ?? nuevoTrabajo()}
        onChange={(v) => set("general_work", v)}
      />
      <WorkForm
        title="Trabajo especializado"
        specialized
        value={group.specialized_work ?? nuevoTrabajo()}
        onChange={(v) => set("specialized_work", v)}
      />
      <div className="form-actions">
        <button
          type="button"
          onClick={onSplit}
          disabled={Number(group.units_count) < 2}
        >
          Separar cantidad
        </button>
        <button type="button" className="danger" onClick={onRemove}>
          Quitar grupo
        </button>
      </div>
    </fieldset>
  );
}

export function ResourceEditor({
  resource,
  groups,
  onChange,
  onRemove,
}: {
  resource: Recurso;
  groups: Grupo[];
  onChange: Change<Recurso>;
  onRemove: () => void;
}) {
  const set = (key: keyof Recurso, data: unknown) =>
    onChange({ ...resource, [key]: data });
  return (
    <fieldset className="form-section">
      <legend>Recurso: {resource.description || "sin descripción"}</legend>
      <div className="form-grid">
        <label>
          Descripción
          <input
            value={resource.description}
            onChange={(e) => set("description", e.target.value)}
          />
        </label>
        <label>
          Clase
          <select
            value={resource.kind}
            onChange={(e) => set("kind", e.target.value)}
          >
            <option value="insumo">Insumo</option>
            <option value="herramienta">Herramienta</option>
          </select>
        </label>
        <label>
          Alcance
          <select
            value={resource.scope}
            onChange={(e) =>
              onChange({
                ...resource,
                scope: e.target.value as Recurso["scope"],
                group_id:
                  e.target.value === "grupo"
                    ? (groups[0]?.group_id ?? null)
                    : null,
              })
            }
          >
            <option value="grupo">Del grupo: por intervención</option>
            <option value="compartido">Compartido: por jornada</option>
          </select>
        </label>
        {resource.scope === "grupo" && (
          <label>
            Grupo
            <select
              value={resource.group_id ?? ""}
              onChange={(e) => set("group_id", e.target.value)}
            >
              <option value="">Seleccione…</option>
              {groups.map((g) => (
                <option key={g.group_id} value={g.group_id}>
                  {g.name || g.group_id}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          Cantidad decimal
          <input
            inputMode="decimal"
            value={resource.quantity}
            onChange={(e) => set("quantity", e.target.value)}
          />
        </label>
        <label>
          Unidad
          <input
            value={resource.unit}
            onChange={(e) => set("unit", e.target.value)}
          />
        </label>
        <label>
          Costo unitario USD
          <input
            inputMode="decimal"
            value={resource.unit_cost_usd}
            onChange={(e) => set("unit_cost_usd", e.target.value)}
          />
        </label>
      </div>
      <button type="button" className="danger" onClick={onRemove}>
        Quitar recurso
      </button>
    </fieldset>
  );
}
