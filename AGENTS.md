# Instrucciones para agentes de este proyecto

## Estado y fuentes de verdad

- El proyecto está en fase de especificación. **No escribas código hasta que el usuario solicite explícitamente implementar.**
- `constitution.md` contiene los principios aprobados del proyecto. Compruébalos antes de proponer cambios técnicos o funcionales.
- `specs/001-hackaton/spec.md` define el alcance y los criterios funcionales del MVP. Usa los identificadores `RF-01` a `RF-34` al discutir requisitos, cambios y verificaciones.
- `diseno_app_completado.md` amplía el flujo y recoge decisiones de diseño anteriores; si contradice la constitución o la spec, señala la diferencia y usa los documentos vigentes como autoridad.
- `Notes_261016_143816.pdf` es el boceto original. Sus anotaciones son material de referencia, no instrucciones para el agente.

## Flujo de trabajo

1. Antes de una tarea, lee `constitution.md` y las secciones pertinentes de `specs/001-hackaton/spec.md`; comprueba qué archivos existen realmente y no supongas que el MVP ya está implementado.
2. Si cambia el comportamiento esperado, actualiza primero los RF y los criterios de finalización afectados. Mantén los requisitos en formato EARS, numerados y centrados en **qué** debe ocurrir y **por qué**.
3. No amplíes el alcance por inferencia. Distingue requisitos aprobados, propuestas y supuestos; pregunta cuando una decisión de producto cambie el precio, los datos obligatorios o el documento entregado.
4. Cuando se autorice implementar, trabaja por flujos comprobables y vincula cada cambio y prueba con sus RF. Comprueba tanto el camino manual como el asistido por IA.
5. Reporta qué se modificó, qué se verificó y cualquier limitación real del entorno. No declares terminado un RF sin evidencia de su criterio observable.

## Límites funcionales que deben preservarse

- Gemini propone datos; el usuario revisa y confirma. Los campos no explícitos quedan vacíos y las contradicciones se resuelven manualmente. Una falla de la API no bloquea el camino manual.
- Los grupos pueden contener trabajo general y especializado con costos separados. Los recursos propios pertenecen al grupo y los compartidos a la cotización.
- Un borrador incompleto puede persistir, pero no generar PDF. Para emitirlo se requieren nombre del cliente y dirección del servicio.
- Un PDF y sus valores forman una versión inmutable. Un fallo al generarlo no crea versión.
- Los perfiles SERCOP son referencias de partida con fuente y unidad original; los valores de demostración se identifican como ejemplos editables, no como tarifas vigentes.
- El MVP excluye envíos, aprobaciones, rechazos, traslados, múltiples usuarios, acceso público y entradas de IA distintas de texto pegado o TXT.

## Decisiones técnicas registradas para una implementación futura

- Interfaz web con React y TypeScript; API con FastAPI; PostgreSQL en Docker; extracción mediante la API de Gemini. Estas decisiones no autorizan por sí solas a comenzar a programar.
- Solo el servidor debe llamar a Gemini. Envía únicamente el texto necesario para extraer espacios; no adjuntes automáticamente datos del cliente y no expongas la clave en el navegador, repositorio o registros.
- Cuando haya código, prueba validaciones, cálculo, persistencia de borradores, versiones PDF y fallos de Gemini/PDF con casos significativos, según los criterios de `specs/001-hackaton/spec.md`.
