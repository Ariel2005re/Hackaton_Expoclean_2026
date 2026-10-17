import { useState } from 'react'
import ClienteForm from '../components/ClienteForm'
import ServicioForm from '../components/ServicioForm'
import GrupoList from '../components/GrupoList'
import GrupoForm from '../components/GrupoForm'
import { crearBorradorVacio, crearGrupoVacio, type Grupo } from '../types/borrador'

let siguienteIdGrupo = 1

export default function NuevaCotizacion() {
  // El borrador se conserva aquí aunque esté incompleto: no se exige
  // cliente ni horario completos para seguir editando (RF-01-03, RF-22).
  const [borrador, setBorrador] = useState(crearBorradorVacio())

  // null = formulario de grupo cerrado; si no, el grupo que se está
  // creando o editando (editar reutiliza el mismo formulario).
  const [grupoEnEdicion, setGrupoEnEdicion] = useState<Grupo | null>(null)

  function abrirNuevoGrupo() {
    setGrupoEnEdicion(crearGrupoVacio(`g${siguienteIdGrupo++}`))
  }

  function editarGrupo(id: string) {
    const grupo = borrador.grupos.find((g) => g.id === id)
    if (grupo) setGrupoEnEdicion(grupo)
  }

  function guardarGrupo(grupo: Grupo) {
    setBorrador((b) => {
      const existe = b.grupos.some((g) => g.id === grupo.id)
      const grupos = existe
        ? b.grupos.map((g) => (g.id === grupo.id ? grupo : g))
        : [...b.grupos, grupo]
      return { ...b, grupos }
    })
    setGrupoEnEdicion(null)
  }

  function quitarGrupo(id: string) {
    setBorrador((b) => ({ ...b, grupos: b.grupos.filter((g) => g.id !== id) }))
  }

  function separarEnDos(id: string) {
    setBorrador((b) => {
      const original = b.grupos.find((g) => g.id === id)
      if (!original) return b
      const copia: Grupo = {
        ...original,
        id: `g${siguienteIdGrupo++}`,
        nombre: `${original.nombre} (copia)`,
      }
      return { ...b, grupos: [...b.grupos, copia] }
    })
  }

  return (
    <section>
      <h1>Nueva cotización</h1>

      <ClienteForm
        cliente={borrador.cliente}
        onChange={(cliente) => setBorrador((b) => ({ ...b, cliente }))}
      />

      <ServicioForm
        servicio={borrador.servicio}
        onChange={(servicio) => setBorrador((b) => ({ ...b, servicio }))}
      />

      <fieldset className="form-section">
        <legend>Grupos</legend>

        <GrupoList
          grupos={borrador.grupos}
          onEditar={editarGrupo}
          onSepararEnDos={separarEnDos}
          onQuitar={quitarGrupo}
        />

        {grupoEnEdicion ? (
          <GrupoForm
            grupoInicial={grupoEnEdicion}
            onGuardar={guardarGrupo}
            onCancelar={() => setGrupoEnEdicion(null)}
          />
        ) : (
          <button type="button" onClick={abrirNuevoGrupo}>
            + Agregar grupo
          </button>
        )}
      </fieldset>

      <p className="section-note">
        Aquí irán trabajo general/especializado y recursos (D04–D05), más
        la carga asistida con Gemini (D07–D08) y la vista previa (D09).
      </p>
    </section>
  )
}
