import type { Grupo } from '../types/borrador'

interface GrupoListProps {
  grupos: Grupo[]
  onEditar: (id: string) => void
  onSepararEnDos: (id: string) => void
  onQuitar: (id: string) => void
}

export default function GrupoList({ grupos, onEditar, onSepararEnDos, onQuitar }: GrupoListProps) {
  if (grupos.length === 0) {
    return <p className="muted">Todavía no hay grupos. Agrega el primero abajo.</p>
  }

  return (
    <ul className="grupo-list">
      {grupos.map((g) => (
        <li key={g.id} className="grupo-item">
          <div>
            <strong>{g.nombre || '(sin nombre)'}</strong>
            <div className="grupo-meta">
              {g.cantidad} unidad(es) · {g.superficieFisica} m² · {g.visitas} visita(s)/período ·{' '}
              {g.diasSemana.length} día(s)/semana
              {g.perfil ? ` · ${g.perfil.replace('_', ' ')}` : ' · sin perfil'}
            </div>
            <div className="grupo-meta">
              General: {g.personasGeneral} persona(s), {g.horasGeneral} h · Especializado:{' '}
              {g.personasEspecializado} persona(s), {g.horasEspecializado} h sobre{' '}
              {g.superficieEspecializada} m²
              {g.superficieEspecializada === 0 && (
                <span className="pendiente-inline"> ⚠ sin superficie especializada</span>
              )}
            </div>
          </div>
          <div className="grupo-actions">
            <button type="button" onClick={() => onEditar(g.id)}>
              Editar
            </button>
            <button type="button" onClick={() => onSepararEnDos(g.id)}>
              Separar
            </button>
            <button type="button" className="danger" onClick={() => onQuitar(g.id)}>
              Quitar
            </button>
          </div>
        </li>
      ))}
    </ul>
  )
}
