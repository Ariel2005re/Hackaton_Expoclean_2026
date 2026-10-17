# E08 · Resultado de pruebas y revisión de la rama P5

Fecha: 2026-10-16. Rama: `feature/mvp-pdf-history`. Revisión realizada por Codex en sustitución de P4, por instrucción expresa del usuario. P4 no ha revisado esta rama.

## Ejecución reproducible

Desde la raíz del repositorio, con Python y las dependencias `reportlab` y `pypdf` instaladas:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
python -m unittest discover -s backend/app/documents/tests -v
```

Resultado observado: **20 pruebas, 20 correctas, 0 fallos, 0 errores** (`OK`). Se revisaron `composition.py`, `identity.py`, `issuance.py`, `history.py` y sus cuatro módulos de pruebas. La revisión encontró el fallo reproducible descrito abajo.

## Cobertura revisada

| Requisito | Escenario y resultado comprobado | Estado en esta rama |
| --- | --- | --- |
| RF-24 | El PDF abre y contiene los campos comerciales, grupos y montos esperados; los valores internos de salario, costo unitario y margen no aparecen en texto ni metadatos. | Cubierto en composición. |
| RF-25 | La emisión conserva PDF, datos visibles, precios, código y fecha; una versión anterior mantiene sus valores tras otra emisión. | Cubierto con almacenamiento simulado. |
| RF-26 | Fallos de generación, bytes sin cabecera PDF, preparación y confirmación de persistencia dejan el borrador editable sin versión. | Parcial: el hallazgo siguiente permite guardar ciertos PDF corruptos. |
| RF-27 | Tras cambiar una cotización, la versión anterior sigue accesible y descargable. | Parcial: preparar el nuevo borrador corresponde a la integración con datos/API. |
| RF-28 | Búsqueda por código, cliente y servicio; descarga del PDF exacto guardado aunque cambien los valores posteriores. | Parcial: la reapertura de borradores y el adaptador persistente corresponden a la integración. |
| RF-34 | Reintentos y cambios revertidos reutilizan código, fecha y PDF originales; cambios visibles o de precio generan otra identidad; fallos no crean versión. | Cubierto con almacenamiento simulado. |

## Límites de la revisión

Las pruebas usan un `FakeStore` transaccional; no verifican PostgreSQL, endpoints FastAPI ni recorridos de interfaz manual o asistida por IA. El adaptador real debe garantizar atomicidad, búsqueda y descarga desde almacenamiento persistente antes de declarar completos los RF-25–RF-28 y RF-34 de extremo a extremo.

### Hallazgo reproducible para corrección posterior

`EmissionService.emit` comprueba solamente que los bytes comiencen por `%PDF-`. En una prueba puntual, el generador devolvió `b'%PDF-corrupt'`: el almacenamiento simulado registró **1 versión**, pero `PdfReader(BytesIO(pdf))` lanzó `PdfStreamError` porque el documento no tiene estructura PDF válida. Esto deja un documento irrecuperable y contradice RF-26. La suite actual no cubre esa variante; antes de integrar, añadir una prueba de PDF con cabecera válida y estructura rota y validar el documento completo antes de confirmar la versión.
