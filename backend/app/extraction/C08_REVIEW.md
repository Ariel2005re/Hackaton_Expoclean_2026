# C08 · Pruebas y revisión de la rama Gemini

Fecha: 2026-10-17. Rama: `feature/mvp-gemini`. Revisión realizada por Codex en sustitución de P2 por instrucción expresa del usuario. P2 no ha revisado esta rama.

## Ejecución reproducible

Desde la raíz de este worktree, con Python 3.12. El entorno ya está creado en esta máquina; para recrearlo se puede usar el intérprete de Python 3.12 disponible en el sistema:

```powershell
& 'C:\Users\Nelson\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m venv ..\.venv-gemini
& '..\.venv-gemini\Scripts\python.exe' -m pip install -r backend/requirements.txt
$env:PYTHONDONTWRITEBYTECODE='1'
& '..\.venv-gemini\Scripts\python.exe' -m pytest backend/tests -q -p no:cacheprovider
& '..\.venv-gemini\Scripts\python.exe' -m pip check
```

Resultado de la suite: **86 pruebas aprobadas, 0 fallos, 0 errores**. Hay una advertencia de deprecación de `starlette.testclient` al usar `httpx`; no afecta el resultado. `pip check` no detectó dependencias rotas.

## Evidencia por tarea y RF

| Tarea | RF | Evidencia observable |
| --- | --- | --- |
| C01 | RF-06, RF-30–RF-31 | Texto pegado/TXT, UTF-8, blancos, límite Unicode y emoji; texto inválido conserva su contenido y no llama a Gemini. |
| C02 | RF-06, RF-11, RF-29–RF-30 | Cliente simulado recibe solo el texto confirmado; clave oculta en representaciones, errores y respuesta del servicio; rechazo, espera y caída preservan ruta manual. |
| C03 | RF-07–RF-09, RF-29 | Respuesta mixta conserva grupos identificables y aísla defectuosos; fragmentos ajenos al texto, identificación sin respaldo y números no representables quedan fuera. |
| C04 | RF-07–RF-09 | Ausentes permanecen vacíos, derivación 280 m² ÷ 8 conserva operandos y operación, contradicciones bloquean confirmación; campos sin respaldo no se presentan como hechos. |
| C05 | RF-08–RF-10 | Corrección, combinación, separación, descarte y confirmación conservan procedencia; reanálisis no inserta ni duplica grupos confirmados. |
| C06 | RF-06, RF-09–RF-11, RF-29–RF-31 | API de análisis distingue éxito, parcial, rechazo, espera y error; rutas HTTP de revisión ejercitan las cinco operaciones sin perder estado confirmado. |
| C07 | RF-06–RF-11, RF-29–RF-31 | Escenarios españoles deterministas de varios espacios cubren explícitos, faltantes, derivación, contradicción, propuesta defectuosa y fallos del proveedor. |

## Resultado de la revisión y límites

La revisión encontró y corrigió fallos de importación, respaldo falso, cantidades truncadas, números no finitos, valores ausentes convertidos en `general`, pérdida de procedencia al combinar/separar, exposición de un error inesperado del proveedor y ausencia de rutas HTTP para revisar propuestas.

Las pruebas de Gemini son simuladas: no se hizo una llamada real al proveedor ni se probó la interfaz React o la persistencia PostgreSQL. Las rutas de revisión intercambian el estado completo con el cliente hasta que se integre el borrador persistido; esto mantiene el alcance de la rama P3.

**Desacuerdo de integración:** `backend/docs/contrato_api.md` en `origin/feature/mvp-data-api` representa la propuesta IA como `datos_extraidos` y usa estados `revisable`/`sin_respaldo` por atributo. Esta rama devuelve `revisable_groups` con estados `explicit`, `derived`, `absent`, `contradictory` y `human_corrected`, necesarios para distinguir los casos de RF-07–RF-09. Antes de integrar P1, P3 y P4 hay que acordar un adaptador o actualizar el contrato compartido conforme a la spec vigente. No se declara terminada la verificación integral de esos RF hasta esa integración.
