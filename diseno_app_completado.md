# Diseño funcional y plan del MVP de cotizaciones de limpieza

## 1. Propósito y alcance

La aplicación ayuda a una empresa de limpieza a preparar cotizaciones a partir de las características de un inmueble. Un usuario interno registra al cliente y el servicio, describe los espacios manualmente o mediante texto/TXT analizado por una IA local, revisa el personal y los costos estimados, guarda el borrador y genera un PDF para el cliente.

El MVP corre localmente para un solo usuario. Termina en la generación y persistencia del PDF: **no envía cotizaciones, no registra aprobación o rechazo y no calcula traslados**. La configuración de empresa permanece separada de las cotizaciones para que, en el futuro, cada empresa pueda usar sus propias tarifas y rendimientos.

## 2. Arquitectura propuesta

- **Interfaz:** React y TypeScript para el formulario por pasos, el editor de espacios, la revisión de la IA, el cálculo, el historial y la configuración.
- **API:** FastAPI en Python para validar datos, consultar Ollama, calcular costos, guardar cotizaciones y generar PDF.
- **Persistencia:** PostgreSQL en Docker para clientes, configuración, perfiles, plantillas de insumos y herramientas, cotizaciones y versiones.
- **IA:** Ollama local en un equipo con GPU. El modelo será configurable; `qwen3:8b` es la opción inicial para evaluar extracción en español. Si Ollama no responde, el flujo manual sigue disponible.
- **Acceso:** sin inicio de sesión en el MVP. Aplicación y API disponibles solo en la máquina local.

## 3. Pantallas y flujo del usuario

### 3.1 Inicio

Mostrar **Nueva cotización**, **Borradores**, **Cotizaciones generadas**, actividad reciente y accesos a **Clientes**, **Historial** y **Configuración**. El resumen indica cantidades y valores; no muestra estados de envío o aprobación.

### 3.2 Cliente

Elegir un cliente existente o crear uno con tipo (persona natural o empresa/institución), nombre o razón social, documento de identificación, contacto, dirección del servicio, teléfono y correo. La dirección de facturación puede ser distinta. Los datos son editables mientras se trabaja en un borrador.

### 3.3 Servicio y calendario

Registrar tipo de infraestructura y de limpieza, fecha de inicio, período del precio (**semanal, quincenal o mensual**), días de servicio y ventana horaria disponible. El calendario distingue período de contrato y número de visitas. Cada grupo de espacios puede tener una frecuencia distinta de la general.

### 3.4 Crear espacios

Dos entradas producen la **misma ficha editable de grupo de espacios**:

1. **Manual:** pulsar «Añadir grupo» y completar el formulario.
2. **Con IA:** pegar una descripción o cargar un archivo `.txt` UTF-8. La API pide a Ollama una propuesta JSON. Ningún grupo entra al cálculo sin revisión del usuario.

Un grupo representa espacios iguales, por ejemplo, «8 oficinas de 35 m² cada una». Si una oficina requiere otro horario, estado, perfil o frecuencia, se separa como otro grupo.

| Dato del grupo | Uso |
| --- | --- |
| Nombre o tipo de espacio | Identificarlo en el editor y PDF. |
| Cantidad y m² por unidad | Calcular `m² físicos = cantidad × m² por unidad`. |
| Frecuencia | Visitas por día y días de servicio; calcular intervenciones del período. |
| Estado | Bueno, regular o malo; ajustar el tiempo estimado. |
| Perfil de referencia | Seleccionado por grupo; aporta un rendimiento de ejemplo editable. |
| Personal | General o especializado; determina la tarifa horaria. Se puede añadir trabajo especializado adicional. |
| Zona | Piso o sector opcional. |
| Tareas y observaciones | Texto libre para describir el alcance. |
| Fragmento de origen | Texto del que la IA obtuvo los datos, cuando corresponda. |

La IA **solo extrae datos explícitos**. Deja vacíos los atributos obligatorios ausentes y muestra advertencias; no inventa superficies, frecuencias, estados, personal ni importes. Si hay datos contradictorios, presenta los fragmentos para que el usuario resuelva el conflicto. En revisión se puede corregir, eliminar, combinar o separar grupos. Un nuevo análisis muestra otra propuesta sin duplicar automáticamente grupos ya confirmados.

Para generar PDF, cada grupo requiere **nombre, cantidad, m² por unidad, frecuencia, estado y tipo de personal**. Se puede guardar un borrador incompleto; la interfaz lista los datos pendientes. El formulario manual funciona aunque Ollama esté detenido.

### 3.5 Estimar trabajo y revisar costos

Contar visitas del período desde la fecha de inicio, los días elegidos y las repeticiones diarias de cada grupo. Mantener separados **m² físicos** e **intervenciones**.

Para la demostración, estimar horas de limpieza por visita mediante `m² físicos ÷ rendimiento de ejemplo (m² por hora de persona) × factor de estado`. Los factores iniciales, identificados como ejemplos editables, son **bueno 1,00; regular 1,25; malo 1,50**. Conservar los rendimientos SERCOP en su unidad original; no convertirlos automáticamente a horas cuando la ficha no tenga base comparable.

