import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../api/client";
import {
  decodeTxtBytes,
  textIssue,
  parseCorrection,
} from "../api/extractionText";
import { GroupEditor, ResourceEditor, ServiceForm } from "../components/Forms";
import PreviewDetails from "../components/PreviewDetails";
import SplitGroup, { partitionGroup } from "../components/SplitGroup";
import {
  nuevoBorrador,
  nuevoGrupo,
  type Borrador,
  type Cliente,
  type Grupo,
  type HistorialItem,
  type Perfil,
  type Propuesta,
  type Recurso,
  type Version,
  type VistaPrevia,
} from "../types/borrador";

const message = (error: unknown) =>
  error instanceof Error ? error.message : String(error);
const pretty = (value: unknown) =>
  value == null ? "Sin dato" : typeof value === "object" ? JSON.stringify(value) : String(value);
const attributeLabel = (name: string) => ({
  name: "Nombre", quantity: "Cantidad", unit_area_m2: "m² por unidad",
  total_area_m2: "Superficie total m²", condition: "Estado",
  cleaning_type: "Tipo de trabajo", visits_per_day: "Visitas por día",
  service_days: "Días de servicio",
} as Record<string, string>)[name] ?? name;
const conditionLabels = {
  explicit: "Explícito", derived: "Derivado", absent: "Ausente",
  contradictory: "Contradictorio", human_corrected: "Corregido por el usuario",
};

