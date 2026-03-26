package com.springboot.whw.springboot_kafka.websocket;

import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.net.URI;
import java.net.URISyntaxException;
import java.time.Duration;
import java.time.Instant;
import java.util.concurrent.ConcurrentLinkedQueue;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;

@Service
public class WebSocketClientService {

    // ── Loggers ──────────────────────────────────────────────────────────────
    /** Log general de la aplicación → logs/application.log + consola */
    private static final Logger logger = LoggerFactory.getLogger(WebSocketClientService.class);

    /**
     * Mensajes que no pudieron enviarse (colgados) → logs/lost-messages.log
     * Formato: TIMESTAMP | TIPO | detalle
     * Tipos: QUEUED | RETRIED | FLUSH_SUMMARY | QUEUE_FULL | DROPPED
     */
    private static final Logger lostLogger = LoggerFactory.getLogger("LOST_WS_MESSAGES");

    /**
     * Reporte de incidencias del WebSocket → logs/incidents.log
     * Formato: TIMESTAMP | NIVEL | TIPO_EVENTO | detalle
     * Tipos de evento:
     *   CONNECTED       – conexión abierta exitosamente
     *   DISCONNECTED    – conexión cerrada (con código y razón)
     *   RECONNECT_SCHED – se programó un intento de reconexión
     *   RECONNECT_OK    – reconexión exitosa
     *   RECONNECT_FAIL  – intento de reconexión fallido
     *   ERROR           – error interno del WebSocket
     *   QUEUE_OVERFLOW  – la cola de pendientes llegó al límite y se descartó un mensaje
     *   FLUSH_START     – inicio del reenvío de mensajes pendientes tras reconexión
     *   FLUSH_END       – fin del reenvío con resumen
     */
    private static final Logger incidentLogger = LoggerFactory.getLogger("WS_INCIDENTS");

    // ── Configuración ─────────────────────────────────────────────────────────
    private static final String WEBSOCKET_URI = "wss://iot.quinta.tech/ws/java";

    /** Backoff exponencial: empieza en 2s, se duplica, tope en 60s */
    private static final long INITIAL_RECONNECT_DELAY_MS = 2_000;
    private static final long MAX_RECONNECT_DELAY_MS     = 60_000;

    /** Máximo de mensajes en cola antes de descartar los más viejos (~40 MB) */
    private static final int MAX_PENDING_QUEUE_SIZE = 100_000;

    // ── Estado interno ────────────────────────────────────────────────────────
    private WebSocketClient client;

    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor(r -> {
        Thread t = new Thread(r, "ws-reconnect-scheduler");
        t.setDaemon(true);
        return t;
    });
    private ScheduledFuture<?> reconnectFuture;

    private final AtomicBoolean isClosing      = new AtomicBoolean(false);
    private final AtomicBoolean isReconnecting = new AtomicBoolean(false);
    private final AtomicInteger reconnectAttempt = new AtomicInteger(0);

    /** Momento exacto en que se detectó la desconexión (para calcular tiempo caído). */
    private volatile Instant disconnectedAt = null;

    /** Contador de mensajes encolados desde la última desconexión (para evitar log spam). */
    private final AtomicInteger queuedSinceDisconnect = new AtomicInteger(0);

    /** Cola thread-safe de mensajes pendientes de envío */
    private final ConcurrentLinkedQueue<String> pendingMessages = new ConcurrentLinkedQueue<>();

    // ── Ciclo de vida ─────────────────────────────────────────────────────────

    @PostConstruct
    public void connect() {
        createAndConnect();
    }

