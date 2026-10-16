# Plan de implementación del MVP de cotizaciones de limpieza

Desglose operativo por persona, rama y dependencia: [tasks.md](tasks.md).

## Base y alcance

La [constitución](constitution.md) fija el stack y los límites; la [spec](specs/001-hackaton/spec.md) define el comportamiento observable. Este plan organiza la implementación sin sustituir ningún RF. El MVP sirve a un usuario interno, con una empresa configurada, sin autenticación, envío, aprobación, pagos ni traslados. La aplicación web usa React con TypeScript, FastAPI, PostgreSQL en Docker y Gemini mediante llamadas exclusivas del servidor. Los ejemplos económicos y las referencias SERCOP se identifican como tales.

## Módulos y secuencia

| Orden | Módulo | Responsabilidad y resultado verificable | RF |
| --- | --- | --- | --- |
| 1 | Configuración y referencias | Administrar la empresa, perfiles SERCOP y propios, valor y unidad publicados, rendimientos de cálculo, tarifas horarias, factores de estado, plantillas de recursos, margen e impuesto. Precargar los cuatro perfiles y marcar los valores de demostración. | RF-14–RF-17, RF-32 |
| 2 | Clientes, servicio y borrador | Registrar o seleccionar cliente; capturar dirección, período, fecha y horario; guardar y recuperar cotizaciones incompletas. La validación de emisión se muestra como pendientes y no impide guardar. | RF-01–RF-03, RF-13, RF-22–RF-23, RF-32 |
| 3 | Grupos y recursos | Capturar los mismos grupos desde formulario o propuesta confirmada; separar grupos no equivalentes; gestionar días de la semana, visitas, estado y trabajo general o especializado. Registrar superficies y recursos propios o compartidos. | RF-04–RF-05, RF-12–RF-13, RF-20, RF-32 |
| 4 | Calendario, esfuerzo y precio | Calcular límites de período, intervenciones por grupo y jornadas distintas; estimar horas por tipo, dotación, duración diaria y costos. Aplicar líneas de costo, margen, descuento, impuesto y redondeo; mostrar desglose interno y motivos de bloqueo. | RF-03–RF-04, RF-12, RF-18–RF-21, RF-23, RF-32–RF-33 |
| 5 | Extracción asistida | Revisar el texto exacto antes de enviarlo; aceptar texto o TXT UTF-8; llamar a Gemini desde FastAPI; validar respuesta y grupos por separado. Mostrar evidencia por atributo, derivados, ausencias y contradicciones; confirmar, corregir, combinar, separar o descartar sin inserción automática. Conservar texto y captura manual ante fallos. | RF-06–RF-11, RF-29–RF-31 |
| 6 | PDF y versiones | Validar y recalcular antes de emitir; generar un PDF sin costos internos; conservar documento y valores inmutables. Fallos de generación o persistencia dejan borrador. Reintentos equivalentes reutilizan la versión; cambios relevantes generan otra. | RF-02–RF-03, RF-13, RF-21, RF-23–RF-27, RF-32, RF-34 |
| 7 | Historial | Buscar por código, cliente o servicio; reabrir borradores y descargar cada PDF anterior sin recalcularlo. | RF-25, RF-27–RF-28, RF-34 |

Cada módulo expone al siguiente datos validados con las mismas reglas que usa la generación del PDF. La interfaz distingue los valores estimados, las correcciones del usuario y los datos pendientes. La extracción asistida produce propuestas del mismo tipo de grupo que el formulario; solo la confirmación humana las incorpora al borrador.

## Modelo de datos

Los campos obligatorios para emitir pueden permanecer vacíos en un borrador. Los importes se conservan como valores decimales; los importes del PDF y el desglose siguen el redondeo de RF-21 y RF-32.

