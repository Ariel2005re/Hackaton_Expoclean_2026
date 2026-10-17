import { useEffect, useState } from 'react'
import {
  DIAS_SEMANA,
  ESTADOS_GRUPO,
  PERFILES_SERCOP,
  type DiaSemana,
  type EstadoGrupo,
  type Grupo,
  type PerfilSercop,
} from '../types/borrador'
import NumeroInput from './NumeroInput'

interface GrupoFormProps {
  grupoInicial: Grupo
  onGuardar: (grupo: Grupo) => void
  onCancelar: () => void
}

const ETIQUETA_PERFIL: Record<PerfilSercop, string> = {
  oficinas: 'Oficinas corporativas',
  patio_comida: 'Patio de comida',
  hospitalizacion: 'Hospitalización',
  area_critica: 'Área crítica',
}

const ETIQUETA_ESTADO: Record<EstadoGrupo, string> = {
  bueno: 'Bueno',
  regular: 'Regular',
  deteriorado: 'Deteriorado',
}

export default function GrupoForm({ grupoInicial, onGuardar, onCancelar }: GrupoFormProps) {
  const [grupo, setGrupo] = useState<Grupo>(grupoInicial)

  // Si cambian de grupo a editar (otro id), resetear el formulario.
  useEffect(() => setGrupo(grupoInicial), [grupoInicial])

  function toggleDia(dia: DiaSemana) {
    const diasSemana = grupo.diasSemana.includes(dia)
      ? grupo.diasSemana.filter((d) => d !== dia)
      : [...grupo.diasSemana, dia]
    setGrupo({ ...grupo, diasSemana })
  }

  const esValido = grupo.nombre.trim().length > 0

  return (
    <div className="form-section grupo-form">
      <label>
        Nombre del grupo
        <input
          value={grupo.nombre}
          onChange={(e) => setGrupo({ ...grupo, nombre: e.target.value })}
          placeholder="Ej. Oficinas piso 3"
        />
      </label>

      <div className="field-group horario-inputs">
        <label>
          Cantidad
          <NumeroInput
            min={1}
            valorPorDefecto={1}
            value={grupo.cantidad}
            onChange={(cantidad) => setGrupo({ ...grupo, cantidad })}
          />
        </label>
        <label>
          Superficie física (m²)
          <NumeroInput
            min={0}
            step="0.01"
            valorPorDefecto={0}
            value={grupo.superficieFisica}
            onChange={(superficieFisica) => setGrupo({ ...grupo, superficieFisica })}
          />
        </label>
        <label>
          Visitas
          <NumeroInput
            min={0}
            valorPorDefecto={0}
            value={grupo.visitas}
            onChange={(visitas) => setGrupo({ ...grupo, visitas })}
          />
        </label>
      </div>

      <div className="field-group">
        <span>Días semanales</span>
        <div className="dias-grid">
          {DIAS_SEMANA.map((dia) => (
            <label key={dia} className="dia-checkbox">
              <input
                type="checkbox"
                checked={grupo.diasSemana.includes(dia)}
                onChange={() => toggleDia(dia)}
              />
              {dia}
            </label>
          ))}
        </div>
      </div>

      <div className="field-group horario-inputs">
        <label>
          Estado
          <select
            value={grupo.estado}
            onChange={(e) => setGrupo({ ...grupo, estado: e.target.value as EstadoGrupo })}
          >
            {ESTADOS_GRUPO.map((estado) => (
              <option key={estado} value={estado}>
                {ETIQUETA_ESTADO[estado]}
              </option>
            ))}
          </select>
        </label>
        <label>
          Perfil SERCOP
          <select
            value={grupo.perfil ?? ''}
            onChange={(e) =>
              setGrupo({ ...grupo, perfil: (e.target.value || null) as PerfilSercop | null })
            }
          >
            <option value="">Selecciona...</option>
            {PERFILES_SERCOP.map((perfil) => (
              <option key={perfil} value={perfil}>
                {ETIQUETA_PERFIL[perfil]}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="trabajo-tipos">
        <fieldset className="trabajo-subseccion">
          <legend>Trabajo general</legend>
          <p className="muted trabajo-superficie-ref">
            Superficie: {grupo.superficieFisica} m² (la del grupo, arriba)
          </p>
          <div className="field-group horario-inputs">
            <label>
              Personas
              <NumeroInput
                min={0}
                valorPorDefecto={1}
                value={grupo.personasGeneral}
                onChange={(personasGeneral) => setGrupo({ ...grupo, personasGeneral })}
              />
            </label>
            <label>
              Horas
              <NumeroInput
                min={0}
                step="0.5"
                valorPorDefecto={0}
                value={grupo.horasGeneral}
                onChange={(horasGeneral) => setGrupo({ ...grupo, horasGeneral })}
              />
            </label>
          </div>
        </fieldset>

        <fieldset className="trabajo-subseccion">
          <legend>Trabajo especializado</legend>
          <div className="field-group horario-inputs">
            <label>
              Superficie especializada (m²)
              <NumeroInput
                min={0}
                step="0.01"
                valorPorDefecto={0}
                value={grupo.superficieEspecializada}
                onChange={(superficieEspecializada) =>
                  setGrupo({ ...grupo, superficieEspecializada })
                }
              />
            </label>
            <label>
              Personas
              <NumeroInput
                min={0}
                valorPorDefecto={1}
                value={grupo.personasEspecializado}
                onChange={(personasEspecializado) =>
                  setGrupo({ ...grupo, personasEspecializado })
                }
              />
            </label>
            <label>
              Horas
              <NumeroInput
                min={0}
                step="0.5"
                valorPorDefecto={0}
                value={grupo.horasEspecializado}
                onChange={(horasEspecializado) => setGrupo({ ...grupo, horasEspecializado })}
              />
            </label>
          </div>
          {grupo.superficieEspecializada === 0 && (
            <p className="pendientes-list">⚠ Falta la superficie especializada de este grupo.</p>
          )}
        </fieldset>
      </div>

      <div className="form-actions">
        <button type="button" onClick={() => onGuardar(grupo)} disabled={!esValido}>
          Guardar grupo
        </button>
        <button type="button" className="secondary" onClick={onCancelar}>
          Cancelar
        </button>
      </div>
    </div>
  )
}
