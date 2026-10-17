// Tipos provisionales mientras P1 publica el contrato definitivo (A02).
// Mantener esta forma lo más cercana posible a lo que describe tasks.md
// para minimizar cambios cuando se conecte al backend real.

export type TipoCliente = 'natural' | 'juridica'

export interface Cliente {
  id?: string
  nombre: string
  tipo: TipoCliente
  direccion?: string
  telefono?: string
}

export type Periodo = 'semana' | 'quincena' | 'mes'

export const DIAS_SEMANA = [
  'lunes',
  'martes',
  'miercoles',
  'jueves',
  'viernes',
  'sabado',
  'domingo',
] as const

export type DiaSemana = (typeof DIAS_SEMANA)[number]

export interface Horario {
  dias: DiaSemana[]
  horaInicio: string // formato "HH:mm"
  horaFin: string // formato "HH:mm"
}

export interface Servicio {
  periodo: Periodo | null
  horario: Horario
}

export interface Pendiente {
  campo: string
  mensaje: string
}

// Perfiles SERCOP de ejemplo (A04). Ajustar nombres/valores cuando
// P1 publique la lista definitiva con sus factores 1,00/1,25/1,50.
export const PERFILES_SERCOP = [
  'oficinas',
  'patio_comida',
  'hospitalizacion',
  'area_critica',
] as const

export type PerfilSercop = (typeof PERFILES_SERCOP)[number]

export const ESTADOS_GRUPO = ['bueno', 'regular', 'deteriorado'] as const

export type EstadoGrupo = (typeof ESTADOS_GRUPO)[number]

export interface Grupo {
  id: string
  nombre: string
  cantidad: number
  superficieFisica: number // m² — superficie del trabajo general (D03)
  diasSemana: DiaSemana[]
  visitas: number
  estado: EstadoGrupo
  perfil: PerfilSercop | null

  // Trabajo general: reutiliza superficieFisica, con personas/horas propias.
  personasGeneral: number
  horasGeneral: number

  // Trabajo especializado: superficie propia (D04), separada de la general,
  // más personas/horas propias.
  superficieEspecializada: number
  personasEspecializado: number
  horasEspecializado: number
}

export function crearGrupoVacio(id: string): Grupo {
  return {
    id,
    nombre: '',
    cantidad: 1,
    superficieFisica: 0,
    diasSemana: [],
    visitas: 1,
    estado: 'bueno',
    perfil: null,
    personasGeneral: 1,
    horasGeneral: 0,
    superficieEspecializada: 0,
    personasEspecializado: 1,
    horasEspecializado: 0,
  }
}

export interface BorradorCotizacion {
  cliente: Cliente | null
  servicio: Servicio
  grupos: Grupo[]
}

export function crearBorradorVacio(): BorradorCotizacion {
  return {
    cliente: null,
    servicio: {
      periodo: null,
      horario: { dias: [], horaInicio: '', horaFin: '' },
    },
    grupos: [],
  }
}
