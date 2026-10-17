import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { Borrador } from "../types/borrador";

export default function Borradores() {
  const [drafts, setDrafts] = useState<Borrador[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api
      .listDrafts()
      .then(setDrafts)
      .catch((e) => setError(String(e)));
  }, []);
  return (
    <section>
      <h1>Borradores</h1>
      {error && <p role="alert">{error}</p>}
      {drafts.length === 0 ? (
        <p>No hay borradores guardados.</p>
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
