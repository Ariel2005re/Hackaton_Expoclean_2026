import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { Perfil } from "../types/borrador";

type Row = Record<string, unknown>;
const number = (value: unknown) => Number(value);

export default function Configuracion() {
  const [company, setCompany] = useState<Row>({
    nombre: "",
    margen_porcentaje: 0,
    impuesto_porcentaje: 0,
  });
  const [profiles, setProfiles] = useState<Perfil[]>([]);
  const [factors, setFactors] = useState<Row[]>([]);
  const [rates, setRates] = useState<Row[]>([]);
  const [templates, setTemplates] = useState<Row[]>([]);
  const [newProfile, setNewProfile] = useState("");
  const [newTemplate, setNewTemplate] = useState<Row>({
    nombre: "",
    tipo: "insumo",
    unidad: "unidad",
    costo_unitario: 0,
  });
  const [notice, setNotice] = useState("");

  async function refresh() {
    try {
      const [c, p, f, r, t] = await Promise.all([
        api.company(),
        api.profiles(),
        api.factors(),
        api.rates(),
        api.templates(),
      ]);
      setCompany(
        c ?? { nombre: "", margen_porcentaje: 0, impuesto_porcentaje: 0 },
      );
      setProfiles(p);
      setFactors(f);
      setRates(r);
      setTemplates(t);
    } catch (e) {
      setNotice(String(e));
    }
  }
  useEffect(() => {
    void refresh();
  }, []);
  async function run(action: Promise<unknown>) {
    try {
      await action;
      await refresh();
      setNotice("Configuración guardada.");
    } catch (e) {
      setNotice(String(e));
    }
  }
  function setRow(
    rows: Row[],
    setter: (rows: Row[]) => void,
    id: unknown,
    key: string,
    value: unknown,
  ) {
    setter(rows.map((row) => (row.id === id ? { ...row, [key]: value } : row)));
  }

  return (
    <section>
      <h1>Configuración de empresa</h1>
      <p>
        Los rendimientos, tarifas y factores de demostración son ejemplos
        editables. Las fichas SERCOP son referencias de partida, no tarifas
        vigentes.
      </p>
      {notice && <p role="status">{notice}</p>}
      <fieldset className="form-section">
        <legend>Empresa</legend>
        <div className="form-grid">
          <label>
            Nombre
            <input
              value={String(company.nombre ?? "")}
              onChange={(e) =>
                setCompany({ ...company, nombre: e.target.value })
              }
            />
          </label>
          <label>
            Margen %
            <input
              inputMode="decimal"
              value={String(company.margen_porcentaje ?? "")}
              onChange={(e) =>
                setCompany({ ...company, margen_porcentaje: e.target.value })
              }
            />
          </label>
          <label>
            Impuesto %
            <input
              inputMode="decimal"
              value={String(company.impuesto_porcentaje ?? "")}
              onChange={(e) =>
                setCompany({ ...company, impuesto_porcentaje: e.target.value })
              }
            />
          </label>
        </div>
        <button
          type="button"
          onClick={() =>
            void run(
              api.updateCompany({
                nombre: company.nombre,
                margen_porcentaje: number(company.margen_porcentaje),
                impuesto_porcentaje: number(company.impuesto_porcentaje),
              }),
            )
          }
        >
          Guardar empresa
        </button>
      </fieldset>
      <fieldset className="form-section">
        <legend>Perfiles y referencias</legend>
        {profiles.map((profile) => (
          <div className="config-row" key={profile.id}>
            <div>
              <strong>{profile.nombre}</strong> · {profile.fuente}{" "}
              {profile.es_ejemplo && <em>Ejemplo editable</em>}
              <br />
              Referencia original: {profile.valor_original ?? "—"}{" "}
              {profile.unidad_original ?? ""}{" "}
              {profile.fuente_url && (
                <a href={profile.fuente_url} target="_blank" rel="noreferrer">
                  Fuente SERCOP
                </a>
              )}
            </div>
            <label>
              Rendimiento ({profile.unidad ?? "m²/hora"})
              <input
                inputMode="decimal"
                value={profile.m2_por_hora ?? ""}
                onChange={(e) =>
                  setProfiles(
                    profiles.map((p) =>
                      p.id === profile.id
                        ? {
                            ...p,
                            m2_por_hora:
                              e.target.value === ""
                                ? null
                                : Number(e.target.value),
                          }
                        : p,
                    ),
                  )
                }
              />
            </label>
            <button
              type="button"
              onClick={() =>
                void run(
                  api.updateProfile(profile.id, {
                    m2_por_hora: profile.m2_por_hora,
                  }),
                )
              }
            >
              Guardar
            </button>
          </div>
        ))}
        <div className="config-row">
          <label>
            Nuevo perfil propio
            <input
              value={newProfile}
              onChange={(e) => setNewProfile(e.target.value)}
            />
          </label>
          <button
            type="button"
            disabled={!newProfile.trim()}
            onClick={() =>
              void run(
                api.createProfile({ nombre: newProfile, m2_por_hora: null }),
              )
            }
          >
            Crear perfil
          </button>
        </div>
      </fieldset>
      <fieldset className="form-section">
        <legend>Factores por estado</legend>
        {factors.map((row) => (
          <div className="config-row" key={String(row.id)}>
            <label>
              {String(row.nombre)} · ejemplo editable
              <input
                inputMode="decimal"
                value={String(row.valor ?? "")}
                onChange={(e) =>
                  setRow(factors, setFactors, row.id, "valor", e.target.value)
                }
              />
            </label>
            <button
              type="button"
              onClick={() =>
                void run(api.updateFactor(number(row.id), number(row.valor)))
              }
            >
              Guardar
            </button>
          </div>
        ))}
      </fieldset>
      <fieldset className="form-section">
        <legend>Tarifas de trabajo</legend>
        {rates.map((row) => (
          <div className="config-row" key={String(row.id)}>
            <label>
              {String(row.descripcion)} ({String(row.unidad)}){" "}
              {Boolean(row.es_ejemplo) && "· ejemplo editable"}
              <input
                inputMode="decimal"
                value={String(row.monto ?? "")}
                onChange={(e) =>
                  setRow(rates, setRates, row.id, "monto", e.target.value)
                }
              />
            </label>
            <button
              type="button"
              onClick={() =>
                void run(api.updateRate(number(row.id), number(row.monto)))
              }
            >
              Guardar
            </button>
          </div>
        ))}
      </fieldset>
      <fieldset className="form-section">
        <legend>Plantillas de insumos y herramientas</legend>
        {templates.map((row) => (
          <div className="config-row" key={String(row.id)}>
            <label>
              Nombre
              <input
                value={String(row.nombre ?? "")}
                onChange={(e) =>
                  setRow(
                    templates,
                    setTemplates,
                    row.id,
                    "nombre",
                    e.target.value,
                  )
                }
              />
            </label>
            <label>
              Tipo
              <input
                value={String(row.tipo ?? "")}
                onChange={(e) =>
                  setRow(
                    templates,
                    setTemplates,
                    row.id,
                    "tipo",
                    e.target.value,
                  )
                }
              />
            </label>
            <label>
              Unidad
              <input
                value={String(row.unidad ?? "")}
                onChange={(e) =>
                  setRow(
                    templates,
                    setTemplates,
                    row.id,
                    "unidad",
                    e.target.value,
                  )
                }
              />
            </label>
            <label>
              Costo USD
              <input
                inputMode="decimal"
                value={String(row.costo_unitario ?? "")}
                onChange={(e) =>
                  setRow(
                    templates,
                    setTemplates,
                    row.id,
                    "costo_unitario",
                    e.target.value,
                  )
                }
              />
            </label>
            <button
              type="button"
              onClick={() =>
                void run(
                  api.updateTemplate(number(row.id), {
                    nombre: row.nombre,
                    tipo: row.tipo,
                    unidad: row.unidad,
                    costo_unitario: number(row.costo_unitario),
                  }),
                )
              }
            >
              Guardar
            </button>
          </div>
        ))}
        <div className="config-row">
          <label>
            Nombre
            <input
              value={String(newTemplate.nombre)}
              onChange={(e) =>
                setNewTemplate({ ...newTemplate, nombre: e.target.value })
              }
            />
          </label>
          <label>
            Tipo
            <select
              value={String(newTemplate.tipo)}
              onChange={(e) =>
                setNewTemplate({ ...newTemplate, tipo: e.target.value })
              }
            >
              <option value="insumo">Insumo</option>
              <option value="herramienta">Herramienta</option>
            </select>
          </label>
          <label>
            Unidad
            <input
              value={String(newTemplate.unidad)}
              onChange={(e) =>
                setNewTemplate({ ...newTemplate, unidad: e.target.value })
              }
            />
          </label>
          <label>
            Costo USD
            <input
              inputMode="decimal"
              value={String(newTemplate.costo_unitario)}
              onChange={(e) =>
                setNewTemplate({
                  ...newTemplate,
                  costo_unitario: e.target.value,
                })
              }
            />
          </label>
          <button
            type="button"
            disabled={!String(newTemplate.nombre).trim()}
            onClick={() =>
              void run(
                api.createTemplate({
                  ...newTemplate,
                  costo_unitario: number(newTemplate.costo_unitario),
                }),
              )
            }
          >
            Crear
          </button>
        </div>
      </fieldset>
    </section>
  );
}
