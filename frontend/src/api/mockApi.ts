import type { Cliente } from '../types/borrador'

// Datos de ejemplo en memoria. Sustituir por llamadas reales a
// backend/app/clientes cuando P1 exponga la ruta (A07).
let clientesSimulados: Cliente[] = [
  {
    id: 'c1',
    nombre: 'Hospital Metropolitano',
    tipo: 'juridica',
    direccion: 'Av. Mariana de Jesús, Quito',
    telefono: '022345678',
  },
  {
    id: 'c2',
    nombre: 'Centro Comercial El Bosque',
    tipo: 'juridica',
    direccion: 'Av. Occidental, Quito',
    telefono: '022998877',
  },
]

export async function buscarClientes(texto: string): Promise<Cliente[]> {
  const q = texto.trim().toLowerCase()
  if (!q) return clientesSimulados
  return clientesSimulados.filter((c) => c.nombre.toLowerCase().includes(q))
}

export async function crearCliente(
  datos: Omit<Cliente, 'id'>,
): Promise<Cliente> {
  const nuevo: Cliente = { ...datos, id: `c${clientesSimulados.length + 1}` }
  clientesSimulados = [...clientesSimulados, nuevo]
  return nuevo
}