| Entidad | Datos y relaciones principales | RF |
| --- | --- | --- |
| Empresa y configuración | Identidad usada en el PDF; moneda USD; tarifas horarias general y especializada; factores bueno, regular y malo; margen e impuesto. Una empresa en el MVP, con configuración separada de las cotizaciones. | RF-16–RF-17, RF-21, RF-24–RF-25, RF-32 |
| Perfil de referencia | Empresa; nombre; origen SERCOP o propio; fuente, valor y unidad originales cuando proceda; rendimientos de cálculo editables por tipo de trabajo en m² por hora. El dato publicado permanece distinguible del supuesto de cálculo. | RF-14–RF-18 |
| Plantilla de recurso | Empresa; clase insumo o herramienta; descripción, unidad y costo unitario de ejemplo editable. Sirve para crear líneas que luego pueden ajustarse en la cotización. | RF-16–RF-17, RF-20 |
| Cliente | Nombre, datos de contacto opcionales y relación con cotizaciones. La dirección del servicio pertenece al borrador de la cotización porque puede diferir entre trabajos de un mismo cliente. | RF-01–RF-02, RF-28 |
| Cotización y borrador | Empresa, cliente opcional mientras sea borrador, código, dirección del servicio, infraestructura, tipo de limpieza, fecha de inicio, período, inicio y fin del horario, descuento y grupos. Conserva la captura editable y enlaza sus versiones emitidas. | RF-01–RF-05, RF-13, RF-21–RF-23, RF-27–RF-28 |
| Grupo de espacios | Cotización; nombre, cantidad, m² por unidad, zona y tareas opcionales, estado, perfil, conjunto de días semanales y visitas por día. Su superficie física es cantidad × m² por unidad. | RF-04–RF-05, RF-12–RF-13, RF-18, RF-33 |
| Trabajo del grupo | Grupo y tipo general o especializado; superficie atendida por intervención (física para general, propia y confirmada para especializado), rendimiento utilizado, horas estimadas y horas ajustadas por intervención, personas y tarifa horaria utilizada. Admite uno o ambos tipos. | RF-04, RF-12–RF-13, RF-18–RF-19, RF-23, RF-32 |
| Recurso de cotización | Recurso propio de un grupo o compartido por la cotización; clase, descripción, unidad, cantidad decimal positiva por intervención o jornada y costo unitario. Conserva los valores editados, independientes de cambios posteriores en la plantilla. | RF-20–RF-21, RF-32–RF-33 |
| Análisis y propuesta de IA | Cotización, texto editable confirmado, estado del análisis, grupos propuestos y advertencias. Cada atributo propuesto conserva valor, condición (explícito, derivado, ausente, contradictorio o corregido por humano), fragmento de origen y operación de derivación cuando exista. No es un grupo confirmado. | RF-06–RF-11, RF-29–RF-31 |
| Versión emitida | Cotización, número/código de versión, fecha de emisión, copia inmutable del alcance visible, parámetros y líneas que produjeron el precio, subtotal, impuesto, total, identidad de contenido comparable y PDF conservado. | RF-24–RF-28, RF-34 |

La identidad de contenido de una versión considera los datos de la cotización visibles en el PDF y todos los valores que afectan el precio. Excluye el código y la fecha propios de la versión para poder reutilizarla tras un reintento o una edición revertida. La versión guarda esos metadatos y su PDF originales.

## Decisiones y alternativas descartadas

| Decisión adoptada | Alternativa descartada | Justificación | RF |
| --- | --- | --- | --- |
| Mantener React/TypeScript, FastAPI y PostgreSQL en Docker, con una empresa y un usuario local. | Incorporar autenticación, colaboración y otra plataforma en el MVP. | Respeta la constitución y limita el trabajo a los flujos que deben demostrarse. | RF-01–RF-03, RF-16, RF-22 |
| Usar un único modelo de grupo confirmado para captura manual y asistida; mantener las propuestas de Gemini aparte hasta la confirmación. | Insertar directamente la respuesta de Gemini en la cotización. | Evita datos inventados, duplicados y conflictos no resueltos; conserva el camino manual. | RF-04–RF-13, RF-29 |
| Enviar a Gemini solo el texto revisado desde el servidor y validar cada grupo recibido. | Llamar desde el navegador o aceptar toda la respuesta como un bloque. | Protege la clave y permite revisar grupos útiles de respuestas parciales sin confiar en el proveedor. | RF-06–RF-11, RF-29–RF-31 |
| Guardar el dato SERCOP con fuente y unidad originales, separado del rendimiento y tarifa de demostración. | Convertir automáticamente las fichas en una tarifa o rendimiento horario. | Evita equiparar bases de medida distintas y presentar referencias históricas como precios vigentes. | RF-14–RF-17 |
| Calcular por grupo y tipo de trabajo, con superficie especializada propia; horas de trabajo totales independientes de la dotación. | Aplicar siempre los m² físicos a ambos trabajos o multiplicar el costo al aumentar personas. | Refleja alcances diferentes y mantiene el costo cuando solo cambia la distribución de las mismas horas. | RF-12, RF-18–RF-19 |
| Contar recursos de grupo por intervención y compartidos por jornada con servicio; redondear cada línea acumulada del período. | Cobrar todos los recursos por visita o redondear cada visita antes de agregar. | Evita duplicar recursos compartidos y fija un total reproducible. | RF-20–RF-21, RF-32–RF-33 |
| Validar la suma diaria de duraciones por grupo frente a un horario positivo del mismo día. | Validar cada visita de forma aislada o admitir turnos que crucen medianoche. | Impide emitir varias visitas que juntas no caben en la ventana definida para el MVP. | RF-03, RF-19, RF-23 |
| Conservar en PostgreSQL el PDF junto con la instantánea de la versión y confirmar ambos como una sola operación de persistencia. | Conservar solo una ruta a un archivo mutable o recalcular el PDF al descargar. | Facilita evitar versiones sin PDF y garantiza que los cambios de configuración no alteren documentos emitidos. | RF-25–RF-28, RF-34 |
| Reutilizar la versión si coinciden contenido visible y valores de precio, conservando su código y fecha. | Crear una versión en cada clic o comparar también notas internas sin efecto en la oferta. | Cumple la idempotencia y evita duplicados después de reintentos o cambios revertidos. | RF-25, RF-27, RF-34 |

