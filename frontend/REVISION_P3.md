# Revisión cruzada de P3 sobre P4 (`feature/mvp-web`)

**Fecha:** 2026-10-17  
**Base revisada:** `feature/mvp-web` `82160c9` frente al contrato de `integration/mvp` `d07b94c`  
**Alcance:** D01–D13, con atención al flujo de Gemini (RF-06–RF-11, RF-29–RF-31). Esta es una revisión técnica realizada por Codex para registrar los resultados de P3; no equivale a una aprobación personal de P3.

## Resultado

**Cambios solicitados antes de aprobar D13/I01.** La aplicación compila y sus 12 pruebas pasan, pero hay criterios observables de la spec que la interfaz todavía no cumple.

| Prioridad | Hallazgo y evidencia | RF / tarea | Corrección y prueba esperada |
| --- | --- | --- | --- |
| Alta | La confirmación del texto permanece activa después de `api.analyze`; el usuario puede pulsar **Analizar descripción** otra vez sin confirmar ese nuevo envío. `NuevaCotizacion.tsx` conserva `confirmed` en `true` y el botón solo comprueba ese estado. | RF-30, D07/D12 | Consumir la confirmación en cada intento de envío y exigir una nueva confirmación del texto exacto antes de otro análisis. Probar dos envíos consecutivos. |
| Alta | La revisión de una propuesta se pierde de la interfaz al recargar o reabrir el borrador: `proposal` solo vive en estado React. El servidor conserva la revisión y ofrece `GET /cotizaciones/{id}/propuestas/{proposal_id}`, pero la interfaz no conserva ni vuelve a consultar el ID. Un grupo pendiente deja de ser revisable aunque siga persistido. | RF-06, RF-09, RF-22; D08/D12 | Guardar el ID de la propuesta activa asociado al borrador y recuperarla al abrirlo; probar corrección y confirmación después de recargar. Para recuperación entre navegadores, acordar en integración una ruta que liste propuestas de una cotización. |
| Media | La vista previa presenta horas **por intervención**, pero no las horas laborales **acumuladas del período** por grupo y tipo. `PreviewDetails.tsx` muestra `total_hours_per_intervention` y el costo, mientras RF-18 exige ambas magnitudes visibles. | RF-18, D09 | Mostrar horas del período calculadas desde la respuesta del servidor y verificar un grupo con varias intervenciones; evitar recalcular precios en React. |
| Media | Al separar manualmente un grupo, sus recursos propios permanecen vinculados solo al grupo original; el grupo nuevo hereda trabajo y alcance, pero ninguna línea de recurso. Esto puede reducir el costo tras una separación. `splitGroup` solo modifica `groups`. | RF-05, RF-20–RF-21; D03/D05 | Definir en la interfaz qué recursos propios se copian a ambos grupos o exigir su reasignación explícita y visible; probar que la vista previa refleja la decisión. |

## Comprobaciones realizadas

- Contraste de `constitution.md`, `specs/001-hackaton/spec.md`, `backend/docs/contrato_api.md` y routers de propuestas, configuración, borradores y versiones en `integration/mvp`.
- `npm test` mediante el runtime disponible (`pnpm dlx npm@10 test`): **12/12 pruebas aprobadas**.
- `npm run build` mediante el mismo runtime: **compilación TypeScript y build Vite correctos**.
- Las pruebas de emisión y Gemini del frontend usan respuestas controladas. La aceptación de extremo a extremo con Gemini, PostgreSQL y PDF real sigue en I07–I09; RF-28 sigue limitado por la ausencia de un listado persistente de borradores en la API.

**Estado de revisión:** pendiente de correcciones y nueva comprobación. No marcar D13 ni I01 como aprobadas con este informe.