export default function NuevaCotizacion() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [draft, setDraft] = useState<Borrador>(nuevoBorrador);
  const [loaded, setLoaded] = useState(!id);
  const [profiles, setProfiles] = useState<Perfil[]>([]);
  const [clients, setClients] = useState<Cliente[]>([]);
  const [clientQuery, setClientQuery] = useState("");
  const [clientType, setClientType] = useState("juridica");
  const [notice, setNotice] = useState("");
  const [preview, setPreview] = useState<VistaPrevia | null>(null);
  const [busy, setBusy] = useState(false);
  const [text, setText] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [proposal, setProposal] = useState<Propuesta | null>(null);
  const [selected, setSelected] = useState<string[]>([]);
  const [correction, setCorrection] = useState<{ groupId: string; name: string; value: string } | null>(null);
  const [proposalSplit, setProposalSplit] = useState<{ groupId: string; left: string; right: string } | null>(null);
  const [splitting, setSplitting] = useState<Grupo | null>(null);
  const [versions, setVersions] = useState<HistorialItem[]>([]);
  const [latestVersion, setLatestVersion] = useState<Version | null>(null);
  const editNumber = useRef(0);
  const saveQueue = useRef<Promise<unknown>>(Promise.resolve());

  useEffect(() => {
    let active = true;
    setConfirmed(false);
    setProposal(null);
    setSelected([]);
    setCorrection(null);
    setProposalSplit(null);
    setPreview(null);
    setLatestVersion(null);
    setVersions([]);
    setNotice("");
    setSplitting(null);
    try {
      setText(localStorage.getItem(`mvp-web-text-${id ?? "new"}`) ?? "");
    } catch {
      /* storage optional */
    }
    api
      .profiles()
      .then((p) => {
        if (active) setProfiles(p);
      })
      .catch((e) => {
        if (active) setNotice(`Perfiles: ${message(e)}`);
      });
    api
      .searchClients("")
      .then((items) => {
        if (active) setClients(items);
      })
      .catch(() => {});
    if (id) {
      setLoaded(false);
      Promise.all([api.getDraft(id), api.currentProposal(id)])
        .then(([d, current]) => {
          if (active) {
            setDraft(d);
            setProposal(current);
            if (current) {
              let cached: string | null = null;
              try { cached = localStorage.getItem(`mvp-web-text-${id}`); } catch { /* optional storage */ }
              setText(cached ?? current.review.original_text);
            }
            setLoaded(true);
          }
        })
        .catch((e) => {
          if (active) setNotice(`Borrador: ${message(e)}`);
        });
    } else {
      setDraft(nuevoBorrador());
      setLoaded(true);
    }
    return () => {
      active = false;
    };
  }, [id]);

  useEffect(() => {
    if (!draft.id) return;
    api
      .history("")
      .then((items) =>
        setVersions(items.filter((item) => item.quote_id === draft.id)),
      )
      .catch(() => {});
  }, [draft.id, latestVersion]);

  function change(next: Borrador) {
    editNumber.current += 1;
    setDraft(next);
    setPreview(null);
  }

  function queueSave(value: Borrador) {
    const run = saveQueue.current
      .catch(() => {})
      .then(() => api.saveDraft(value));
    saveQueue.current = run;
    return run;
  }

  async function save(value: Borrador = draft, manageBusy = true) {
    if (manageBusy) setBusy(true);
    try {
      const saved = await queueSave(value);
      if (!value.id) {
        try {
          localStorage.setItem(`mvp-web-text-${saved.id}`, text);
          localStorage.removeItem("mvp-web-text-new");
        } catch {
          /* storage optional */
        }
        setDraft(saved);
        navigate(`/borradores/${saved.id}`, { replace: true });
      }
      setNotice("Borrador guardado.");
      return saved;
    } catch (e) {
      setNotice(`No se pudo guardar: ${message(e)}`);
      return null;
    } finally {
      if (manageBusy) setBusy(false);
    }
  }

  async function updatePreview(value: Borrador = draft, silent = false) {
    try {
      const revision = editNumber.current;
      const saved = await queueSave(value);
      const result = await api.preview(saved.id!);
      if (revision === editNumber.current) setPreview(result);
      if (!value.id) {
        setDraft(saved);
        navigate(`/borradores/${saved.id}`, { replace: true });
      }
      if (!silent) setNotice("Vista previa actualizada.");
    } catch (e) {
      setNotice(`Vista previa: ${message(e)}. El borrador permanece editable.`);
    }
  }

  useEffect(() => {
    if (!loaded || !draft.id || busy) return;
    const timer = window.setTimeout(() => {
      void updatePreview(draft, true);
    }, 650);
    return () => window.clearTimeout(timer);
    // Only a user edit triggers this; the queued saves preserve edit order.
  }, [draft, loaded, busy]);

  async function searchClients() {
    try {
      setClients(await api.searchClients(clientQuery));
    } catch (e) {
      setNotice(message(e));
    }
  }

  async function registerClient() {
    if (!draft.client.name.trim()) {
      setNotice("Escriba el nombre del cliente.");
      return;
    }
    try {
      const client = await api.createClient({
        tipo: clientType,
        nombre: draft.client.name,
        ruc: draft.client.identification || null,
        direccion: null,
        telefono: draft.client.phone || null,
        correo: draft.client.email || null,
      });
      change({ ...draft, cliente_id: client.id });
      setNotice("Cliente registrado.");
    } catch (e) {
      setNotice(message(e));
    }
  }

  function changeGroup(value: Grupo) {
    change({
      ...draft,
      groups: draft.groups.map((g) =>
        g.group_id === value.group_id ? value : g,
      ),
    });
  }
  function splitGroup(group: Grupo) {
    const count = Number(group.units_count);
    if (!Number.isInteger(count) || count < 2) return;
    if (
      draft.resources.some(
        (r) => r.scope === "grupo" && r.group_id === group.group_id,
      )
    ) {
      setSplitting(group);
      return;
    }
    applySplit(partitionGroup(group, Math.floor(count / 2)), []);
  }

  function applySplit(groups: [Grupo, Grupo], resources: Recurso[]) {
    change({
      ...draft,
      groups: draft.groups.flatMap((g) =>
        g.group_id === groups[0].group_id ? groups : [g],
      ),
      resources: [
        ...draft.resources.filter((r) => r.group_id !== groups[0].group_id),
        ...resources,
      ],
    });
    setSplitting(null);
  }

  function addResource() {
    const resource: Recurso = {
      resource_id: crypto.randomUUID(),
      description: "",
      kind: "insumo",
      scope: "compartido",
      group_id: null,
      quantity: "",
      unit_cost_usd: "",
      unit: "unidad",
    };
    change({ ...draft, resources: [...draft.resources, resource] });
  }

  async function readTxt(file: File | undefined) {
    if (!file) return;
    try {
      const data = await file.arrayBuffer();
      const decoded = decodeTxtBytes(file.name, data);
      setText(decoded);
      setConfirmed(false);
      try {
        localStorage.setItem(`mvp-web-text-${draft.id ?? "new"}`, decoded);
      } catch {
        /* storage optional */
      }
      setNotice("TXT cargado; revise el texto exacto antes de confirmar.");
    } catch (e) {
      setNotice(message(e));
    }
  }

  async function analyze() {
    const issue = textIssue(text);
    if (issue) {
      setNotice(issue);
      return;
    }
    if (!confirmed) {
      setNotice(
        "Confirme el texto exacto y la advertencia de datos personales.",
      );
      return;
    }
    try {
      setConfirmed(false);
      setBusy(true);
      const saved = await save(draft, false);
      if (!saved) return;
      setNotice("Analizando descripción con Gemini…");
      const result = await api.analyze(saved.id!, text);
      setProposal(result);
      setSelected([]);
      setNotice(result.analysis.message);
    } catch (e) {
      setNotice(`Gemini: ${message(e)}. Puede continuar manualmente.`);
    } finally {
      setBusy(false);
    }
  }

  async function review(action: string, payload: Record<string, unknown>) {
    if (!draft.id || !proposal) return;
    try {
      setBusy(true);
      if (action === "confirmar" && !(await save(draft, false))) return;
      const response = await api.review(draft.id, proposal.id, action, payload);
      setProposal({ ...proposal, review: response.review });
      setSelected([]);
      if (action === "confirmar") change(await api.getDraft(draft.id));
      setNotice("Revisión guardada.");
    } catch (e) {
      setNotice(`Revisión: ${message(e)}`);
    } finally {
      setBusy(false);
    }
  }

  async function issue() {
    if (!preview?.is_emission_valid) return;
    try {
      setBusy(true);
      const saved = await save(draft, false);
      if (!saved) return;
      const fresh = await api.preview(saved.id!);
      setPreview(fresh);
      if (!fresh.is_emission_valid) {
        setNotice("La cotización tiene pendientes de emisión.");
        return;
      }
      const version = await api.issue(saved.id!);
      setLatestVersion(version);
      setNotice(`Versión ${version.code} disponible.`);
    } catch (e) {
      setNotice(`No se pudo emitir: ${message(e)}`);
    } finally {
      setBusy(false);
    }
  }

  if (!loaded) return <p role="status">{notice || "Cargando borrador…"}</p>;
  return (
    <section>
      <fieldset disabled={busy} style={{ border: 0, padding: 0, margin: 0 }}>
        <h1>{draft.id ? "Editar cotización" : "Nueva cotización"}</h1>
        {notice && (
          <p role="status" className="status">
            {notice}
          </p>
        )}
        <fieldset className="form-section">
          <legend>Cliente y dirección del servicio</legend>
          <div className="form-grid">
            <label>
              Buscar cliente existente
              <input
                value={clientQuery}
                onChange={(e) => setClientQuery(e.target.value)}
              />
            </label>
            <button type="button" onClick={() => void searchClients()}>
              Buscar clientes
            </button>
            <label>
              Cliente
              <select
                value={draft.cliente_id ?? ""}
                onChange={(e) => {
                  const client = clients.find(
                    (c) => c.id === Number(e.target.value),
                  );
                  change({
                    ...draft,
                    cliente_id: client?.id ?? null,
                    client: {
                      ...draft.client,
                      name: client?.nombre ?? "",
                      identification: client?.ruc ?? "",
                      email: client?.correo ?? "",
                      phone: client?.telefono ?? "",
                    },
                  });
                }}
              >
                <option value="">Nuevo o sin seleccionar</option>
                {clients.map((client) => (
                  <option value={client.id} key={client.id}>
                    {client.nombre}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Tipo de cliente nuevo
              <select
                value={clientType}
                onChange={(e) => setClientType(e.target.value)}
              >
                <option value="natural">Persona natural</option>
                <option value="juridica">Persona jurídica</option>
              </select>
            </label>
            <label>
              Nombre del cliente
              <input
                value={draft.client.name}
                onChange={(e) =>
                  change({
                    ...draft,
                    cliente_id: null,
                    client: { ...draft.client, name: e.target.value },
                  })
                }
              />
            </label>
            <label>
              Dirección del servicio
              <input
                value={draft.client.service_address}
                onChange={(e) =>
                  change({
                    ...draft,
                    client: {
                      ...draft.client,
                      service_address: e.target.value,
                    },
                  })
                }
              />
            </label>
            <label>
              RUC o identificación
              <input
                value={draft.client.identification ?? ""}
                onChange={(e) =>
                  change({
                    ...draft,
                    client: { ...draft.client, identification: e.target.value },
                  })
                }
              />
            </label>
            <label>
              Correo
              <input
                type="email"
                value={draft.client.email ?? ""}
                onChange={(e) =>
                  change({
                    ...draft,
                    client: { ...draft.client, email: e.target.value },
                  })
                }
              />
            </label>
            <label>
              Teléfono
              <input
                value={draft.client.phone ?? ""}
                onChange={(e) =>
                  change({
                    ...draft,
                    client: { ...draft.client, phone: e.target.value },
                  })
                }
              />
            </label>
          </div>
          <button type="button" onClick={() => void registerClient()}>
            Registrar cliente
          </button>
        </fieldset>
        <ServiceForm
          value={draft.service}
          onChange={(service) => change({ ...draft, service })}
        />
        <h2>Grupos</h2>
        {splitting && (
          <SplitGroup
            group={splitting}
            resources={draft.resources.filter(
              (r) => r.scope === "grupo" && r.group_id === splitting.group_id,
            )}
            onApply={applySplit}
            onCancel={() => setSplitting(null)}
          />
        )}
        {draft.groups.map((group) => (
          <GroupEditor
            key={group.group_id}
            group={group}
            profiles={profiles}
            onChange={changeGroup}
            onSplit={() => splitGroup(group)}
            onRemove={() =>
              change({
                ...draft,
                groups: draft.groups.filter(
                  (g) => g.group_id !== group.group_id,
                ),
                resources: draft.resources.filter(
                  (r) => r.group_id !== group.group_id,
                ),
              })
            }
          />
        ))}
        <button
          type="button"
          onClick={() =>
            change({ ...draft, groups: [...draft.groups, nuevoGrupo()] })
          }
        >
          Añadir grupo
        </button>
        <h2>Recursos</h2>
        {draft.resources.map((resource) => (
          <ResourceEditor
            key={resource.resource_id}
            resource={resource}
            groups={draft.groups}
            onChange={(value) =>
              change({
                ...draft,
                resources: draft.resources.map((r) =>
                  r.resource_id === value.resource_id ? value : r,
                ),
              })
            }
            onRemove={() =>
              change({
                ...draft,
                resources: draft.resources.filter(
                  (r) => r.resource_id !== resource.resource_id,
                ),
              })
            }
          />
        ))}
        <button type="button" onClick={addResource}>
          Añadir recurso
        </button>
        <fieldset className="form-section">
          <legend>Precio del período</legend>
          <div className="form-grid">
            <label>
              Margen %
              <input
                inputMode="decimal"
                value={draft.margin_percentage}
                onChange={(e) =>
                  change({ ...draft, margin_percentage: e.target.value })
                }
                placeholder="Usar empresa"
              />
            </label>
            <label>
              Descuento fijo USD
              <input
                inputMode="decimal"
                value={draft.discount_usd}
                onChange={(e) =>
                  change({ ...draft, discount_usd: e.target.value })
                }
              />
            </label>
            <label>
              Impuesto %
              <input
                inputMode="decimal"
                value={draft.tax_percentage}
                onChange={(e) =>
                  change({ ...draft, tax_percentage: e.target.value })
                }
                placeholder="Usar empresa"
              />
            </label>
          </div>
        </fieldset>
        <div className="form-actions">
          <button type="button" disabled={busy} onClick={() => void save()}>
            Guardar borrador
          </button>
          <button
            type="button"
            disabled={busy}
            onClick={() => void updatePreview()}
          >
            Guardar y actualizar vista previa
          </button>
        </div>
        <fieldset className="form-section">
          <legend>Descripción para Gemini</legend>
          <p>
            El texto puede contener datos personales. Revise y edite el texto
            exacto que se enviará a Gemini.
          </p>
          <label>
            TXT UTF-8
            <input
              type="file"
              accept=".txt,text/plain"
              onChange={(e) => void readTxt(e.target.files?.[0])}
            />
          </label>
          <label>
            Texto exacto
            <textarea
              rows={7}
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                setConfirmed(false);
                try {
                  localStorage.setItem(
                    `mvp-web-text-${draft.id ?? "new"}`,
                    e.target.value,
                  );
                } catch {
                  /* storage optional */
                }
              }}
            />
          </label>
          <p>{Array.from(text).length} / 50 000 puntos de código Unicode</p>
          <label className="check">
            <input
              type="checkbox"
              checked={confirmed}
              onChange={(e) => setConfirmed(e.target.checked)}
            />{" "}
            Confirmo este texto y entiendo la advertencia de datos personales.
          </label>
          <button
            type="button"
            disabled={busy || !confirmed}
            onClick={() => void analyze()}
          >
            Analizar descripción
          </button>
        </fieldset>
        {proposal && (
          <fieldset className="form-section">
            <legend>Propuesta en revisión</legend>
            <p>
              {proposal.analysis.message}
            </p>
            {proposal.review.defective_groups.map((g, i) => (
              <p key={i} className="pendientes-list">
                Grupo defectuoso: {g.defect_reasons.join("; ")}
              </p>
            ))}
            {proposal.review.revisable_groups.map((group) => (
              <div className="proposal" key={group.id}>
                <h3>{group.name}</h3>
                <label className="check">
                  <input
                    type="checkbox"
                    checked={selected.includes(group.id)}
                    onChange={(e) =>
                      setSelected(
                        e.target.checked
                          ? [...selected, group.id]
                          : selected.filter((id) => id !== group.id),
                      )
                    }
                  />{" "}
                  Seleccionar para combinar
                </label>
                <table>
                  <thead>
                    <tr>
                      <th>Atributo</th>
                      <th>Valor y condición</th>
                      <th>Respaldo</th>
                      <th>Acción</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(group.attributes).map(([name, attr]) => (
                      <tr key={name}>
                        <td>{attributeLabel(name)}</td>
                        <td>
                          {pretty(attr.value)} · {conditionLabels[attr.condition]}
                          {attr.operation && <small> · {attr.operation}</small>}
                          {attr.origin_values && (
                            <small>
                              {" "}
                              · Origen: {pretty(attr.origin_values)}
                            </small>
                          )}
                          {attr.conflicting_values && (
                            <small>
                              {" "}
                              · Conflicto: {pretty(attr.conflicting_values)}
                            </small>
                          )}
                        </td>
                        <td>{attr.source_fragment ?? "Sin respaldo"}</td>
                        <td>
                          <button
                            type="button"
                            onClick={() => {
                              setCorrection({ groupId: group.id, name, value: attr.value == null ? "" : pretty(attr.value) });
                            }}
                          >
                            Corregir
                          </button>
                          {correction?.groupId === group.id && correction.name === name && (
                            <div>
                              <label>Nuevo valor de {attributeLabel(name)}
                                <input autoFocus value={correction.value} onChange={(e) => setCorrection({ ...correction, value: e.target.value })} />
                              </label>
                              <button type="button" onClick={() => {
                                try {
                                  const new_value = parseCorrection(name, correction.value);
                                  void review("corregir", { group_id: group.id, attribute_name: name, new_value });
                                  setCorrection(null);
                                } catch (e) { setNotice(message(e)); }
                              }}>Aplicar corrección</button>
                              <button type="button" onClick={() => setCorrection(null)}>Cancelar corrección</button>
                            </div>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {group.warnings?.length > 0 && (
                  <p className="pendientes-list">{group.warnings.join("; ")}</p>
                )}
                <div className="form-actions">
                  <button
                    type="button"
                    disabled={!group.can_be_confirmed}
                    onClick={() =>
                      void review("confirmar", { group_id: group.id })
                    }
                  >
                    Confirmar grupo
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setProposalSplit({ groupId: group.id, left: "", right: "" });
                    }}
                  >
                    Separar
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      void review("descartar", { group_id: group.id })
                    }
                  >
                    Descartar
                  </button>
                </div>
                {proposalSplit?.groupId === group.id && (
                  <fieldset>
                    <legend>Separar propuesta</legend>
                    <label>Cantidad del primer grupo
                      <input inputMode="numeric" value={proposalSplit.left} onChange={(e) => setProposalSplit({ ...proposalSplit, left: e.target.value })} />
                    </label>
                    <label>Cantidad del segundo grupo
                      <input inputMode="numeric" value={proposalSplit.right} onChange={(e) => setProposalSplit({ ...proposalSplit, right: e.target.value })} />
                    </label>
                    <button type="button" onClick={() => {
                      const quantities = [Number(proposalSplit.left), Number(proposalSplit.right)];
                      if (quantities.some((value) => !Number.isInteger(value) || value <= 0)) {
                        setNotice("Las dos cantidades deben ser enteros positivos.");
                        return;
                      }
                      void review("separar", { group_id: group.id, split_quantities: quantities });
                      setProposalSplit(null);
                    }}>Aplicar separación de propuesta</button>
                    <button type="button" onClick={() => setProposalSplit(null)}>Cancelar separación de propuesta</button>
                  </fieldset>
                )}
              </div>
            ))}
            <button
              type="button"
              disabled={selected.length !== 2}
              onClick={() =>
                void review("combinar", {
                  group_id_1: selected[0],
                  group_id_2: selected[1],
                })
              }
            >
              Combinar dos seleccionados
            </button>
          </fieldset>
        )}
        <fieldset className="form-section">
          <legend>Vista previa</legend>
          {preview ? (
            <>
              <p>
                {preview.is_emission_valid
                  ? "Lista para emitir"
                  : "Pendientes de emisión"}
              </p>
              {preview.pending_emission_issues.length > 0 && (
                <ul className="pendientes-list">
                  {preview.pending_emission_issues.map((issue, i) => (
                    <li key={i}>{issue}</li>
                  ))}
                </ul>
              )}
              <PreviewDetails preview={preview} groupNames={Object.fromEntries(draft.groups.map((group) => [group.group_id, group.name]))} />
              <button
                type="button"
                disabled={!preview.is_emission_valid || busy}
                onClick={() => void issue()}
              >
                Generar PDF
              </button>
            </>
          ) : (
            <p>Guarde el borrador para ver calendario, costos y pendientes.</p>
          )}
        </fieldset>
        {latestVersion && (
          <p>
            Versión emitida: {latestVersion.code} ·{" "}
            <a href={api.pdfUrl(latestVersion.quote_id, latestVersion.code)}>
              Descargar PDF
            </a>
          </p>
        )}
        {versions.length > 0 && (
          <fieldset className="form-section">
            <legend>Versiones anteriores</legend>
            <ul>
              {versions.map((v) => (
                <li key={v.code}>
                  {v.code} · {v.issued_at} · USD {v.total} ·{" "}
                  <a href={api.pdfUrl(v.quote_id, v.code)}>Descargar PDF</a>
                </li>
              ))}
            </ul>
          </fieldset>
        )}
        <p>
          <Link to="/borradores">Ver borradores</Link> ·{" "}
          <Link to="/historial">Buscar historial</Link>
        </p>
      </fieldset>
    </section>
  );
}
