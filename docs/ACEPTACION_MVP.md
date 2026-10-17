# Aceptación de la candidata MVP

Fecha de ejecución: 2026-10-17. Rama de trabajo: `codex/mvp-final-validation`.
Este documento distingue evidencia técnica de aprobación de entrega. No acredita
revisiones personales ni autoriza la fusión final a `main`.

## Resultado observado

- PostgreSQL en Docker: **156 pruebas y 41 subpruebas aprobadas**. Incluye pruebas
  HTTP, persistencia real, cálculos, extracción controlada y emisión PDF.
- Frontend integrado: **npm ci**, **20 pruebas** y **npm run build** correctos.
- Instalación sobre volumen nuevo `mvp-acceptance-20261017`: migración y precarga
  ejecutada dos veces; inicialmente 149 pruebas + 41 subpruebas. La ampliación
  a 151 añade fallos HTTP de render y persistencia con rollback PostgreSQL.
- Segunda instalación vacía `mvp-final-audit`: 152 + 41 aprobadas con sugerencia
  RF-19. Tras cubrir extracción de ambos trabajos y su confirmación persistida,
  la suite final pasó 156 + 41 en esa base aislada.
- Flujos manual y asistido recorridos mediante navegador con descarga real.
- Gemini real: una extracción sintética devolvió SUCCESS con un grupo revisable;
  otra solicitud desde React agotó 60 segundos. Se conservó texto/borrador y se
  terminó manualmente hasta descargar PDF. No se afirma disponibilidad continua
  del proveedor ni que las respuestas simuladas prueben su servicio externo.

Comandos de reproducción en [README](../README.md). La ejecución frontend usa
`pnpm dlx npm@10` en esta máquina por disponibilidad del runtime.

## Evidencia de navegador

### I07 · Camino manual

- Borrador `cbf5b107-74b7-42de-a97d-74a581980153`, datos sintéticos.
- Sin grupos: permite guardar, muestra pendiente y deshabilita PDF.
- Oficinas: 2 × 50 m², lunes/miércoles, una visita diaria. General:
  rendimiento 50, tarifa 10; especializado: superficie 20, rendimiento 20,
  tarifa 12. Un trabajador por tipo. Recurso compartido: 0,5 × USD 2 por jornada.
- Vista previa: 4 horas generales y 2 especializadas en el período; costos
  40 + 24 + 2 = 66; margen 10 %, impuesto 15 %; **total USD 83,49**.
- Versión `COT-3B9F06EF7F5E`; cambiar tarifa general a 12 genera
  `COT-A21E061AE1C9`, USD 93,61. El PDF anterior conserva sus bytes.
- Revertir la tarifa a 10 devuelve el primer código y no crea tercera versión.
- [PDF manual](../output/pdf/manual-v1.pdf),
  [captura de versiones](../output/evidence/manual-versions.png).
- Tras recrear el contenedor API se recuperó el mismo borrador y se descargó el
  PDF: SHA-256 idéntico a la descarga original,
  `E315C96A8025DA49A239D48BAF92FA4782E1E6D62290C472B316282326EE4B86`.

### I08 · Revisión asistida con proveedor controlado

- App en 5174, API de prueba en 8001 y PostgreSQL aislado. Solo se sustituye el
  transporte Gemini con `backend/tests/browser_fixture.py`; parser, revisión,
  guardado, cálculo y emisión son los módulos reales.
- Borrador `34d4df79-02f1-48d8-aa18-934705d47517`.
- Texto confirmado: ocho oficinas, superficie total 280 m², estados bueno/malo,
  general, lunes, una visita; bodega sin medidas; espacio sin identificación.
- UI muestra dos revisables y un defectuoso, derivación **280 ÷ 8 = 35 m²**,
  ausencias y contradicción. No inserta grupos y bloquea confirmación conflictiva.
- Recargar recupera el texto y la propuesta persistida. Corregir estado a bueno
  muestra corrección humana; descartar bodega no la incorpora.