    private synchronized void createAndConnect() {
        if (isClosing.get()) return;

        // Cerrar cliente zombie anterior antes de crear uno nuevo
        if (client != null && !client.isClosed()) {
            try { client.closeBlocking(); } catch (Exception ignored) {}
        }

        try {
            URI uri = new URI(WEBSOCKET_URI);
            client = new WebSocketClient(uri) {

                @Override
                public void onOpen(ServerHandshake handshakedata) {
                    int attempt = reconnectAttempt.getAndSet(0);
                    cancelReconnectFuture();
                    isReconnecting.set(false);

                    if (attempt == 0) {
                        logger.info("WebSocket conectado a {}", WEBSOCKET_URI);
                        incidentLogger.info("CONNECTED | uri={}", WEBSOCKET_URI);
                    } else {
                        String downtime = formatDowntime(disconnectedAt);
                        logger.info("WebSocket reconectado a {} tras {} intento(s) (caído {})", WEBSOCKET_URI, attempt, downtime);
                        incidentLogger.info("RECONNECT_OK | uri={} | intentos={} | tiempoCaido={}",
                                WEBSOCKET_URI, attempt, downtime);
                    }

                    flushPendingMessages();
                    disconnectedAt = null;
                }

                @Override
                public void onMessage(String message) {
                    logger.debug("Mensaje recibido del WebSocket: {}", message);
                }

                @Override
                public void onClose(int code, String reason, boolean remote) {
                    disconnectedAt = Instant.now();
                    logger.warn("WebSocket cerrado. code={} reason='{}' remote={}", code, reason, remote);
                    incidentLogger.warn("DISCONNECTED | code={} | reason='{}' | remote={} | pendingQueue={}",
                            code, reason, remote, pendingMessages.size());
                    lostLogger.warn("DISCONNECTED | {} | code={} | reason='{}' | remote={}",
                            disconnectedAt, code, reason, remote);

                    if (!isClosing.get()) {
                        scheduleReconnect();
                    }
                }

                @Override
                public void onError(Exception ex) {
                    String msg = ex.getMessage() != null ? ex.getMessage() : ex.getClass().getSimpleName();
                    logger.error("Error en WebSocket: {}", msg, ex);
                    incidentLogger.error("ERROR | {} | pendingQueue={}", msg, pendingMessages.size());
                    lostLogger.warn("ERROR | {} | {}", Instant.now(), msg);
                }
            };

            logger.info("Conectando al WebSocket: {}", WEBSOCKET_URI);
            // Desactivar pings del cliente: enviamos datos continuamente (10-20 msg/s)
            // y nginx ya tiene proxy_read_timeout 3600s, así que no necesitamos heartbeat
            client.setConnectionLostTimeout(0);
            client.connect();

        } catch (URISyntaxException e) {
            logger.error("URI de WebSocket inválida: {}", WEBSOCKET_URI, e);
            incidentLogger.error("CONNECT_FAIL | URI inválida: {}", WEBSOCKET_URI);
        }
    }

    // ── Envío de mensajes ─────────────────────────────────────────────────────

    public void sendMessage(String message) {
        // synchronized para que múltiples hilos de Kafka no colisionen en el mismo client.send()
        synchronized (this) {
            if (client != null && client.isOpen()) {
                try {
                    client.send(message);
                    return; // enviado ok, salimos
                } catch (Exception e) {
                    String errMsg = e.getMessage() != null ? e.getMessage() : e.getClass().getSimpleName();
                    // La librería lanza "WebSocket is not connected" cuando cae justo al enviar
                    if (errMsg.contains("not connected") || errMsg.contains("NotYetConnected")) {
                        logger.debug("WebSocket cayó al enviar, encolando (normal durante reconexión)");
                    } else {
                        logger.error("Error inesperado al enviar mensaje: {}", errMsg, e);
                        incidentLogger.warn("SEND_FAIL | error={}", errMsg);
                    }
                }
            }
        }
        // Si llega aquí es porque no estaba conectado o falló el send
        // NO llamamos scheduleReconnect() aquí — onClose() ya lo hará cuando el server cierre la conexión
        enqueue(message);
    }

    private void enqueue(String message) {
        if (pendingMessages.size() >= MAX_PENDING_QUEUE_SIZE) {
            String dropped = pendingMessages.poll(); // descartar el más viejo
            lostLogger.warn("QUEUE_FULL | DROPPED | {} | {}", Instant.now(), dropped);
            incidentLogger.error("QUEUE_OVERFLOW | limite={} | mensaje descartado (el más antiguo)", MAX_PENDING_QUEUE_SIZE);
        }
        pendingMessages.offer(message);
        int count = queuedSinceDisconnect.incrementAndGet();

        // Cada mensaje queda registrado en lost-messages.log (NO en consola ni application.log)
        lostLogger.info("QUEUED | {} | pending={} | {}", Instant.now(), count, message);

        // Solo la primera vez y cada 100 se avisa en incidents.log (sin spam)
        if (count == 1) {
            incidentLogger.warn("QUEUE_ACTIVE | WebSocket caído, encolando mensajes | pending={}", pendingMessages.size());
        } else if (count % 100 == 0) {
            incidentLogger.warn("QUEUED_SUMMARY | {} mensajes encolados desde desconexión | pending={}",
                    count, pendingMessages.size());
        }
    }

