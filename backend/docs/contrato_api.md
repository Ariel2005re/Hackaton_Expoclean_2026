# Contrato API integrado del backend

Autoridad funcional: `specs/001-hackaton/spec.md` (RF-01–RF-34). Los campos del
borrador pueden quedar vacíos. La vista previa decide si es emitible; el POST
de versiones vuelve a validar en el servidor.

## Borradores y cálculo

- `POST /cotizaciones/`: crea; `id` opcional (se genera UUID). Devuelve el borrador.
- `PUT /cotizaciones/{id}`: reemplaza el borrador editable completo.
- `GET /cotizaciones/{id}`: recupera el borrador.
- `GET /cotizaciones/`: lista todos los borradores editables con el mismo contrato, ordenados por ID; devuelve `[]` si no existen. No depende del navegador.
- `GET /cotizaciones/{id}/preview`: calendario, horas, líneas y
  `pending_emission_issues`; `is_emission_valid` controla la emisión.
- `POST /clientes/`, `GET /clientes/?nombre=...`, `GET /clientes/{id}`.
- `/config/empresa`, `/config/perfiles`, `/config/factores`, `/config/tarifas`
  y `/config/plantillas` proporcionan referencias y supuestos editables.

Ejemplo de borrador completo mínimo. Los recursos de grupo usan `scope: "grupo"`
y `group_id`; los compartidos usan `scope: "compartido"` y se cobran por jornada.
Los importes son USD. Una tarifa o rendimiento no configurados impiden emitir.

```json
{
  "id": "borr-1234",
  "cliente_id": null,
  "client": {"name": "Cliente", "service_address": "Quito, Av. 10"},
  "service": {
    "infrastructure_type": "Oficinas", "cleaning_type": "Limpieza general",
    "start_date": "2026-11-02", "period_type": "semanal",
    "start_time": "08:00:00", "end_time": "16:00:00"
  },
  "groups": [{
    "group_id": "oficinas", "name": "Oficinas", "units_count": 2,
    "sqm_per_unit": "50", "service_days": ["lunes", "miércoles"],
    "visits_per_day": 1, "state": "bueno", "profile_id": "1",
    "zone": "Planta baja", "tasks_description": "Pisos y mesas",
    "general_work": {"enabled": true, "assigned_workers": 1,
      "productivity_sqm_per_hour": "50", "hourly_rate_usd": "10"},
    "specialized_work": {"enabled": false}
  }],
  "resources": [{"resource_id": "r1", "description": "Detergente",
    "kind": "insumo", "scope": "compartido", "quantity": "0.5",
    "unit_cost_usd": "2.00", "unit": "litro"}],
  "margin_percentage": "10", "discount_usd": "1", "tax_percentage": "15"
}
```

`custom_surface_sqm` en `specialized_work` es obligatorio si está activo.
`adjusted_hours_per_intervention` y `custom_state_factor` son ajustes opcionales.
El factor pertenece al grupo y las horas ajustadas a cada trabajo. En
`group_efforts[id].general` y `.specialized` se devuelven `estimated_base_hours`,
`total_hours_per_intervention`, `assigned_workers`, `duration_hours` y
`suggested_workers`. La sugerencia es el entero superior de horas por intervención
× visitas diarias ÷ ventana diaria, mínimo uno; queda `null` sin horario válido.
Es informativa y no cambia dotación, horas ni precio. Los equipos son simultáneos.
Si tarifa, rendimiento, factor, margen o impuesto se omiten, se usa la
configuración actual de la empresa, sin modificar el borrador almacenado.

## Gemini y revisión humana

- `POST /cotizaciones/{id}/propuestas/analizar` recibe `text`, `confirmed` y
  `personal_data_warning_acknowledged`. Solo `text` confirmado se envía a
  Gemini. Devuelve `id`, `analysis` y `review`; guarda el texto aun si falla.
- `GET /cotizaciones/{id}/propuestas/{proposal_id}` recupera el estado.
- `GET /cotizaciones/{id}/propuestas/actual`: devuelve `{id, analysis, review}` de la última propuesta (mayor ID), incluso si falló el análisis; 204 si no existe propuesta, 404 si no existe la cotización. La interfaz recupera texto y revisión sin insertar grupos.
- `POST /cotizaciones/{id}/propuestas/{proposal_id}/{acción}` admite
  `corregir`, `combinar`, `separar`, `descartar`, `confirmar`.
- El cuerpo de la acción contiene, según corresponda, `group_id`,
  `attribute_name`, `new_value`, `group_id_1`, `group_id_2`, `split_quantities`.
  Solo `confirmar` incorpora el grupo al borrador. Un reanálisis crea otra
  revisión y no modifica grupos confirmados.

`review.revisable_groups[].attributes` conserva por atributo `value`,
`condition` (`explicit`, `derived`, `absent`, `contradictory`,
`human_corrected`), `source_fragment`, `operation`, `origin_values` y
`conflicting_values`. Los defectuosos se presentan aparte. El grupo
confirmado conserva `provenance` en el borrador. La ruta global `/extraction`
permite validación y revisión sin persistir; la interfaz debe usar las rutas
ligadas a cotización para no perder el estado.

El atributo de propuesta `cleaning_type` admite `general`, `especializado` y
`ambos` con respaldo explícito. Confirmar `ambos` activa ambos trabajos sin
inventar superficie especializada, perfil, rendimientos ni tarifas; esos
pendientes deben completarse antes de emitir.

## Versiones e historial

- `POST /cotizaciones/{id}/versiones` emite o devuelve una versión equivalente.
  Responde `code`, `issued_at`, `total_usd`, `pdf_url`.
- `GET /historial?query=...` busca código, cliente y servicio.
- `GET /cotizaciones/{id}/versiones/{code}/pdf` descarga los bytes guardados.

La identidad de la versión usa datos comerciales visibles y valores de cálculo;
excluye código y fecha. El PDF, la identidad y la instantánea se confirman en
una transacción. Los precios SERCOP en `/config/perfiles` llevan fuente,
valor y unidad originales; nunca se convierten automáticamente en precio final.
