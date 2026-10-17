# Solicitud de revisión de la candidata MVP

Base propuesta: `integration/mvp`. Rama: `codex/mvp-final-validation`.
La rama está publicada en `origin`. La creación automática de la PR fue rechazada
por el conector GitHub: HTTP 403, `Resource not accessible by integration`.
El navegador integrado solicita inicio de sesión. No se creó una PR ni se
registraron aprobaciones. Este archivo deja preparado su contenido.

## Título

MVP web integrado: flujos manual y asistido, PDF y aceptación RF-01–RF-34

## Descripción

Integra P4 con el backend, recuperación persistente de borradores y revisiones,
sugerencias de dotación, extracción de ambos trabajos y correcciones de aceptación.

### Verificación

- Backend PostgreSQL: 156 pruebas y 41 subpruebas aprobadas.
- Frontend: npm ci, 20 pruebas y npm run build correctos.
- Instalación vacía, migraciones y precarga repetida.
- Navegador: camino manual y asistido controlado hasta descarga real del PDF.
- Timeout real de Gemini seguido de finalización manual y PDF.
- Versiones anteriores inmutables, reintentos/reversión sin duplicados y rollback
  ante fallo de render o persistencia.
- Recursos repartidos explícitamente al separar, conservación de superficies y
  horas, dotación editable sin cambio de costo y configuración recuperable.

### Evidencia

Consultar `docs/ACEPTACION_MVP.md`, `frontend/REVISION_P3.md` y `output/pdf/`.
README contiene arranque y reproducción, incluido proveedor exclusivo de pruebas.

### Pendientes de aprobación

A10, B09 y D13/I01 requieren registrar las revisiones cruzadas correspondientes.
I10 exige dos revisores distintos del integrador. La revisión técnica de Codex
no se presenta como aprobación personal de P1/P3/P5. No fusionar a `main` hasta
obtener las aprobaciones y comprobar la rama final.

## Guion para los revisores

1. Seguir README en checkout limpio y registrar commit revisado y resultados.
2. Crear borrador sin grupos: debe conservarse y bloquear PDF.
3. Completar cliente, servicio, grupos, ambos trabajos y recursos; revisar
   calendario, pendientes y cálculo. Cambiar solo personas no debe cambiar costo.
4. Emitir PDF, cambiar tarifa, emitir otra versión y recuperar la anterior.
   Revertir datos debe reutilizar la versión previa sin duplicarla.
5. Recorrer I08 con respuesta parcial y contradicción; resolver, separar/combinar,
   confirmar y reanalizar. No debe haber incorporación automática ni duplicados.
6. Provocar indisponibilidad Gemini y terminar manualmente. Revisar pruebas de
   rollback PDF y matriz RF. Registrar observaciones o aprobación explícita.