    // ── Reenvío de mensajes al reconectar ─────────────────────────────────────

    private void flushPendingMessages() {
        int total = pendingMessages.size();
        queuedSinceDisconnect.set(0); // reset para el próximo ciclo de desconexión
        if (total == 0) {
            lostLogger.info("RECONNECTED | {} | Sin mensajes pendientes", Instant.now());
            return;
        }

        logger.info("Reenviando {} mensaje(s) pendiente(s)...", total);
        incidentLogger.info("FLUSH_START | pendientes={}", total);
        lostLogger.warn("RECONNECTED | {} | Reenviando {} mensaje(s)", Instant.now(), total);

        int sent = 0, failed = 0;
        String msg;
        while ((msg = pendingMessages.poll()) != null) {
            try {
                client.send(msg);
                lostLogger.info("RETRIED | {} | {}", Instant.now(), msg);
                sent++;
            } catch (Exception e) {
                // Detener el flush, re-encolar y esperar siguiente reconexión
                pendingMessages.offer(msg);
                failed++;
                String errMsg = e.getMessage() != null ? e.getMessage() : e.getClass().getSimpleName();
                logger.error("Fallo durante flush (deteniendo): {}", errMsg);
                break;
            }
        }

        String downtime = formatDowntime(disconnectedAt);
        lostLogger.warn("FLUSH_SUMMARY | {} | enviados={} | fallidos={} | restantes={} | tiempoCaido={}",
                Instant.now(), sent, failed, pendingMessages.size(), downtime);
        incidentLogger.info("FLUSH_END | mensajesSalvados={} | fallidos={} | restantes={} | tiempoCaido={}",
                sent, failed, pendingMessages.size(), downtime);

        if (sent > 0) {
            incidentLogger.info("RECOVERY_SUMMARY | Se previnió la pérdida de {} mensaje(s) durante {} de desconexión",
                    sent, downtime);
        }
    }

    // ── Reconexión con backoff exponencial ───────────────────────────────────

    private synchronized void scheduleReconnect() {
        if (isClosing.get() || (reconnectFuture != null && !reconnectFuture.isDone())) {
            return;
        }
        isReconnecting.set(true);
        int attempt  = reconnectAttempt.incrementAndGet();
        long delayMs = Math.min(
                INITIAL_RECONNECT_DELAY_MS * (1L << Math.min(attempt - 1, 5)),
                MAX_RECONNECT_DELAY_MS);

        logger.info("Reconexión #{} programada en {} ms", attempt, delayMs);
        incidentLogger.warn("RECONNECT_SCHED | intento={} | delay={}ms | pendingQueue={}",
                attempt, delayMs, pendingMessages.size());

        reconnectFuture = scheduler.schedule(() -> {
            logger.info("Intentando reconexión #{} ...", attempt);
            createAndConnect();
        }, delayMs, TimeUnit.MILLISECONDS);
    }

    private synchronized void cancelReconnectFuture() {
        if (reconnectFuture != null) {
            reconnectFuture.cancel(false);
            reconnectFuture = null;
        }
    }

    // ── Utilidades ────────────────────────────────────────────────────────────

    /** Número de mensajes actualmente en cola (útil para monitoreo / health endpoint). */
    public int getPendingMessageCount() {
        return pendingMessages.size();
    }

    /**
     * Formatea el tiempo transcurrido desde {@code from} hasta ahora
     * en un string legible, ej: "3m 42s" o "8s".
     */
    private String formatDowntime(Instant from) {
        if (from == null) return "desconocido";
        Duration d = Duration.between(from, Instant.now());
        long minutes = d.toMinutes();
        long seconds = d.getSeconds() % 60;
        if (minutes > 0) return minutes + "m " + seconds + "s";
        return seconds + "s";
    }

    public void close() {
        isClosing.set(true);
        cancelReconnectFuture();
        scheduler.shutdownNow();
        if (client != null) {
            client.close();
        }
        incidentLogger.info("SHUTDOWN | pendingQueue={}", pendingMessages.size());
    }
}