Sugerir personal general y especializado según horas estimadas y ventana de servicio. Permitir ajustar personas y horas por persona. Calcular costo laboral por perfil como **personas × horas por persona × visitas × tarifa horaria**. El trabajo especializado adicional puede tener horas propias por visita.

Agregar **insumos** y **herramientas extra** desde plantillas configurables. Cada línea indica descripción, cantidad, costo unitario y si corresponde a cada visita o una vez por período. Se pueden añadir, quitar y editar líneas. **No incluir traslado**.

El desglose interno muestra mano de obra general y especializada, insumos, herramientas extra, costo directo, margen, descuento fijo opcional, impuesto porcentual y total. Fórmula del MVP: `subtotal = costo directo + margen sobre el costo directo - descuento`; `impuesto = subtotal × tasa`; `total = subtotal + impuesto`. Usar USD y aritmética decimal. Si falta una tarifa, rendimiento o dato obligatorio, conservar el borrador y bloquear solo la generación del PDF, indicando qué falta.

### 3.6 Vista previa y PDF

La vista previa muestra cliente, alcance, grupos, superficie total, frecuencia, calendario, período, subtotal, impuesto y total. El PDF incluye estos datos y las condiciones de la oferta. **No revela salarios, costos unitarios internos ni margen**.

«Generar PDF» valida el borrador, recalcula los valores y guarda una **versión inmutable** con copia de datos, parámetros y PDF. Editar después abre otro borrador de versión; el PDF anterior conserva su precio. El código permanece estable y se usan identificadores como `A001 v1`, `A001 v2`.

### 3.7 Historial

Buscar por código, cliente o servicio; abrir borradores; revisar versiones; duplicar una cotización; y descargar el PDF de cada versión. El detalle muestra resumen, espacios, cálculo interno y versiones. No hay controles de envío, aprobación o rechazo.

## 4. Referencias SERCOP y configuración

Precargar cuatro perfiles de referencia:

| Perfil | Fuente |
| --- | --- |
| Limpieza de oficinas, interiores tipo I | https://portal.compraspublicas.gob.ec/sercop/wp-content/uploads/2017/01/limpiezatipoI1.pdf |
| Centros operativos en campamentos | https://portal.compraspublicas.gob.ec/sercop/wp-content/uploads/2017/04/2.pdf |
| Instituciones educativas | https://portal.compraspublicas.gob.ec/sercop/wp-content/uploads/2016/03/ficha-tecnica-limpieza-educativas.pdf |
| Áreas externas de edificaciones | https://portal.compraspublicas.gob.ec/sercop/wp-content/uploads/2023/03/4_LIMPIEZA-AREA-EXTERNA.pdf |

Cada perfil conserva el dato publicado, su unidad original, fuente y actividades u observaciones útiles. La empresa puede editar perfiles, crear otros y seleccionar uno diferente por grupo. Los precios de adhesión **no son el precio automático** de la cotización. SERCOP identifica el catálogo 2022–2025 como no vigente; por ello los perfiles se etiquetan como referencias históricas, no como tarifas actuales ni garantía de cumplimiento: https://portal.compraspublicas.gob.ec/sercop/catalogos-no-vigentes-2/

La configuración de empresa incluye identidad para PDF, tarifas horarias de personal general y especializado, rendimientos de ejemplo por perfil, factores de estado, plantillas de insumos y herramientas, margen e impuesto. Los importes precargados para demostrar el flujo son **ficticios y editables**, claramente identificados.

## 5. Persistencia y contratos entre módulos

Guardar entidades separadas para **empresa/configuración**, **cliente**, **perfil de referencia**, **plantilla de recurso**, **cotización**, **grupo de espacios**, **línea de recurso** y **versión generada**. Cada versión conserva una copia del cálculo y el PDF, para que cambios posteriores en tarifas no alteren el historial.

La API permite consultar y editar configuración y perfiles; crear y buscar clientes; crear, guardar y consultar borradores; analizar texto/TXT; calcular una vista previa; generar una versión; listar historial; y descargar PDF. El resultado de IA usa el mismo esquema de grupos que el formulario, con valores nulos y advertencias donde falte información. La validación de la API prevalece sobre la salida del modelo.

## 6. Orden de desarrollo y criterios de aceptación

1. Crear base React/FastAPI, PostgreSQL en Docker, modelos y configuración inicial con perfiles y costos de ejemplo.
2. Completar primero el camino manual: cliente → servicio → espacios → cálculo → borrador → PDF → historial y versiones.
3. Añadir extracción con Ollama y pantalla de revisión reutilizando el formulario manual.
4. Verificar cálculo con espacios de distinta frecuencia, estado y personal; los insumos y herramientas cambian el costo sin cambiar los m² físicos.
5. Probar textos en español completos, incompletos y contradictorios; comprobar que la IA no inventa datos, que la falla de Ollama no impide trabajar y que repetir el análisis no duplica grupos.
6. Comprobar que un borrador incompleto se recupera pero no genera PDF, que el documento no expone costos internos y que una versión antigua conserva sus datos y PDF tras cambiar configuración o generar otra versión.

El MVP está listo para presentarse cuando un usuario pueda recorrer tanto el camino manual como el asistido por IA, explicar cada importe desde el desglose interno y recuperar cotizaciones y PDF después de reiniciar la aplicación.