## Estrategia de pruebas y aceptación

Cada caso de prueba registrará identificador, RF cubiertos, datos iniciales, acción y resultado observable. Los cálculos tendrán ejemplos con valores esperados independientes del resultado producido por la aplicación. Las pruebas de extremo a extremo usarán PostgreSQL y la descarga real del PDF; la respuesta de Gemini podrá simularse de forma determinista para comprobar éxito, respuesta parcial y fallos, y se evaluará aparte con descripciones reales en español cuando haya credencial disponible.

| Conjunto | Escenarios principales | RF |
| --- | --- | --- |
| Clientes, configuración y borradores | Seleccionar/crear cliente; guardar y recuperar borrador vacío o incompleto; editar cuatro perfiles SERCOP y uno propio; comprobar etiquetas de ejemplo y unidades originales. | RF-01–RF-02, RF-13–RF-17, RF-22, RF-28 |
| Calendario y validación | Semana, quincena, mes desde días 29–31, feriados, varios grupos y visitas; horario inválido o nocturno; suma diaria de dos visitas que excede la ventana; datos faltantes o no positivos. | RF-03–RF-05, RF-13, RF-23, RF-32–RF-33 |
| Estimación y precio | M² físicos frente a intervenciones; tres estados y factor inválido; superficies general y especializada distintas o especializada ausente; dos tipos simultáneos; cambiar personas sin cambiar costo; recursos por visita y por jornada; redondeo por línea, descuento bloqueante e impuesto. | RF-04, RF-12–RF-13, RF-18–RF-21, RF-23, RF-32–RF-33 |
| Gemini y captura manual | Evidencia por atributo, derivación 280 ÷ 8, ausencias, contradicciones, combinación, separación y reanálisis; grupo identificable frente a uno defectuoso; texto Unicode y entradas vacías o excesivas; rechazo, espera y respuesta inutilizable; completar por formulario sin Gemini. | RF-04–RF-11, RF-29–RF-31 |
| PDF, versiones e historial | Bloqueo de borrador inválido; PDF con alcance y totales sin costos internos; fallo de generación o persistencia sin versión; descarga histórica tras cambiar tarifas; reutilización después de clic repetido o cambios revertidos; nueva versión ante cambio visible o de precio; búsqueda por código, cliente y servicio. | RF-02–RF-03, RF-13, RF-21–RF-28, RF-32, RF-34 |
| Flujos completos | De cliente y captura manual a borrador, revisión, versión y descarga; repetir con texto/TXT y revisión de propuestas. Comprobar que cada RF-01–RF-34 tenga al menos una prueba trazable y resultado registrado. | RF-01–RF-34 |

La aceptación requiere que ambos flujos completos funcionen, que un borrador inválido permanezca recuperable sin PDF, que cada versión descargada conserve exactamente su contenido y precio, y que ningún PDF exponga salarios, costos unitarios internos ni margen. Los fallos de Gemini no deben impedir el flujo manual.