- Separar 8 en 3 y 5 conserva origen; combinar vuelve a 8 y 280 m². Confirmar
  incorpora un grupo; perfil y parámetros de cálculo se completan manualmente.
- Reanalizar exige otra confirmación; el formulario conserva **un solo grupo**.
  Se descartan las nuevas propuestas y se emite `COT-2E6AD36BF383`, **USD 50,60**.
- Descarga desde interfaz y búsqueda por código en historial verificadas.
- [Propuesta parcial](../output/evidence/assisted-partial.png),
  [historial](../output/evidence/assisted-history.png),
  [PDF](../output/pdf/assisted-reviewed.pdf),
  [render inspeccionado](../output/evidence/assisted-pdf.png).

### RF-11 · Finalización tras fallo real

- Borrador `ce0bada8-9543-4f45-9d62-cdf2e653b325`: solicitud real agotó 60 segundos.
  Texto intacto, confirmación consumida y formulario manual disponible.
- Captura manual posterior de 2 oficinas × 35 m², lunes, rendimiento 35,
  tarifa 10: 2 horas, USD 20. Se descargó `COT-0FF7E3B620F0`.
- [PDF después del timeout](../output/pdf/manual-after-gemini-timeout.pdf).

### RF-01/RF-15/RF-22 · Clientes y perfil propio

- Registrar `Cliente de prueba I09`, buscarlo y seleccionarlo recupera nombre y
  correo, manteniendo la dirección del servicio.
- Crear `Perfil propio I09`, guardar rendimiento 80 y seleccionarlo en un grupo.
- Borrador incompleto `1643a0fc-1cb0-4254-bf92-7ad461c11c77` guarda ambos vínculos.

### RF-05/RF-19/RF-20 · Separación y ajustes con API real

- Preparación: copia por API del caso sintético manual, sin versiones, con ID
  `1d0402ff-5a0e-46a9-a882-b3dc2dda6e20`; cambios siguientes realizados en UI.
- Cambiar dotación general de 1 a 2 reduce duración de 2 a 1 hora sin cambiar
  las 4 horas del período ni USD 40 de costo general; total sigue USD 83,49.
- Ajustar horas a 4 generales y 2 especializadas por intervención y añadir
  recurso propio 0,5 × USD 4 da total USD 169,51.
- Cancelar separación conserva un grupo. Aplicar 1 + 1 espacios con asignación
  propia 0,2/0,3 conserva 100 m² físicos, 20 m² especializados, 4/2 horas ajustadas
  por intervención y el recurso compartido único. El total continúa USD 169,51.
- PDF `COT-271219AB6086` descargado:
  [documento](../output/pdf/resources-split.pdf),
  [captura](../output/evidence/resources-split.png).

### RF-16/RF-25 · Configuración completa e inmutabilidad

- En base aislada, editar empresa, margen 12 %, impuesto 15 %, rendimiento
  Oficinas 65, factor regular 1,3 y tarifas general/especializada 11/14.
- Crear plantilla de herramienta a USD 3,25, editarla a 4,25 y recargar la página:
  todos los valores reaparecen guardados; fuente/unidad SERCOP se conservan.
- Descargar la versión asistida anterior tras los cambios produce el mismo SHA-256:
  `74C15DAB439F56806B520E8F947B3E835BD432F82D7FFF8FFB01C6A5FC0CDD9E`.

## Correcciones finales de I09

- RF-19: vista previa con horas base y dotación sugerida por tipo para todas las
  visitas diarias, sin modificar lo elegido. Prueba de 3 horas × 2 visitas /
  ventana de 2 horas recomienda 3 personas; aceptar 3 habilita emisión y conserva
  costo. 3,01 horas requieren 4 personas. Sin horario válido no hay sugerencia.
  Presentación comprobada en navegador con API real.
