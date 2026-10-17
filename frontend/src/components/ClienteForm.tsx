import { useEffect, useState } from 'react'
import type { Cliente, TipoCliente } from '../types/borrador'
import { buscarClientes, crearCliente } from '../api/mockApi'

interface ClienteFormProps {
  cliente: Cliente | null
  onChange: (cliente: Cliente | null) => void
}

export default function ClienteForm({ cliente, onChange }: ClienteFormProps) {
  const [modo, setModo] = useState<'buscar' | 'nuevo'>('buscar')
  const [texto, setTexto] = useState('')
  const [resultados, setResultados] = useState<Cliente[]>([])

  const [nombre, setNombre] = useState('')
  const [tipo, setTipo] = useState<TipoCliente>('natural')
  const [direccion, setDireccion] = useState('')
  const [telefono, setTelefono] = useState('')

  useEffect(() => {
    if (modo !== 'buscar') return
    buscarClientes(texto).then(setResultados)
  }, [texto, modo])

  async function handleCrearCliente() {
    if (!nombre.trim()) return
    const nuevo = await crearCliente({ nombre, tipo, direccion, telefono })
    onChange(nuevo)
  }

  return (
    <fieldset className="form-section">
      <legend>Cliente</legend>

      <div className="tabs">
        <button
          type="button"
          className={modo === 'buscar' ? 'active' : undefined}
          onClick={() => setModo('buscar')}
        >
          Buscar existente
        </button>
        <button
          type="button"
          className={modo === 'nuevo' ? 'active' : undefined}
          onClick={() => setModo('nuevo')}
        >
          Registrar nuevo
        </button>
      </div>

      {modo === 'buscar' && (
        <div className="field-group">
          <input
            type="text"
            placeholder="Buscar por nombre..."
            value={texto}
            onChange={(e) => setTexto(e.target.value)}
          />
          <ul className="result-list">
            {resultados.map((c) => (
              <li key={c.id}>
                <button type="button" onClick={() => onChange(c)}>
                  {c.nombre} — {c.tipo === 'natural' ? 'Persona natural' : 'Persona jurídica'}
                </button>
              </li>
            ))}
            {resultados.length === 0 && <li className="muted">Sin resultados</li>}
          </ul>
        </div>
      )}

      {modo === 'nuevo' && (
        <div className="field-group">
          <label>
            Nombre
            <input value={nombre} onChange={(e) => setNombre(e.target.value)} />
          </label>
          <label>
            Tipo
            <select value={tipo} onChange={(e) => setTipo(e.target.value as TipoCliente)}>
              <option value="natural">Persona natural</option>
              <option value="juridica">Persona jurídica</option>
            </select>
          </label>
          <label>
            Dirección
            <input value={direccion} onChange={(e) => setDireccion(e.target.value)} />
          </label>
          <label>
            Teléfono
            <input value={telefono} onChange={(e) => setTelefono(e.target.value)} />
          </label>
          <button type="button" onClick={handleCrearCliente} disabled={!nombre.trim()}>
            Usar este cliente
          </button>
        </div>
      )}

      {cliente && (
        <p className="selected-chip">
          Cliente seleccionado: <strong>{cliente.nombre}</strong>{' '}
          <button type="button" onClick={() => onChange(null)}>
            Quitar
          </button>
        </p>
      )}
    </fieldset>
  )
}
