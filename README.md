# Expoclean · MVP de cotizaciones

Aplicación local para un usuario interno: React/TypeScript, FastAPI y PostgreSQL.
Captura manual, propuestas Gemini con revisión, vista previa, borradores y
versiones PDF inmutables. Los precios se calculan en el servidor.

## Arranque local

Requisitos: Docker Desktop iniciado y Node.js con npm. Usar el checkout completo
`codex/mvp-final-validation` mientras se completan las revisiones finales. En
esta máquina está en `.worktrees/integration-mvp`.

1. Si no existe `.env`, copiar `.env.example` como `.env` en la raíz del checkout.
   Conservar un archivo existente. Configurar `GEMINI_API_KEY` para extracción
   real; vacía permite usar el camino manual. Modelo y timeout se configuran
   mediante `GEMINI_MODEL` y `GEMINI_TIMEOUT_SECONDS`.
2. Desde esa raíz, arrancar API y base:

   ```powershell
   docker compose up -d --build
   docker compose ps
   ```

   La API queda en <http://127.0.0.1:8000/docs>. Migraciones y precarga se ejecutan
   al arrancar. Repetir la precarga no sobrescribe configuración existente.

3. En otra terminal:

   ```powershell
   cd frontend
   npm ci
   npm run dev -- --host 127.0.0.1
   ```

   Abrir <http://127.0.0.1:5173>. Vite reenvía `/api` al backend. La clave solo
   pertenece al servidor; no colocarla en variables `VITE_*`. En esta máquina
   también puede ejecutarse npm con el runtime disponible: `pnpm dlx npm@10`.

4. En **Configuración**, revisar empresa, perfiles, rendimientos y tarifas.
   Rendimientos y tarifas iniciales están vacíos: introducir valores de la
   empresa o valores sintéticos para una demostración. Las referencias SERCOP
   conservan fuente y unidad original; no son precios finales vigentes.

## Recorrido de uso

1. Crear cotización, registrar o seleccionar cliente y completar dirección del
   servicio, fecha, período y horario dentro del mismo día.
2. Añadir grupos manualmente o pegar texto/cargar TXT UTF-8. Confirmar el texto
   antes de cada análisis; revisar respaldo, ausencias y contradicciones.
   Corregir, combinar, separar o descartar propuestas y confirmar las elegidas.
3. Completar cantidad, m² por unidad, calendario, visitas, estado, perfil y
   trabajos. Registrar dotación, rendimientos y tarifas. La superficie
   especializada es independiente. Añadir recursos propios o compartidos.
4. Guardar y revisar la vista previa. Los pendientes impiden emitir, pero el
   borrador incompleto se conserva y aparece en **Borradores** desde el servidor.
5. Generar y descargar PDF. **Historial** busca código, cliente o servicio y
   conserva versiones anteriores. Emitir datos equivalentes devuelve la versión
   existente, incluso después de editar y revertir cambios.

Ante un error de Gemini, texto y borrador permanecen disponibles para completar
manualmente. Una solicitud puede tardar hasta el timeout configurado.

## Pruebas

Frontend, desde `frontend/`:

```powershell
npm ci
npm test
npm run build
```

Backend con PostgreSQL aislado, desde la raíz. Un nombre de proyecto nuevo
permite comprobar una instalación vacía. No usar una base con trabajo real:

```powershell
docker compose -p mvp-tests run --build --rm -e GEMINI_API_KEY= api sh -c 'python -m backend.migrate && python -m backend.seed_data && python -m backend.seed_data && python -m pytest backend/tests backend/app/documents/tests -q -p no:cacheprovider'
docker compose -p mvp-tests stop
```

El volumen conserva los datos al detener contenedores. `docker compose down -v`
elimina ese volumen; no es necesario para el uso diario.

## Aceptación asistida repetible (I08)

`backend/tests/browser_fixture.py` sustituye únicamente la respuesta de Gemini.
La entrada normal `backend.app.main:app` no lo carga. Después de preparar la
base de pruebas anterior, ejecutar:

```powershell
docker compose -p mvp-tests up -d db
docker compose -p mvp-tests run --rm --no-deps -p 127.0.0.1:8001:8000 -e GEMINI_API_KEY= api python -m uvicorn backend.tests.browser_fixture:create_app --factory --host 0.0.0.0 --port 8000
```

En otra terminal, desde `frontend/`:

```powershell
$env:API_PROXY_TARGET='http://127.0.0.1:8001'
npm run dev -- --host 127.0.0.1 --port 5174
```

Usar exactamente `DESCRIPTION` del archivo de prueba: devuelve dos grupos
revisables (uno incompleto), un defectuoso y una contradicción. Otro texto simula
indisponibilidad. API, revisión, PostgreSQL y PDF son reales. Para volver al
backend normal: `Remove-Item Env:API_PROXY_TARGET` antes de iniciar Vite.

## Estado de entrega

- [Aceptación y evidencia](docs/ACEPTACION_MVP.md).
- [Contrato API](backend/docs/contrato_api.md).
- [Revisión técnica de P4](frontend/REVISION_P3.md).
- [Requisitos RF-01–RF-34](specs/001-hackaton/spec.md) y [tareas](tasks.md).

La candidata sigue separada de `main` hasta registrar las revisiones cruzadas
pendientes y las dos aprobaciones de integración exigidas por I10.
