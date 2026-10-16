# Tareas del MVP para cinco personas

Derivado de [plan.md](plan.md), [spec.md](specs/001-hackaton/spec.md) y [constitution.md](constitution.md). Este documento **planifica** la implementación; no autoriza por sí solo a escribir código. Cada tarea está acotada a **15–25 minutos**. Si supera 25 minutos, se divide antes de continuar. Los identificadores de RF indican la comprobación funcional que habilita cada tarea.

## Trabajo compartido y reglas de ramas

- **Precondición verificada en G01:** esta carpeta es un checkout de Git de `Ariel2005re/Hackaton_Expoclean_2026`; `main` y `origin/main` coincidieron en el commit base indicado abajo. Nadie debe inicializar un repositorio distinto por su cuenta.
- Cada persona crea su rama desde el **mismo commit base**. Una persona modifica solo sus rutas asignadas y pruebas correspondientes. Los cambios al archivo de arranque de FastAPI, registro global de rutas y migraciones compartidas pertenecen a P1 durante integración.
- Las cinco ramas se desarrollan en paralelo. Las dependencias marcadas «integración» se satisfacen en la rama `integration/mvp` después de aprobar las pruebas de cada rama; las demás dependencias se resuelven dentro de la rama de su dueño.
- Contrato de integración: un **borrador** admite campos vacíos; un **grupo** tiene sus trabajos y recursos; una **vista previa** devuelve calendario, horas, líneas monetarias y pendientes; una **propuesta IA** conserva valor, estado y fragmento por atributo; una **versión** devuelve metadatos y PDF inmutables. P1 comparte el documento de A02 mediante una revisión visible para las otras cuatro ramas antes de que sus adaptadores dependan de él; no hace falta fusionar código antes del cierre. Las reglas de negocio siguen la spec.
- Ninguna rama se fusiona por tener solo una interfaz visible: requiere sus pruebas locales, revisión de otra persona y registro de RF comprobados. Si hay conflictos de integración, se resuelven en `integration/mvp`, se vuelven a probar y luego se hace la revisión final antes de fusionar a la rama base.

### Puerta inicial — P1

- [x] **G01 · 15 min · Dep.: ninguna · RF-01–RF-34.** Verificar checkout, remoto, rama base y commit de partida común; compartirlos con las cinco personas.
  **Hecho cuando:** `git rev-parse`, rama y remoto identifican el mismo repositorio compartido y todos conocen el commit base.
  **Referencia común para P1–P5:** repositorio `https://github.com/Ariel2005re/Hackaton_Expoclean_2026.git`; rama base `main`; commit de partida `63a1025231c004a07a22f03378bfd4590d7a64b1`. El checkout local, `origin/main` y la rama `main` del remoto coincidieron en ese commit al verificar G01.
- [x] **G02 · 15 min · Dep.: G01 · RF-01–RF-34.** Publicar este tablero y acordar las cinco ramas y las rutas de propiedad antes de empezar la implementación.
  **Hecho cuando:** las cinco personas confirman por escrito rama, rutas asignadas y dependencias; no hay dos dueños de un mismo archivo.
  **Asignación publicada:** P1 `feature/mvp-data-api` (Docker, datos, modelos, migraciones y rutas compartidas); P2 `feature/mvp-estimation` (`backend/app/estimation/`); P3 `feature/mvp-gemini` (`backend/app/extraction/`); P4 `feature/mvp-web` (`frontend/`); P5 `feature/mvp-pdf-history` (`backend/app/documents/`). Cada persona posee las pruebas de sus rutas. El inicio depende de G02 y los adaptadores del contrato A02 según cada tarea. Las confirmaciones individuales se incorporarán cuando el usuario las comparta por escrito.

## P1 — datos, configuración y API de borradores

**Rama:** `feature/mvp-data-api`. **Propiedad:** configuración Docker, `backend/app/db/`, `backend/app/models/`, rutas de clientes/configuración/borradores y sus pruebas. P1 es dueño de migraciones y registro global de rutas; los módulos ajenos se conectan durante integración. **Revisor:** P5.

