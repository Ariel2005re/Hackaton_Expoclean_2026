# Constitución del proyecto

1. La especificación en `specs/001-hackaton/spec.md` define el comportamiento; todo cambio funcional debe reflejarse allí antes de implementarse.
2. El MVP usa React con TypeScript, FastAPI, PostgreSQL en Docker y la API de Gemini para la extracción de espacios.
3. La aplicación sirve a un usuario interno; no ofrece acceso público, cuentas ni colaboración multiusuario en el MVP.
4. Solo el servidor llama a Gemini; la clave permanece fuera del cliente, del repositorio y de los registros de aplicación.
5. Se envía a Gemini únicamente el texto necesario para extraer espacios; el resultado se valida y se trata como una propuesta no confiable.
6. Todo atributo propuesto por la IA debe mostrar respaldo en el texto; los ausentes quedan vacíos y los contradictorios requieren resolución humana.
7. El flujo manual funciona aunque Gemini falle o no esté disponible.
8. Tarifas, rendimientos, factores y recursos son configurables; toda cifra de demostración se identifica como ejemplo y SERCOP se presenta como referencia, no como tarifa vigente.
9. Un borrador incompleto puede guardarse, pero no generar PDF; cada PDF emitido y sus valores permanecen inmutables.
10. Cada requisito implementado tiene una verificación trazable; cálculo, validación, fallos y límites incluyen pruebas significativas.
11. Los flujos manual y asistido se prueban desde la captura hasta la persistencia y descarga del PDF.
12. El MVP excluye envío, aprobación, rechazo, pagos, traslados y lectura de archivos distintos de TXT para la IA.
