import { useEffect, useRef, useState } from "react";
import type { Grupo, Recurso } from "../types/borrador";

// Partition totals, never per-unit areas or hourly rates (RF-05, RF-12).
export function partitionGroup(
  group: Grupo,
  firstCount: number,
): [Grupo, Grupo] {
  const total = Number(group.units_count);
  if (!Number.isInteger(firstCount) || firstCount <= 0 || firstCount >= total)
    throw new Error(
      "Las dos cantidades deben ser enteros positivos y sumar la original.",
    );
  const first = structuredClone(group);
  const second = structuredClone(group);
  first.units_count = String(firstCount);
  second.units_count = String(total - firstCount);
  second.group_id = crypto.randomUUID();
  second.name = `${group.name} (separado)`;
  for (const kind of ["general_work", "specialized_work"] as const) {
    for (const key of [
      "adjusted_hours_per_intervention",
      "custom_surface_sqm",
    ] as const) {
      const value = group[kind][key];
      if (
        value?.trim() &&
        Number.isFinite(Number(value)) &&
        Number(value) > 0
      ) {
        const left = Number(
          ((Number(value) * firstCount) / total).toPrecision(12),
        );
        first[kind][key] = String(left);
        second[kind][key] = String(
          Number((Number(value) - left).toPrecision(12)),
        );
      }
    }
  }
  return [first, second];
}

export default function SplitGroup({
  group,
  resources,
  onApply,
  onCancel,
}: {
  group: Grupo;
  resources: Recurso[];
  onApply: (groups: [Grupo, Grupo], resources: Recurso[]) => void;
  onCancel: () => void;
}) {
  const [count, setCount] = useState(
    String(Math.floor(Number(group.units_count) / 2)),
  );
  const [allocations, setAllocations] = useState(resources.map(() => ["", ""]));
  const [error, setError] = useState("");
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current;
    if (element?.showModal) element.showModal();
    else element?.setAttribute("open", "");
    return () => element?.close?.();
  }, []);
  function apply() {
    try {
      const groups = partitionGroup(group, Number(count));
      const assigned = resources.flatMap((resource, i) => {
        const pair = allocations[i];
        if (
          !pair.some((q) => q.trim()) ||
          pair.some(
            (q) => q.trim() && (!Number.isFinite(Number(q)) || Number(q) <= 0),
          )
        )
          throw new Error(
            `Asigne una cantidad positiva de ${resource.description || "cada recurso"} a uno o ambos grupos. Deje vacío el destino que no lo usa.`,
          );
        return pair.flatMap((quantity, side) =>
          quantity.trim()
            ? [
                {
                  ...resource,
                  resource_id: crypto.randomUUID(),
                  group_id: groups[side].group_id,
                  quantity,
                },
              ]
            : [],
        );
      });
      onApply(groups, assigned);
    } catch (e) {
      setError(String(e instanceof Error ? e.message : e));
    }
  }
  return (
    <dialog ref={dialog} aria-label="Separar grupo" style={{ maxWidth: "650px", maxHeight: "85vh", overflow: "auto" }} onCancel={(e) => { e.preventDefault(); onCancel(); }}>
      <h2>Separar {group.name}</h2>
      <label>
        Espacios del primer grupo
        <input
          inputMode="numeric"
          value={count}
          onChange={(e) => setCount(e.target.value)}
        />
      </label>
      <p>
        Segundo grupo: {Number(group.units_count) - Number(count)} espacios. La
        superficie especializada y las horas ajustadas se repartirán
        proporcionalmente.
      </p>
      {resources.map((resource, i) => (
        <fieldset key={resource.resource_id}>
          <legend>{resource.description || "Recurso sin descripción"}</legend>
          <p>
            Actual: {resource.quantity} {resource.unit} por intervención · USD{" "}
            {resource.unit_cost_usd} por unidad.
          </p>
          {[0, 1].map((side) => (
            <label key={side}>
              Cantidad para grupo {side + 1}
              <input
                inputMode="decimal"
                value={allocations[i][side]}
                onChange={(e) =>
                  setAllocations(
                    allocations.map((pair, j) =>
                      j === i
                        ? pair.map((q, k) => (k === side ? e.target.value : q))
                        : pair,
                    ),
                  )
                }
              />
            </label>
          ))}
        </fieldset>
      ))}
      <p>
        Confirme el consumo de cada grupo. Los recursos compartidos seguirán
        cobrados una vez por jornada.
      </p>
      {error && <p role="alert">{error}</p>}
      <button type="button" onClick={apply}>
        Aplicar separación
      </button>
      <button type="button" onClick={onCancel}>
        Cancelar separación
      </button>
    </dialog>
  );
}
