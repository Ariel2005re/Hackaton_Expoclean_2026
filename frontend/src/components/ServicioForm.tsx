import { DIAS_SEMANA, type DiaSemana, type Periodo, type Servicio } from '../types/borrador'

interface ServicioFormProps {
  servicio: Servicio
  onChange: (servicio: Servicio) => void
}

const HORA_INICIO_DIURNO = 6 * 60 // 06:00 en minutos
const HORA_FIN_DIURNO = 22 * 60 // 22:00 en minutos

function minutos(hora: string): number | null {
  if (!hora) return null
  const [h, m] = hora.split(':').map(Number)
  if (Number.isNaN(h) || Number.isNaN(m)) return null
  return h * 60 + m
}

export function calcularPendientesHorario(servicio: Servicio): string[] {
  const pendientes: string[] = []
  const inicio = minutos(servicio.horario.horaInicio)
  const fin = minutos(servicio.horario.horaFin)

  if (inicio === null || fin === null) {
    return pendientes // aún no hay suficiente información para evaluar
  }

  if (fin <= inicio) {
    pendientes.push('El horario tiene duración cero o negativa (hora fin debe ser mayor a hora inicio).')
  } else if (inicio < HORA_INICIO_DIURNO || fin > HORA_FIN_DIURNO) {
    pendientes.push('El horario cae fuera de la franja diurna (06:00–22:00); se marca como nocturno.')
  }

  return pendientes
}

export default function ServicioForm({ servicio, onChange }: ServicioFormProps) {
  const pendientes = calcularPendientesHorario(servicio)

  function toggleDia(dia: DiaSemana) {
    const dias = servicio.horario.dias.includes(dia)
      ? servicio.horario.dias.filter((d) => d !== dia)
      : [...servicio.horario.dias, dia]
    onChange({ ...servicio, horario: { ...servicio.horario, dias } })
  }

  return (
    <fieldset className="form-section">
      <legend>Servicio</legend>

      <label>
        Período
        <select
          value={servicio.periodo ?? ''}
          onChange={(e) =>
            onChange({ ...servicio, periodo: (e.target.value || null) as Periodo | null })
          }
        >
          <option value="">Selecciona...</option>
          <option value="semana">Semana</option>
          <option value="quincena">Quincena</option>
          <option value="mes">Mes</option>
        </select>
      </label>

      <div className="field-group">
        <span>Días de la semana</span>
        <div className="dias-grid">
          {DIAS_SEMANA.map((dia) => (
            <label key={dia} className="dia-checkbox">
              <input
                type="checkbox"
                checked={servicio.horario.dias.includes(dia)}
                onChange={() => toggleDia(dia)}
              />
              {dia}
            </label>
          ))}
        </div>
      </div>

      <div className="field-group horario-inputs">
        <label>
          Hora inicio
          <input
            type="time"
            value={servicio.horario.horaInicio}
            onChange={(e) =>
              onChange({
                ...servicio,
                horario: { ...servicio.horario, horaInicio: e.target.value },
              })
            }
          />
        </label>
        <label>
          Hora fin
          <input
            type="time"
            value={servicio.horario.horaFin}
            onChange={(e) =>
              onChange({
                ...servicio,
                horario: { ...servicio.horario, horaFin: e.target.value },
              })
            }
          />
        </label>
      </div>

      {pendientes.length > 0 && (
        <ul className="pendientes-list">
          {pendientes.map((p) => (
            <li key={p}>⚠ {p}</li>
          ))}
        </ul>
      )}
    </fieldset>
  )
}