- RF-04/RF-07/RF-12: la extracción conserva ambos trabajos con respaldo explícito,
  incluida la forma «especializada». Confirmar activa ambos sin inventar superficie
  especializada; prueba HTTP comprueba que sigue pendiente antes del PDF.
- La clave configurada no aparece en los 128 archivos revisados (versionados y
  build frontend); `.env` está ignorado. Las pruebas también comprueban errores
  sin secretos. El escaneo no equivale a revisar todo el historial Git.

## Matriz de evidencia

Las rutas de pruebas siguientes son relativas al repositorio. La existencia de
una prueba no sustituye inspeccionar su criterio observable. Las aprobaciones
personales y la fusión final se registran por separado de esta auditoría técnica.

| RF | Escenario / resultado comprobado | Evidencia |
| --- | --- | --- |
| RF-01 | Registrar, buscar y seleccionar cliente; dirección de servicio independiente. | Navegador I09; `backend/tests/test_persistencia.py`. |
| RF-02 | Borrador incompleto persiste; faltantes impiden emitir. | I07; `test_persistencia.py`, `test_estimation/test_preview.py`. |
| RF-03 | Semana/quincena/mes, ventana positiva, fin de mes. | `backend/tests/test_estimation/test_calendar.py`, `test_effort.py`; formulario I07. |
| RF-04 | Grupos con calendario, estado, perfil y ambos trabajos. | I07; `test_persistencia.py`, `frontend/src/components/Forms.test.tsx`. |
| RF-05 | Separación conserva cantidades, superficie especializada y horas; asignación explícita/cancelación de recursos. | `frontend/src/components/SplitGroup.test.tsx`; recorrido real y PDF de recursos. |
| RF-06 | Confirmación previa e incorporación solo tras revisión. | I08; `frontend/src/pages/NuevaCotizacion.test.tsx`. |
| RF-07 | Ausencias vacías, 280 ÷ 8 con operación y origen. | I08; `backend/tests/test_extraction/test_group_validator.py`. |
| RF-08 | Conflicto bloqueado hasta corrección humana. | I08; `test_extraction/test_provenance.py`. |
| RF-09 | Parcial/defectuoso, corregir, separar, combinar, descartar y confirmar con procedencia. | I08; `test_extraction/test_acceptance_gates.py`, `test_proposal_manager.py`. |
| RF-10 | Reanálisis no duplica automáticamente el grupo confirmado. | I08; `backend/tests/test_integration_flow.py`. |
| RF-11 | Timeout preserva trabajo y permite PDF manual. | Recorrido real y PDF de contingencia; `test_extraction/test_service.py`. |
| RF-12 | General/especializado usan superficies y costos distintos. | I07; `test_estimation/test_effort.py`. |
| RF-13 | Falta de grupo, superficie especializada y magnitudes bloquean PDF. | I07; `test_estimation/test_preview.py`. |
| RF-14 | Cuatro referencias visibles con fuente, valor y unidad original. | Configuración en navegador; `backend/seed_data.py`, `test_persistencia.py`. |
| RF-15 | Perfil propio creado, editado y seleccionado. | Recorrido I09 descrito arriba. |
| RF-16 | Perfil/tarifa/factor alimentan preview, sin reescribir valores editados del borrador; empresa y plantilla editadas y recuperadas. | `test_editable_company_assumptions_feed_preview_without_changing_draft`; recorrido configuración completa. |
| RF-17 | Etiquetas de ejemplo y referencia SERCOP, unidades separadas del rendimiento. | Configuración en navegador; prueba de persistencia de referencia. |
| RF-18 | Horas por tipo, intervención y período, calendario e importes. | I07/I08; `test_estimation/test_effort.py`, `PreviewDetails.test.tsx`. |
| RF-19 | Dotación reparte mismas horas; simultaneidad usa máximo; ajuste cambia cálculo; sugerencia de dotación según ventana/visitas sin cambios automáticos. | `test_estimation/test_effort.py`, `test_suggested_staff_accounts_for_visits_without_changing_price`; recorrido real y componente frontend. |
| RF-20 | Recurso propio por intervención, compartido por jornada, cantidad decimal. | `test_estimation/test_pricing.py`, `test_persistencia.py`; I07 compartido. |
| RF-21 | Tabla esperada al centavo, margen/descuento/impuesto y subtotal positivo. | `test_estimation/test_pricing.py`; I07/I08. |
| RF-22 | Guardar/recuperar incompletos y estado de revisión persistido. | I07/I08; `test_drafts_and_latest_review_can_be_reopened_without_browser_state`. |
| RF-23 | Preview válida permite emitir; duración diaria/faltantes impiden. | I07; `test_estimation/test_preview.py`. |
| RF-24 | PDF muestra alcance, calendario y total sin desglose comercial interno. | PDF manual/asistido renderizados; `backend/app/documents/tests/test_composition.py`. |
| RF-25 | Versión conserva instantánea y PDF; anterior no cambia al editar tarifa. | I07; pruebas de documentos e integración. |
| RF-26 | Fallo de render o persistencia no crea versión y conserva borrador. | `test_pdf_failures_leave_no_version_and_keep_draft`, dos variantes PostgreSQL/HTTP. |
| RF-27 | Nueva versión con cambio relevante; anterior descargable. | I07; `test_manual_draft_preview_issue_reuse_history_and_pdf`. |
| RF-28 | Lista desde servidor, reapertura e historial por código/cliente/servicio. | I07/I08; `Borradores.test.tsx`, `backend/app/documents/tests/test_history.py`. |
| RF-29 | Servidor valida por grupo; defectuoso aislado; errores no revelan clave. | I08; `test_extraction/test_acceptance_gates.py`, `test_client.py`. |
| RF-30 | Texto exacto, advertencia y confirmación consumida en cada envío. | I08; `NuevaCotizacion.test.tsx`, `test_extraction/test_client.py`. |
| RF-31 | Blancos, 50 000 puntos Unicode/emoji y TXT inválido rechazados sin llamada. | `frontend/src/api/extractionText.test.ts`, `NuevaCotizacion.test.tsx`, `test_extraction/test_validator.py`. |
| RF-32 | Validaciones y mitad hacia arriba; importes UI con dos decimales. | `test_estimation/test_pricing.py`, `test_effort.py`; I08. |
| RF-33 | Intervenciones por grupo y jornadas únicas, fechas 29–31/bisiesto. | `test_estimation/test_calendar.py`. |
| RF-34 | Reintento y reversión reutilizan versión; fallos hacen rollback. | I07; `test_integration_flow.py`, `backend/app/documents/tests/test_issuance.py`. |

## Pendientes de cierre

1. Mantener candidata, matriz y evidencias revisables. Los defectos técnicos
   encontrados durante I09 están corregidos y verificados.
2. Registrar revisiones cruzadas pendientes de A10, B09 y D13. Las revisiones
   técnicas C08/E08 realizadas por Codex constan en sus respectivos informes;
   no atribuir aprobación a personas que no la han dado.
3. Publicar candidata/solicitud de revisión cuando el acceso remoto lo permita;
   obtener las dos aprobaciones I10 y solo entonces fusionar a la rama base.
4. Actualizar este registro después de cada corrección de aceptación. No marcar
   el MVP formalmente terminado únicamente por tener suites aprobadas.

## Incidencias del entorno

- `npm ci` inicialmente falló por un `esbuild.exe` abierto por Vite. Tras detener
  las dos sesiones de desarrollo propias, instalación, 20 tests y build pasaron.
- Un intento de reconstruir Docker falló resolviendo `registry-1.docker.io`.
  El reintento terminó correctamente y se recreó la API con la imagen actualizada.
  La API se limita a `127.0.0.1:8000` conforme al uso local del MVP.
- Advertencias de deprecación de React Router y Starlette no hicieron fallar
  las suites. No se presenta este informe como auditoría de dependencias.