- [ ] **A01 · 25 min · Dep.: G02 · RF-01, RF-16, RF-22.** Preparar arranque mínimo de FastAPI y PostgreSQL en Docker, con configuración local sin secretos versionados.
  **Hecho cuando:** la API inicia contra la base local y una comprobación de conexión pasa desde un entorno limpio.
- [ ] **A02 · 25 min · Dep.: A01 · RF-01–RF-34.** Documentar el contrato compartido de borrador, grupo, trabajo, recurso, vista previa, propuesta IA, pendientes y versión con ejemplos mínimos.
  **Hecho cuando:** P2–P5 pueden consultar el documento revisado y validar sus ejemplos contra la versión acordada para integración.
- [ ] **A03 · 25 min · Dep.: A01 · RF-14–RF-17, RF-32.** Definir persistencia de empresa, factores, tarifas, perfiles y plantillas de recursos.
  **Hecho cuando:** una migración crea esas estructuras y permite recuperar unidades y fuentes SERCOP separadas de los supuestos de cálculo.
- [ ] **A04 · 25 min · Dep.: A03 · RF-14–RF-17.** Precargar los cuatro perfiles SERCOP y factores 1,00/1,25/1,50 como ejemplos editables.
  **Hecho cuando:** una instalación vacía muestra cuatro perfiles con fuente y unidad originales, y los valores de ejemplo tienen etiqueta visible.
- [ ] **A05 · 25 min · Dep.: A01 · RF-01–RF-05, RF-13, RF-22.** Definir persistencia de cliente, cotización editable, grupo y trabajo general/especializado con campos de borrador opcionales.
  **Hecho cuando:** se puede guardar y recuperar un borrador sin cliente completo ni grupos, y otro con ambos tipos de trabajo.
- [ ] **A06 · 25 min · Dep.: A05 · RF-20, RF-25–RF-27, RF-29–RF-31.** Añadir estructuras de recursos propios/compartidos, propuestas IA y versiones con PDF y copia de valores.
  **Hecho cuando:** la migración guarda una propuesta separada de grupos confirmados y representa una versión con documento y datos inmutables.
- [ ] **A07 · 25 min · Dep.: A03, A05 · RF-01–RF-02, RF-14–RF-17.** Exponer operaciones de clientes y configuración/perfiles sin sobrescribir valores históricos de cotizaciones.
  **Hecho cuando:** crear/buscar cliente y editar configuración devuelve los valores guardados; una cotización existente conserva sus líneas editadas.
- [ ] **A08 · 25 min · Dep.: A05–A06 · RF-04–RF-05, RF-12–RF-13, RF-20, RF-22.** Exponer guardado y recuperación de cotización, grupos, trabajos y recursos, admitiendo incompletos.
  **Hecho cuando:** guardar y reabrir un borrador reproduce todos los valores y el formulario manual puede continuar sin Gemini.
- [ ] **A09 · 25 min · Dep.: A04, A07–A08 · RF-01–RF-05, RF-12–RF-17, RF-20, RF-22.** Probar persistencia con PostgreSQL para valores editables, borradores vacíos y grupos con trabajos y recursos.
  **Hecho cuando:** las pruebas recuperan exactamente los datos guardados y detectan un perfil o plantilla que pierda fuente, unidad o valores.
- [ ] **A10 · 20 min · Dep.: A09 · RF-01–RF-05, RF-12–RF-17, RF-20, RF-22.** Ejecutar pruebas de la rama, registrar RF cubiertos y abrir solicitud de revisión a P5.
  **Hecho cuando:** resultados reproducibles y observaciones de P5 quedan registrados; la rama está lista para integración.

## P2 — calendario, estimación, precio y validación

**Rama:** `feature/mvp-estimation`. **Propiedad:** `backend/app/estimation/` y sus pruebas. Trabaja con datos del contrato y dobles de persistencia; no modifica migraciones ni registro global de rutas. **Revisor:** P1.

- [ ] **B01 · 25 min · Dep.: G02 · RF-03, RF-33.** Calcular límites inclusivos de semana, quincena y mes, incluidos comienzos 29–31 y año bisiesto.
  **Hecho cuando:** ejemplos del 15 de enero al 14 de febrero y del 31 de enero a fin de febrero dan los días esperados.
