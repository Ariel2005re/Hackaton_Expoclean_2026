import type { VistaPrevia } from "../types/borrador";

const obj = (value: unknown): Record<string, unknown> =>
  value && typeof value === "object" ? (value as Record<string, unknown>) : {};
const label = (value: unknown) => (value == null ? "—" : String(value));
const money = (value: unknown) => value == null ? "—" : Number(value).toFixed(2);

export default function PreviewDetails({ preview, groupNames = {} }: { preview: VistaPrevia; groupNames?: Record<string, string> }) {
  const groupName = (id: string) => groupNames[id] || id;
  const calendar = obj(preview.calendar_summary);
  const price = obj(preview.pricing_summary);
  const efforts = Object.entries(preview.group_efforts ?? {});
  const lines = [
    ...(Array.isArray(price.labor_lines) ? price.labor_lines : []),
    ...(Array.isArray(price.group_resource_lines)
      ? price.group_resource_lines
      : []),
    ...(Array.isArray(price.shared_resource_lines)
      ? price.shared_resource_lines
      : []),
  ].map(obj);
  return (
    <>
      {preview.calendar_summary && (
        <section>
          <h3>Calendario</h3>
          <p>
            Desde {label(calendar.start_date)} hasta {label(calendar.end_date)}{" "}
            · {label(calendar.total_days)} días ·{" "}
            {label(calendar.shared_service_days_count)} jornadas con servicio
            compartido.
          </p>
          <ul>
            {Object.entries(obj(calendar.group_interventions)).map(
              ([id, count]) => (
                <li key={id}>
                  Grupo {groupName(id)}: {label(count)} intervenciones
                </li>
              ),
            )}
          </ul>
        </section>
      )}
      {efforts.length > 0 && (
        <section>
          <h3>Superficies y horas por intervención</h3>
          <table>
            <thead>
              <tr>
                <th>Grupo</th>
                <th>m² físicos</th>
                <th>Trabajo general</th>
                <th>Trabajo especializado</th>
                <th>Duración de visita</th>
              </tr>
            </thead>
            <tbody>
              {efforts.map(([id, raw]) => {
                const group = obj(raw),
                  general = obj(group.general),
                  specialized = obj(group.specialized);
                const detail = (work: Record<string, unknown>) =>
                  Object.keys(work).length
                    ? `${label(work.surface_sqm)} m² · ${label(work.total_hours_per_intervention)} h por intervención · ${Number(work.total_hours_per_intervention) * Number(obj(calendar.group_interventions)[id] ?? 0)} h en el período · ${label(work.assigned_workers)} personas · ${label(work.duration_hours)} h de duración`
                    : "No incluido";
                return (
                  <tr key={id}>
                    <td>{groupName(id)}</td>
                    <td>{label(group.physical_sqm)}</td>
                    <td>{detail(general)}</td>
                    <td>{detail(specialized)}</td>
                    <td>{label(group.visit_duration_hours)} h</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </section>
      )}
      {preview.pricing_summary && (
        <section>
          <h3>Desglose interno en USD</h3>
          <table>
            <thead>
              <tr>
                <th>Concepto</th>
                <th>Alcance</th>
                <th>Recurrencia</th>
                <th>Costo período</th>
              </tr>
            </thead>
            <tbody>
              {lines.map((line, index) => (
                <tr key={index}>
                  <td>{label(line.description)}</td>
                  <td>
                    {line.scope === "compartido"
                      ? "Compartido"
                      : `Grupo ${groupName(label(line.group_id))}`}
                  </td>
                  <td>{label(line.recurrence_count)}</td>
                  <td>{money(line.rounded_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <dl className="totals">
            <div>
              <dt>Mano de obra general</dt>
              <dd>{money(price.total_labor_general_usd)}</dd>
            </div>
            <div>
              <dt>Mano de obra especializada</dt>
              <dd>{money(price.total_labor_specialized_usd)}</dd>
            </div>
            <div>
              <dt>Insumos</dt>
              <dd>{money(price.total_insumos_usd)}</dd>
            </div>
            <div>
              <dt>Herramientas</dt>
              <dd>{money(price.total_herramientas_usd)}</dd>
            </div>
            <div>
              <dt>Costo directo</dt>
              <dd>{money(price.direct_cost_usd)}</dd>
            </div>
            <div>
              <dt>Margen</dt>
              <dd>{money(price.margin_usd)}</dd>
            </div>
            <div>
              <dt>Descuento</dt>
              <dd>{money(price.discount_usd)}</dd>
            </div>
            <div>
              <dt>Subtotal</dt>
              <dd>{money(price.subtotal_usd)}</dd>
            </div>
            <div>
              <dt>Impuesto</dt>
              <dd>{money(price.tax_usd)}</dd>
            </div>
            <div className="grand-total">
              <dt>Total USD</dt>
              <dd>{money(price.total_usd)}</dd>
            </div>
          </dl>
          {Boolean(price.subtotal_error) && (
            <p role="alert">{label(price.subtotal_error)}</p>
          )}
        </section>
      )}
    </>
  );
}
