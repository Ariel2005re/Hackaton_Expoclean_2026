import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { HistorialItem } from "../types/borrador";

export default function Historial() {
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<HistorialItem[]>([]);
  const [error, setError] = useState("");
  useEffect(() => {
    api
      .history(query)
      .then(setItems)
      .catch((e) => setError(String(e)));
  }, [query]);
  return (
    <section>
      <h1>Historial de versiones</h1>
      <label>
        Buscar por código, cliente o servicio
        <input value={query} onChange={(e) => setQuery(e.target.value)} />
      </label>
      {error && <p role="alert">{error}</p>}
      {items.length === 0 ? (
        <p>No hay versiones para esta búsqueda.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Código</th>
              <th>Cliente</th>
              <th>Servicio</th>
              <th>Fecha</th>
              <th>Total USD</th>
              <th>Acciones</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.code}>
                <td>{item.code}</td>
                <td>{item.client}</td>
                <td>
                  {item.scope}
                  <br />
                  {item.service_address}
                </td>
                <td>{item.issued_at}</td>
                <td>{item.total}</td>
                <td>
                  <Link to={`/borradores/${item.quote_id}`}>
                    Abrir borrador
                  </Link>{" "}
                  ·{" "}
                  <a href={api.pdfUrl(item.quote_id, item.code)}>
                    Descargar PDF
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