- [ ] **B02 · 25 min · Dep.: B01 · RF-04, RF-20, RF-33.** Contar intervenciones por grupo y jornadas distintas con servicio, incluidos feriados y coincidencia de grupos.
  **Hecho cuando:** dos grupos el mismo día suman sus visitas, pero solo una jornada compartida.
- [ ] **B03 · 25 min · Dep.: G02 · RF-04, RF-12, RF-16, RF-18, RF-32.** Estimar m² físicos y horas por tipo con superficie especializada propia, rendimiento y factor de estado.
  **Hecho cuando:** el cálculo separa general y especializado y rechaza rendimiento, factor o superficie usada no positivos.
- [ ] **B04 · 25 min · Dep.: B02–B03 · RF-03, RF-19, RF-23.** Calcular duración con dotación por tipo y comprobar la suma de visitas diarias de cada grupo contra el horario.
  **Hecho cuando:** cambiar solo personas mantiene horas/costo, y dos visitas que juntas exceden la ventana bloquean emisión.
- [ ] **B05 · 20 min · Dep.: B02 · RF-20–RF-21, RF-33.** Calcular una línea por recurso de grupo/intervención y por recurso compartido/jornada.
  **Hecho cuando:** cantidades decimales se cobran con recurrencia correcta sin duplicar compartidos.
- [ ] **B06 · 25 min · Dep.: B03, B05 · RF-18, RF-21, RF-32.** Calcular líneas laborales por grupo y tipo y precio USD con redondeo por línea, margen, descuento e impuesto.
  **Hecho cuando:** una tabla de valores esperados reproduce costo directo, subtotal, impuesto y total al centavo.
- [ ] **B07 · 25 min · Dep.: B04, B06 · RF-02–RF-04, RF-13, RF-21, RF-23, RF-32.** Reunir pendientes de emisión sin bloquear el guardado del borrador.
  **Hecho cuando:** cliente, grupo, superficie especializada, horario, magnitudes o subtotal inválidos generan pendientes específicos y ningún PDF habilitado.
- [ ] **B08 · 25 min · Dep.: A02, B01–B07 · RF-03–RF-04, RF-12–RF-13, RF-18–RF-21, RF-23, RF-32–RF-33.** Exponer la vista previa conforme al contrato y probarla con casos límite de calendario y dinero.
  **Hecho cuando:** la respuesta incluye conteos, horas, líneas y pendientes verificables sin depender de la interfaz.
- [ ] **B09 · 20 min · Dep.: B08 · RF-03–RF-04, RF-12–RF-13, RF-18–RF-21, RF-23, RF-32–RF-33.** Ejecutar pruebas de la rama, registrar RF cubiertos y solicitar revisión a P1.
  **Hecho cuando:** las pruebas pasan y P1 confirma los resultados y el contrato de vista previa.

## P3 — extracción Gemini y revisión de propuestas

**Rama:** `feature/mvp-gemini`. **Propiedad:** `backend/app/extraction/` y sus pruebas. Usa el contrato acordado y un doble de almacenamiento hasta integración. **Revisor:** P2.

- [ ] **C01 · 20 min · Dep.: G02 · RF-06, RF-30–RF-31.** Validar texto pegado/TXT UTF-8, blancos y límite de 50 000 puntos de código Unicode sobre el texto confirmado.
  **Hecho cuando:** un emoji cuenta como un punto y blancos o exceso impiden llamar a Gemini sin perder el texto.
- [ ] **C02 · 25 min · Dep.: C01 · RF-06, RF-11, RF-29–RF-30.** Encapsular la llamada del servidor a Gemini con clave fuera de cliente y registros, control de rechazo y espera.
  **Hecho cuando:** una prueba comprueba que solo se envía texto confirmado y que la clave no aparece en salida ni errores.
- [ ] **C03 · 25 min · Dep.: A02, C02 · RF-07–RF-09, RF-29.** Validar cada grupo de la respuesta y exigir nombre o tipo con fragmento de respaldo.
  **Hecho cuando:** una respuesta mixta deja revisable el grupo identificable y señala sin incorporar el defectuoso.
