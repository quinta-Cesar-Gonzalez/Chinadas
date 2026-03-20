# springboot-kafka — Puente Kafka → WebSocket

> Servicio Java/Spring Boot que actúa como bridge entre un broker Kafka externo y un servidor WebSocket. Consume mensajes de telemetría (sensores, GPS, cargas) y los reenvía en tiempo real al backend de Quinta a través de una conexión WebSocket segura y persistente.

---

## Tabla de contenidos

- [Propósito y contexto](#propósito-y-contexto)
- [Stack tecnológico](#stack-tecnológico)
- [Arquitectura general](#arquitectura-general)
- [Flujo de datos principal](#flujo-de-datos-principal)
- [Topics de Kafka](#topics-de-kafka)
- [Formato de mensajes](#formato-de-mensajes)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Componentes principales](#componentes-principales)
- [Configuración y variables clave](#configuración-y-variables-clave)
- [Seguridad y autenticación](#seguridad-y-autenticación)
- [Logging](#logging)
- [Tests](#tests)
- [Deuda técnica](#deuda-técnica)
- [Servicios relacionados](#servicios-relacionados)

---

## Propósito y contexto

Este servicio actúa como **puente (bridge)** entre la infraestructura de mensajería Kafka y el servidor WebSocket de Quinta (`iot.quinta.tech`). Su responsabilidad es:

1. **Consumir** mensajes publicados en topics de Kafka por dispositivos IoT (sensores de llantas, GPS, sensores de carga).
2. **Transformar** el mensaje: envolverlo en un JSON estándar con `topic` y `payload`.
3. **Reenviar** el mensaje transformado vía WebSocket al servidor central, que distribuye la data en tiempo real a los clientes conectados.

El servicio es parte del ecosistema IoT de **Quinta (org_id: 218)** y opera sobre mensajes de telemetría de flota vehicular.

---

## Stack tecnológico

| Capa | Tecnología | Versión |
|---|---|---|
| Lenguaje | Java | 17+ (Spring Boot managed) |
| Framework | Spring Boot | 2.7.5 |
| Mensajería | Apache Kafka + Spring Kafka | Spring managed |
| WebSocket (cliente) | Java-WebSocket (TooTallNate) | 1.5.3 |
| JSON | org.json | 20230227 |
| Reducción de boilerplate | Lombok | 1.18.30 |
| Logging | SLF4J + Logback (Spring Boot Starter Logging) | Spring managed |
| Build | Maven | — |
| Tests | JUnit 5 + Spring Boot Test + spring-kafka-test | Spring managed |

---

## Arquitectura general

```
┌─────────────────────────┐         SASL/SCRAM-SHA-512         ┌──────────────────────┐
│   Broker Kafka externo  │ ◄────────────────────────────────── │  springboot-kafka    │
│   101.132.76.195:9092   │  topics: topic-sensor-218           │  (este servicio)     │
│                         │          topic-gps-218              │                      │
│  Productores IoT:       │          topic-load-218             │  KafkaConsumer       │
│  - Dispositivos sensor  │ ──────────────────────────────────► │       │              │
│  - Dispositivos GPS     │          mensajes JSON              │       ▼              │
│  - Sensores de carga    │                                     │  processAndSend()    │
└─────────────────────────┘                                     │       │              │
                                                                │       ▼              │
                                                                │  WebSocketClient     │
                                                                │       │              │
                                                                └───────│──────────────┘
                                                                        │ WSS (TLS)
                                                                        ▼
                                                               ┌──────────────────────┐
                                                               │ wss://iot.quinta.tech │
                                                               │       /ws/java        │
                                                               │                      │
                                                               │  Servidor WebSocket  │
                                                               │  del backend Quinta  │
                                                               └──────────────────────┘
```

---

## Flujo de datos principal

```
1. El KafkaConsumer recibe un ConsumerRecord de cualquiera de los 3 topics.
2. Extrae el topic de Kafka y el payload (String JSON).
3. Llama a mapKafkaTopicToWebSocketTopic() para traducir el topic:
   - "topic-gps-218"    → "gps"
   - "topic-sensor-218" → "sensor"
   - "topic-load-218"   → "load"
4. Construye un nuevo JSONObject:
   {
     "topic":   "<webSocketTopic>",
     "payload": { ...datos originales del dispositivo... }
   }
5. Llama a WebSocketClientService.sendMessage() que envía el string por la conexión WSS activa.
6. Si el WebSocket está desconectado, el mensaje se descarta (con log WARN).
```

---

## Topics de Kafka

| Topic Kafka | Alias WebSocket | Tipo de datos |
|---|---|---|
| `topic-sensor-218` | `sensor` | Telemetría de sensores de llantas (presión, temperatura, etc.) |
| `topic-gps-218` | `gps` | Posición geográfica de unidades (lat, lng, velocidad, etc.) |
| `topic-load-218` | `load` | Datos de sensores de carga de vehículo |
| `test` | _(sólo productor de prueba)_ | Mensajes de desarrollo/testing |

> **Nota:** El sufijo `-218` corresponde al `org_id` de Quinta en el broker Kafka compartido.

---

## Formato de mensajes

### Mensaje recibido de Kafka (entrada)

El valor de cada `ConsumerRecord` es un JSON en string. El schema exacto depende del tipo de topic, pero el servicio lo trata como un JSON genérico sin validación de schema.

### Mensaje enviado al WebSocket (salida)

El servicio envuelve siempre el payload original en el siguiente envelope:

```json
{
  "topic": "sensor" | "gps" | "load",
  "payload": {
    // Contenido original del mensaje Kafka, sin modificaciones
  }
}
```

---

## Estructura del proyecto

```
Chinadas/
├── pom.xml                                    # Dependencias Maven
├── src/
│   ├── main/
│   │   ├── java/com/springboot/whw/springboot_kafka/
│   │   │   ├── SpringbootKafkaApplication.java        # Entry point (@SpringBootApplication)
│   │   │   ├── kafka/
│   │   │   │   ├── MQTopic.java                       # Constantes de topics Kafka
│   │   │   │   ├── KafkaSendResultHandler.java        # Callback global de envíos Kafka
│   │   │   │   ├── consumer/
│   │   │   │   │   └── KafkaConsumer.java             # Consumidor y bridge principal
│   │   │   │   └── producer/
│   │   │   │       └── KafkaProducer.java             # Productor REST (uso en pruebas)
│   │   │   └── websocket/
│   │   │       └── WebSocketClientService.java        # Cliente WebSocket con reconexión
│   │   └── resources/
│   │       └── application.properties                 # Configuración Kafka y credenciales
│   └── test/
│       └── java/com/springboot/whw/springboot_kafka/
│           ├── KafkaListenerTest.java                 # Test del callback de productor
│           └── SpringbootKafkaApplicationTests.java   # Test de carga del contexto Spring
```

---

## Componentes principales

### `KafkaConsumer`

- **Paquete:** `kafka.consumer`
- **Anotación:** `@KafkaListener(topics = {TOPIC_SENSOR, TOPIC_GPS, TOPIC_LOAD})`
- **Responsabilidad:** Escucha los 3 topics simultáneamente. Por cada mensaje, mapea el topic Kafka a su alias WebSocket, arma el JSON envelope y delega el envío a `WebSocketClientService`.
- **Comportamiento ante error de mapeo:** Log `WARN` y descarte del mensaje (no hay DLQ).
- **Comportamiento ante error de envío WebSocket:** Log `ERROR` con stacktrace completo.

### `WebSocketClientService`

- **Paquete:** `websocket`
- **Tipo:** `@Service`, inicializado con `@PostConstruct`
- **URL destino (hardcoded):** `wss://iot.quinta.tech/ws/java`
- **Reconexión automática:** Si la conexión se cierra inesperadamente, programa un `TimerTask` que intenta reconectar cada **5 segundos** vía `reconnectBlocking()`.
- **Comportamiento si no hay conexión:** Log `WARN` y descarte del mensaje (sin cola de buffer).

### `KafkaProducer`

- **Paquete:** `kafka.producer`
- **Tipo:** `@RestController` en `/kafka/producer`
- **Uso:** Utilidad de prueba/debugging. Expone endpoints HTTP para publicar mensajes al topic `test`.

| Endpoint | Propósito |
|---|---|
| `GET /kafka/producer/send?message=X` | Envío simple al topic `test` |
| `GET /kafka/producer/send/callback?message=X` | Envío con callback lambda |
| `GET /kafka/producer/send/future/callback?message=X` | Envío con `ListenableFutureCallback` |

### `MQTopic`

- Interface de constantes con los nombres de los topics Kafka:
  - `TEST = "test"`
  - `TOPIC_SENSOR = "topic-sensor-218"`
  - `TOPIC_GPS = "topic-gps-218"`
  - `TOPIC_LOAD = "topic-load-218"`

### `KafkaSendResultHandler`

- Implementa `ProducerListener` de Spring Kafka.
- Registra log `INFO` tanto en éxito como en error de envío de mensajes producidos.

---

## Configuración y variables clave

Las configuraciones actuales están definidas en `application.properties`. **Las credenciales están en texto plano — ver sección Deuda Técnica.**

| Propiedad | Valor actual | Descripción |
|---|---|---|
| `spring.kafka.bootstrap-servers` | `101.132.76.195:9092` | Dirección del broker Kafka |
| `spring.kafka.properties.security.protocol` | `SASL_PLAINTEXT` | Protocolo de seguridad |
| `spring.kafka.properties.sasl.mechanism` | `SCRAM-SHA-512` | Mecanismo de autenticación |
| `spring.kafka.properties.sasl.jaas.config` | *(contiene user/pass)* | Credenciales JAAS para Kafka |
| `spring.kafka.consumer.properties.group.id` | `sxArk415VtJojnez2LXPrg` | Consumer group activo |
| `spring.kafka.consumer.enable-auto-commit` | `true` | Commit automático de offsets |
| `spring.kafka.consumer.auto.commit.interval.ms` | `1000` | Intervalo de commit (ms) |
| `spring.kafka.consumer.auto-offset-reset` | `latest` | Solo consume mensajes nuevos al arrancar |
| `spring.kafka.consumer.properties.session.timeout.ms` | `120000` | Timeout de sesión consumer (2 min) |
| `spring.kafka.consumer.properties.request.timeout.ms` | `180000` | Timeout de request consumer (3 min) |
| `spring.kafka.listener.missing-topics-fatal` | `false` | No falla si el topic no existe al arrancar |

### Consumer groups disponibles (Quinta org)

El archivo de configuración documenta los grupos de consumidores autorizados para el usuario `fDlOyN218`:

- `sxArk415VtJojnez2LXPrg` ← **activo actualmente**
- `LvjvcCokBbJGzphbSNKrGR`
- `jByMeaZrLOPOovpipHs2AW`
- `J4idf66ORTwdNBcD93HSC6`

---

## Seguridad y autenticación

### Kafka → Servicio
- **Protocolo:** `SASL_PLAINTEXT` (sin TLS en la capa de transporte hacia Kafka)
- **Mecanismo SASL:** `SCRAM-SHA-512`
- **Credenciales:** Usuario `fDlOyN218`, org Quinta (218)

### Servicio → WebSocket
- **Protocolo:** `WSS` (WebSocket sobre TLS)
- **Autenticación:** No visible en el código (puede estar en el handshake del servidor destino)

---

## Logging

El servicio utiliza **SLF4J + Logback** (default de Spring Boot). Los logs relevantes son:

| Nivel | Clase | Mensaje / Evento |
|---|---|---|
| `INFO` | `WebSocketClientService` | Conexión WebSocket abierta exitosamente |
| `INFO` | `WebSocketClientService` | Intento de conexión y reconexión |
| `INFO` | `WebSocketClientService` | Mensaje recibido del servidor WebSocket |
| `INFO` | `WebSocketClientService` | Mensaje enviado al WebSocket (con contenido completo) |
| `INFO` | `KafkaSendResultHandler` | Mensaje Kafka producido con éxito |
| `INFO` | `KafkaSendResultHandler` | Error al producir mensaje Kafka |
| `WARN` | `WebSocketClientService` | Conexión WebSocket cerrada (con code y reason) |
| `WARN` | `WebSocketClientService` | Mensaje descartado por WebSocket desconectado |
| `WARN` | `KafkaConsumer` | Topic Kafka sin mapeo WebSocket definido |
| `ERROR` | `WebSocketClientService` | Error interno del WebSocket |
| `ERROR` | `WebSocketClientService` | URI inválida al construir el cliente |
| `ERROR` | `WebSocketClientService` | Interrupción durante reconexión bloqueante |
| `ERROR` | `KafkaConsumer` | Error al construir o enviar mensaje WebSocket |

---

## Tests

| Clase | Tipo | Propósito |
|---|---|---|
| `SpringbootKafkaApplicationTests` | Spring Context Test | Verifica que el contexto de Spring carga correctamente |
| `KafkaListenerTest` | Integration Test | Prueba el callback global del productor: envía un mensaje al topic `test` y espera 1 segundo |

> Los tests están configurados con `skipTests=true` en el `pom.xml` — no corren por defecto en el build.

---

## Deuda técnica

### 🔴 Alta prioridad

- **Credenciales en texto plano**: El usuario, contraseña y JAAS config de Kafka están hardcodeados en `application.properties`. Deben migrarse a un sistema de secretos (variables de entorno, AWS Secrets Manager, Vault, etc.).
- **URL WebSocket hardcodeada**: `wss://iot.quinta.tech/ws/java` está hardcoded en `WebSocketClientService.java`. Debe externalizarse a `application.properties` o variable de entorno para permitir distintos entornos (dev, staging, prod).

### 🟡 Media prioridad

- **Mensajes descartados sin buffer**: Si el WebSocket está desconectado cuando llega un mensaje de Kafka, el mensaje se pierde permanentemente. No hay cola en memoria ni Dead Letter Queue (DLQ).
- **Sin validación de schema**: El payload de Kafka se reenvía sin ninguna validación de estructura. Un mensaje malformado causa una excepción en `new JSONObject(payload)` que se captura y solo loggea.
- **`KafkaProducer` expuesto en producción**: El controller REST de producción de mensajes no tiene ninguna autenticación y apunta al topic `test`. Debe removerse o protegerse en ambientes productivos.
- **`auto-commit` habilitado**: Con `enable-auto-commit=true`, si el servicio falla después del commit pero antes de enviar por WebSocket, los mensajes se pierden sin posibilidad de reintento.

### 🟢 Baja prioridad

- **Reconexión básica**: El mecanismo de reconexión usa un `Timer` simple con un solo intento a los 5 segundos. No hay backoff exponencial ni límite de reintentos.
- **Comentarios en chino**: Varios comentarios del código base están en chino mandarín (heredados del proyecto base). Deben traducirse al español o inglés.
- **Tests no corren en el build**: `skipTests=true` en `pom.xml` desactiva los tests globalmente.

---

## Servicios relacionados

| Servicio | Relación | Descripción |
|---|---|---|
| **Productores IoT (desconocido)** | Upstream → este servicio | Publican en `topic-sensor-218`, `topic-gps-218`, `topic-load-218` |
| **`wss://iot.quinta.tech/ws/java`** | Este servicio → Downstream | Servidor WebSocket del backend Quinta que recibe y distribuye los mensajes |
| **Broker Kafka (`101.132.76.195:9092`)** | Infraestructura compartida | Broker externo usado por Quinta (org 218) |

---

## Cómo correr el servicio

### Requisitos

- Java 17+
- Maven 3.x
- Acceso de red al broker Kafka (`101.132.76.195:9092`) y al servidor WebSocket (`iot.quinta.tech`)

### Iniciar

```bash
mvn spring-boot:run
```

### Build JAR

```bash
mvn clean package -DskipTests
java -jar target/springboot_kafka-1.0.0.jar
```

### Probar productor local (solo dev)

```bash
# Enviar mensaje simple al topic "test"
curl "http://localhost:8080/kafka/producer/send?message=hola"

# Enviar con callback
curl "http://localhost:8080/kafka/producer/send/callback?message=hola"
```

---

*Generado: Marzo 2026 | Versión del artefacto: `1.0.0` | Group ID: `com.springboot.whw`*
