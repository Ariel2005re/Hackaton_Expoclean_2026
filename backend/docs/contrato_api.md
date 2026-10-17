# Contrato de la API - Hackathon Expo Clean 2026

Este documento define las estructuras JSON exactas que usarán el Frontend y el
Backend para comunicarse. Cubre los siete objetos del contrato de integración
acordado en `tasks.md`: borrador, grupo, trabajo, recurso, vista previa,
propuesta IA y versión. Los ejemplos son mínimos y editables; no son valores
de producción.

## Borrador (incluye grupo, trabajo y recurso)

`POST /cotizaciones/` y `GET /cotizaciones/{id}`

```json
{
  "id": "borr-1234",
  "cliente_id": 999,
  "periodo": "Mensual",
  "estado": "borrador",
  "grupos": [
    {
      "id": 1,
      "nombre": "Oficinas Principales",
      "cantidad": 1,
      "superficie_fisica": 150.0,
      "dias_semanales": 5,
      "visitas_diarias": 1,
      "estado_confirmacion": "confirmado",
      "trabajos": [
        {
          "tipo": "general",
          "superficie_usada": 150.0,
          "horas_estimadas": 4.5,
          "personas": 1
        }
      ],
      "recursos": [
        {
          "tipo": "propio",
          "id_insumo": 101,
          "cantidad": 2.5,
          "costo_unitario": 18.50
        }
      ]
    }
  ]
}
```

Un borrador admite campos vacíos: `cliente_id`, `periodo` y `grupos` pueden
omitirse o llegar vacíos y el borrador igual se guarda (RF-22).

## Vista previa

Generada por P2 (`feature/mvp-estimation`) a partir de un borrador. P1 no la
persiste; se define aquí solo como referencia de integración.

```json
{
  "cotizacion_id": "borr-1234",
  "calendario": {
    "dias_semanales": 5,
    "visitas_diarias": 1,
    "horas_totales_mes": 90.0
  },
  "lineas": [
    {
      "concepto": "Mano de obra - Oficinas Principales",
      "cantidad": 90.0,
      "unidad": "hora",
      "costo_unitario": 2.94,
      "subtotal": 264.60
    }
  ],
  "total": 264.60,
  "pendientes": [
    "Falta dirección del servicio para poder emitir el PDF"
  ]
}
```

`pendientes` es la lista de datos obligatorios que faltan para emitir un PDF
(por ejemplo nombre del cliente o dirección del servicio, ver AGENTS.md).

## Propuesta IA

Generada por P3 (`feature/mvp-gemini`) a partir de texto pegado o TXT.
Cada atributo propuesto conserva su valor, estado y el fragmento de texto
que lo respalda; los atributos sin respaldo quedan vacíos.

```json
{
  "id": 1,
  "cotizacion_id": "borr-1234",
  "estado": "revisable",
  "texto_original": "Oficina de 150 m2, limpieza 5 veces por semana...",
  "datos_extraidos": {
    "superficie_fisica": {
      "valor": 150.0,
      "estado": "revisable",
      "fragmento": "Oficina de 150 m2"
    },
    "dias_semanales": {
      "valor": 5,
      "estado": "revisable",
      "fragmento": "limpieza 5 veces por semana"
    },
    "direccion": {
      "valor": null,
      "estado": "sin_respaldo",
      "fragmento": null
    }
  }
}
```

`estado` por propuesta es `revisable`, `confirmada` o `rechazada`; por
atributo dentro de `datos_extraidos`, `revisable` o `sin_respaldo`.

## Versión (PDF inmutable)

Generada por P4 (`feature/mvp-pdf-history`) al emitir un borrador completo.

```json
{
  "id": "VER-1234-A",
  "borrador_id": "borr-1234",
  "fecha_emision": "2026-10-16T15:00:00Z",
  "pdf_url": "/pdfs/VER-1234-A.pdf",
  "total_congelado": 264.60,
  "datos_inmutables": {
    "cliente": { "nombre": "Acme Cia Ltda", "direccion": "Av. Siempre Viva 123" },
    "grupos": "... copia completa de grupos/trabajos/recursos al momento de emitir ..."
  }
}
```

`datos_inmutables` y `total_congelado` nunca cambian aunque las tarifas o
factores se editen después (RF-25 a RF-27, RF-29 a RF-31).