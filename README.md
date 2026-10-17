# Hackaton_Expoclean_2026
## Solution404

## Backend integrado (rama `integration/mvp`)

Desde la raíz del checkout de integración, ejecutar `docker compose up -d --build`.
La API queda en `http://localhost:8000/docs`; PostgreSQL se inicia
y se prepara automáticamente. Las referencias SERCOP conservan precio, unidad
y fuente originales; tarifas y rendimientos de cálculo se configuran antes
de emitir.

Contrato de borradores, propuestas, vista previa e historial:
[`backend/docs/contrato_api.md`](backend/docs/contrato_api.md). Para pruebas:
`docker compose exec -T api python -m pytest backend/tests backend/app/documents/tests -q -p no:cacheprovider`.

`feature/mvp-web` aún no incorpora la interfaz; la integración queda en esta
rama hasta completar las verificaciones I06–I10.
