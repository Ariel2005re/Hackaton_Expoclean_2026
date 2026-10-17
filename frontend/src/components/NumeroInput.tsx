import { useEffect, useState } from 'react'

interface NumeroInputProps {
  value: number
  onChange: (valor: number) => void
  min?: number
  step?: string | number
  valorPorDefecto?: number
}

/**
 * Input numérico que evita el problema de los inputs controlados con
 * type="number": mientras el usuario escribe, el texto se maneja como
 * string libre (puede quedar vacío momentáneamente). El valor numérico
 * real solo se actualiza cuando el texto es un número válido, y al salir
 * del campo (onBlur) se corrige a valorPorDefecto si quedó vacío/incompleto.
 */
export default function NumeroInput({
  value,
  onChange,
  min,
  step,
  valorPorDefecto = 0,
}: NumeroInputProps) {
  const [texto, setTexto] = useState(String(value))

  // Si el valor cambia desde afuera (ej. al cargar otro grupo para
  // editar), sincroniza el texto mostrado.
  useEffect(() => {
    setTexto(String(value))
  }, [value])

  function manejarCambio(nuevoTexto: string) {
    setTexto(nuevoTexto)
    if (nuevoTexto.trim() === '') return // permite borrar sin forzar a 0
    const numero = Number(nuevoTexto)
    if (!Number.isNaN(numero)) onChange(numero)
  }

  function manejarBlur() {
    if (texto.trim() === '' || Number.isNaN(Number(texto))) {
      setTexto(String(valorPorDefecto))
      onChange(valorPorDefecto)
    }
  }

  return (
    <input
      type="number"
      min={min}
      step={step}
      value={texto}
      onChange={(e) => manejarCambio(e.target.value)}
      onBlur={manejarBlur}
    />
  )
}
