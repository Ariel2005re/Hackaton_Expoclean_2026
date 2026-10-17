# Verificación de P4 (`feature/mvp-web`)

Autoridad funcional: `constitution.md` y `specs/001-hackaton/spec.md`. El frontend usa el contrato de `integration/mvp` (`d07b94c`) mediante `/api`, con proxy Vite al puerto 8000. P4 modifica únicamente `frontend/`.

## Cobertura comprobada

| Tareas | RF | Evidencia de P4 |
| --- | --- | --- |
| D01–D03 | RF-01–RF-05, RF-13, RF-22 | Navegación, formularios de cliente/servicio y grupos; pruebas de unidades, estados, horario y separación; guardado y reapertura por ID contra API real. |
| D04–D06 | RF-12–RF-21 | Activación de cada trabajo, ajustes, recursos y configuración; compilación y consulta real de cuatro perfiles. El cálculo y las tarifas finales los valida el backend. |
| D07–D08 | RF-06–RF-11, RF-29–RF-31 | Pruebas de TXT UTF-8, límite Unicode, confirmación, respuesta parcial, contradicción, corrección y error de Gemini. Propuestas confirmadas se recuperan del borrador. |
| D09–D10 | RF-18–RF-28, RF-32–RF-34 | Pruebas de bloqueo de PDF por pendientes, emisión simulada y enlace de descarga; smoke real de vista previa incompleta. Historial usa `/historial`; la emisión real completa queda para I07. |
| D11–D12 | RF anteriores | 12 pruebas Vitest distribuidas entre captura, serialización, entrada asistida y ambos flujos de interfaz. |

Comandos verificados: `npm ci`, `npm test` (12 pruebas) y `npm run build`. En esta máquina `npm` no está en PATH; se ejecutó con `pnpm dlx npm@10`. El servidor Docker de `integration/mvp` respondió a `/api/config/perfiles` y `/api/historial`. Un borrador temporal se creó, reabrió, previsualizó y eliminó; pudo guardarse incompleto y no emitirse.

## Pendientes de aceptación

- **RF-28 / I06:** el backend no tiene `GET /cotizaciones/` para listar borradores. La vista actual recuerda IDs en el navegador; no acredita un listado persistente entre navegadores.
- **I07–I09:** falta ejecutar con integración completa los caminos manual y asistido hasta PDF real, versionado, descarga y fallos de Gemini/PDF. Las pruebas de P4 usan respuestas controladas para esos escenarios.
- **D13:** queda la revisión cruzada de P3 antes de declarar la rama lista para integración. Los RF anteriores se registran como cobertura de interfaz, no como aceptación integral del MVP.