- [ ] **C04 · 25 min · Dep.: C03 · RF-07–RF-09.** Representar procedencia por atributo, ausencia, contradicción y derivación de 280 m² ÷ 8 oficinas.
  **Hecho cuando:** cada valor visible tiene origen u operación y las contradicciones permanecen sin confirmar.
- [ ] **C05 · 25 min · Dep.: C04 · RF-08–RF-10.** Implementar corrección, combinación, separación, descarte y confirmación de propuestas como operaciones previas a incorporación.
  **Hecho cuando:** el respaldo por atributo sobrevive a combinar/separar y un reanálisis no duplica grupos confirmados.
- [ ] **C06 · 20 min · Dep.: C02–C05 · RF-06, RF-09–RF-11, RF-29–RF-31.** Exponer análisis y revisión conforme al contrato; conservar texto y ruta manual ante error.
  **Hecho cuando:** éxito, respuesta parcial, rechazo y espera entregan estados distinguibles sin alterar grupos confirmados.
- [ ] **C07 · 25 min · Dep.: C06 · RF-06–RF-11, RF-29–RF-31.** Probar con respuestas simuladas deterministas y descripciones españolas de varios espacios.
  **Hecho cuando:** se comprueban datos explícitos, faltantes, contradicción, grupo defectuoso, derivación y fallos de Gemini.
- [ ] **C08 · 20 min · Dep.: C07 · RF-06–RF-11, RF-29–RF-31.** Ejecutar pruebas de la rama, registrar RF cubiertos y solicitar revisión a P2.
  **Hecho cuando:** resultados reproducibles y revisión de P2 quedan registrados.

## P4 — interfaz React

**Rama:** `feature/mvp-web`. **Propiedad:** `frontend/` y sus pruebas. Puede usar respuestas simuladas del contrato mientras se completan las ramas del backend. **Revisor:** P3.

- [ ] **D01 · 20 min · Dep.: G02 · RF-01, RF-22, RF-28.** Preparar aplicación React/TypeScript y navegación entre nueva cotización, borradores, configuración e historial.
  **Hecho cuando:** cada vista abre localmente y la compilación de frontend pasa.
- [ ] **D02 · 20 min · Dep.: D01, A02 · RF-01–RF-03, RF-22.** Mostrar selección/registro de cliente y formulario de servicio con período y horario.
  **Hecho cuando:** datos incompletos se pueden conservar visualmente y horarios nocturnos o de duración cero muestran pendiente.
- [ ] **D03 · 25 min · Dep.: D02 · RF-04–RF-05, RF-13.** Añadir lista y formulario de grupos con cantidad, superficie física, días semanales, visitas, estado y perfil.
  **Hecho cuando:** se puede crear, editar, separar y quitar grupos sin perder el resto del borrador.
- [ ] **D04 · 25 min · Dep.: D03 · RF-04, RF-12–RF-13, RF-18–RF-19.** Añadir trabajo general/especializado, superficie especializada y ajuste de personas/horas.
  **Hecho cuando:** ambos trabajos muestran superficies y horas separadas y la superficie especializada faltante queda señalada.
- [ ] **D05 · 20 min · Dep.: D03 · RF-16, RF-20–RF-21.** Añadir recursos propios y compartidos con cantidad decimal, unidad y costo unitario.
  **Hecho cuando:** se distingue visualmente cobro por intervención y por jornada, y se pueden editar ambas líneas.
- [ ] **D06 · 20 min · Dep.: D01, A02 · RF-14–RF-17.** Mostrar configuración de perfiles, tarifas, rendimientos, factores y plantillas con etiquetas de ejemplo/SERCOP.
  **Hecho cuando:** se puede editar un perfil propio y los cuatro iniciales muestran fuente y unidad originales.
- [ ] **D07 · 20 min · Dep.: D01, A02 · RF-06, RF-11, RF-30–RF-31.** Mostrar carga TXT/texto, texto exacto editable, advertencia de datos personales y confirmación previa.
  **Hecho cuando:** no hay envío sin confirmación y un error conserva el texto y deja abierto el formulario manual.
