import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Borrador } from "../types/borrador";

export default function Borradores() {
  const [drafts, setDrafts] = useState<Borrador[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    Promise.all(
      api.localDraftIds().map((id) => api.getDraft(id).catch(() => null)),
    )
      .then((items) =>
        setDrafts(items.filter((item): item is Borrador => item !== null)),
      )
      .catch((e) => setError(String(e)));
  }, []);
  return (
    <section>
      <h1>Borradores</h1>
      <p>
        Se muestran los borradores creados en este navegador. El servidor aún no
        ofrece un listado general.
      </p>
      {error && <p role="alert">{error}</p>}
      {drafts.length === 0 ? (
        <p>No hay borradores locales.</p>
      ) : (
        <ul>
          {drafts.map((d) => (
            <li key={d.id}>
              <Link to={`/borradores/${d.id}`}>
                {d.client.name || "Sin cliente"} ·{" "}
                {d.service.cleaning_type || "Servicio por definir"} · {d.id}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