- [ ] **D08 · 25 min · Dep.: D03, D07 · RF-07–RF-10, RF-29.** Mostrar grupos propuestos con respaldo por atributo y controles de corrección, combinación, separación y descarte.
  **Hecho cuando:** grupos defectuosos se distinguen de revisables y ninguno entra al borrador antes de confirmación.
- [ ] **D09 · 25 min · Dep.: D04–D05, A02 · RF-18–RF-23, RF-32–RF-33.** Mostrar vista previa con calendario, horas, líneas de costo y pendientes de emisión.
  **Hecho cuando:** los cambios en estado, personas, visitas o recursos actualizan el desglose mostrado y explican bloqueos.
- [ ] **D10 · 25 min · Dep.: D09 · RF-24–RF-28, RF-34.** Mostrar generación/descarga de PDF, versiones e historial buscable.
  **Hecho cuando:** se puede reabrir un borrador y descargar una versión anterior desde la vista.
- [ ] **D11 · 25 min · Dep.: D02–D05, D09–D10 · RF-01–RF-05, RF-12–RF-13, RF-18–RF-28, RF-32–RF-34.** Probar el flujo manual con respuestas simuladas, incluidos pendientes y versión anterior.
  **Hecho cuando:** la prueba recorre cliente → grupo → vista previa → PDF/historial y detecta un dato obligatorio ausente.
- [ ] **D12 · 25 min · Dep.: D07–D10 · RF-06–RF-11, RF-29–RF-31.** Probar el flujo asistido con respuesta parcial y fallo de Gemini simulados.
  **Hecho cuando:** la prueba exige confirmación, conserva evidencia y texto, y permite terminar manualmente tras el fallo.
- [ ] **D13 · 20 min · Dep.: D11–D12 · RF-01–RF-34.** Ejecutar pruebas y compilación de la rama, registrar RF cubiertos y solicitar revisión a P3.
  **Hecho cuando:** resultados reproducibles y revisión de P3 quedan registrados.

## P5 — PDF, versiones e historial

**Rama:** `feature/mvp-pdf-history`. **Propiedad:** `backend/app/documents/` y sus pruebas. Usa una vista previa fija y un doble de almacenamiento hasta integrar P1 y P2. **Revisor:** P4.

- [ ] **E01 · 25 min · Dep.: G02 · RF-02–RF-03, RF-24.** Crear composición de PDF desde una instantánea de ejemplo con cliente, dirección, alcance, calendario, período y totales.
  **Hecho cuando:** el PDF se abre y el texto extraído contiene los campos comerciales requeridos.
- [ ] **E02 · 20 min · Dep.: E01 · RF-21, RF-24.** Excluir salarios, costos unitarios internos y margen del documento.
  **Hecho cuando:** una prueba de contenido no encuentra esos valores ni etiquetas en el PDF.
- [ ] **E03 · 25 min · Dep.: A02, E01 · RF-25, RF-34.** Definir instantánea de datos visibles y valores de precio, excluyendo código/fecha de la comparación de equivalencia.
  **Hecho cuando:** dos entradas equivalentes dan la misma identidad y un cambio visible o de precio da otra.
- [ ] **E04 · 25 min · Dep.: E03 · RF-25–RF-27, RF-34.** Preparar servicio de emisión que conserve PDF e instantánea juntos o no cree versión ante fallo.
  **Hecho cuando:** pruebas con almacenamiento simulado cubren éxito, fallo de PDF y fallo de persistencia sin versión parcial.
- [ ] **E05 · 25 min · Dep.: E03–E04 · RF-25, RF-27, RF-34.** Reutilizar versión anterior tras clic repetido o cambios revertidos y crear otra tras cambio relevante.
  **Hecho cuando:** las pruebas conservan código, fecha y PDF del reintento y distinguen una nueva versión válida.
- [ ] **E06 · 25 min · Dep.: E04 · RF-27–RF-28.** Preparar búsqueda por código/cliente/servicio y descarga del PDF conservado, sin recálculo.
  **Hecho cuando:** una versión previa se encuentra y descarga aun si la configuración actual cambió.
- [ ] **E07 · 25 min · Dep.: E02, E05–E06 · RF-24–RF-28, RF-34.** Probar privacidad del PDF, inmutabilidad, fallos, búsqueda e idempotencia con instantáneas controladas.
  **Hecho cuando:** todas las variantes tienen resultado esperado independiente del PDF o versión generados.
- [ ] **E08 · 20 min · Dep.: E07 · RF-24–RF-28, RF-34.** Ejecutar pruebas de la rama, registrar RF cubiertos y solicitar revisión a P4.
  **Hecho cuando:** resultados reproducibles y revisión de P4 quedan registrados.

## Integración, pruebas conjuntas y fusión final

**Rama:** `integration/mvp`, creada desde el commit base. La persona que integra no modifica las ramas ajenas; cualquier corrección sustancial vuelve al dueño y a su revisión. Cada paso también dura menos de 30 minutos.

- [ ] **I01 · 20 min · Dep.: A10, B09, C08, D13, E08 · RF-01–RF-34.** Verificar que las cinco ramas tienen pruebas locales aprobadas y revisión cruzada registrada.
  **Hecho cuando:** existe una lista de resultados por rama y ningún cambio sin revisar entra en integración.
- [ ] **I02 · 25 min · Dep.: I01 · RF-01–RF-05, RF-12–RF-17, RF-20, RF-22.** Fusionar P1 y comprobar migraciones y API de borradores con PostgreSQL limpio.
  **Hecho cuando:** instalación y pruebas de datos pasan en la rama de integración.
- [ ] **I03 · 25 min · Dep.: I02 · RF-03–RF-04, RF-12–RF-13, RF-18–RF-21, RF-23, RF-32–RF-33.** Fusionar P2, conectar vista previa a borradores y repetir pruebas de cálculo/validación.
  **Hecho cuando:** la vista previa usa datos persistidos y devuelve los importes esperados.
- [ ] **I04 · 25 min · Dep.: I03 · RF-06–RF-11, RF-29–RF-31.** Fusionar P3, registrar su ruta y conservar propuestas/texto en borradores.
  **Hecho cuando:** respuesta parcial, error y confirmación funcionan sin insertar grupos automáticamente.
- [ ] **I05 · 25 min · Dep.: I04 · RF-23–RF-28, RF-34.** Fusionar P5 y conectar emisión, versiones, historial y PDF a la base y vista previa reales.
  **Hecho cuando:** un PDF se persiste y descarga; un fallo simulado no deja versión parcial.
- [ ] **I06 · 25 min · Dep.: I05 · RF-01–RF-34.** Fusionar P4 y conectar la interfaz a las operaciones integradas.
  **Hecho cuando:** frontend y backend compilan juntos y abren clientes, borradores, propuestas, vista previa e historial.
- [ ] **I07 · 25 min · Dep.: I06 · RF-01–RF-05, RF-12–RF-28, RF-32–RF-34.** Ejecutar de extremo a extremo el camino manual con PostgreSQL y descarga real del PDF.
  **Hecho cuando:** borrador incompleto bloquea PDF, cotización completa lo descarga y una versión anterior mantiene precio tras cambiar tarifa.
- [ ] **I08 · 25 min · Dep.: I06 · RF-06–RF-11, RF-29–RF-31.** Ejecutar de extremo a extremo el camino asistido con Gemini simulado y su alternativa manual ante fallo.
  **Hecho cuando:** evidencia, contradicción y respuesta parcial pasan por revisión humana y el fallo no impide emitir manualmente.
- [ ] **I09 · 25 min · Dep.: I07–I08 · RF-01–RF-34.** Revisar matriz RF → prueba, PDF de ejemplo y resultados de instalación limpia; asignar defectos a la rama dueña.
  **Hecho cuando:** RF-01–RF-34 tienen evidencia de prueba y no quedan defectos de aceptación sin resolver.
- [ ] **I10 · 20 min · Dep.: I09 · RF-01–RF-34.** Solicitar revisión final de integración a dos personas distintas del integrador y fusionar a la rama base solo tras aprobarla.
  **Hecho cuando:** revisiones, pruebas y PDF descargado constan en la solicitud de fusión; la rama base pasa las mismas comprobaciones.
