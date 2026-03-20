package com.springboot.whw.springboot_kafka.websocket;

import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.net.URI;
import java.net.URISyntaxException;
import java.time.Instant;
import java.util.Timer;
import java.util.TimerTask;
import java.util.concurrent.ConcurrentLinkedQueue;

@Service
public class WebSocketClientService {

    // Logger general de la aplicación
    private static final Logger logger = LoggerFactory.getLogger(WebSocketClientService.class);

    // Logger dedicado exclusivamente al archivo logs/lost-messages.log
    // El nombre "LOST_WS_MESSAGES" debe coincidir con el <logger name="..."> en logback-spring.xml
    private static final Logger lostLogger = LoggerFactory.getLogger("LOST_WS_MESSAGES");

    private static final String WEBSOCKET_URI = "wss://iot.quinta.tech/ws/java";

    private WebSocketClient client;
    private Timer reconnectTimer;
    private boolean isClosing = false;

    // Cola thread-safe para guardar mensajes que no pudieron enviarse
    private final ConcurrentLinkedQueue<String> pendingMessages = new ConcurrentLinkedQueue<>();

    @PostConstruct
    public void connect() {
        try {
            URI uri = new URI(WEBSOCKET_URI);
            client = new WebSocketClient(uri) {
                @Override
                public void onOpen(ServerHandshake handshakedata) {
                    logger.info("WebSocket connection opened to {}", WEBSOCKET_URI);

                    // Al reconectar, intentamos re-enviar todos los mensajes acumulados
                    int pendingCount = pendingMessages.size();
                    if (pendingCount > 0) {
                        lostLogger.warn("RECONNECTED | {} | Intentando re-enviar {} mensaje(s) pendiente(s)",
                                Instant.now(), pendingCount);

                        String pending;
                        int retried = 0;
                        int failed = 0;
                        while ((pending = pendingMessages.poll()) != null) {
                            try {
                                client.send(pending);
                                lostLogger.warn("RETRIED | {} | {}", Instant.now(), pending);
                                retried++;
                            } catch (Exception e) {
                                // Si falla de nuevo, volvemos a encolar
                                pendingMessages.offer(pending);
                                failed++;
                                logger.error("Error re-enviando mensaje pendiente: {}", pending, e);
                            }
                        }
                        lostLogger.warn("RETRY_SUMMARY | {} | Re-enviados: {} | Fallidos: {}",
                                Instant.now(), retried, failed);
                    } else {
                        lostLogger.warn("RECONNECTED | {} | Sin mensajes pendientes", Instant.now());
                    }

                    cancelReconnectTimer();
                }

                @Override
                public void onMessage(String message) {
                    logger.info("Received message from WebSocket: {}", message);
                }

                @Override
                public void onClose(int code, String reason, boolean remote) {
                    logger.warn("WebSocket connection closed. Code: {}, Reason: {}, Remote: {}", code, reason, remote);
                    lostLogger.warn("DISCONNECTED | {} | Code: {} | Reason: {} | Remote: {}",
                            Instant.now(), code, reason, remote);
                    if (!isClosing) {
                        scheduleReconnect();
                    }
                }

                @Override
                public void onError(Exception ex) {
                    logger.error("WebSocket error", ex);
                    lostLogger.warn("ERROR | {} | {}", Instant.now(), ex.getMessage());
                }
            };

            logger.info("Attempting to connect to WebSocket: {}", WEBSOCKET_URI);
            client.connect();
        } catch (URISyntaxException e) {
            logger.error("Invalid WebSocket URI", e);
        }
    }

    public void sendMessage(String message) {
        if (client != null && client.isOpen()) {
            client.send(message);
        } else {
            // Log general (warn)
            logger.warn("WebSocket not connected. Message queued for retry: {}", message);

            // Log detallado en el archivo dedicado lost-messages.log
            lostLogger.warn("LOST | {} | {}", Instant.now(), message);

            // Encolar el mensaje para re-enviarlo cuando se restaure la conexión
            pendingMessages.offer(message);
        }
    }

    /**
     * Retorna el número de mensajes actualmente en la cola de pendientes.
     * Útil para monitoreo o endpoints de salud.
     */
    public int getPendingMessageCount() {
        return pendingMessages.size();
    }

    private void scheduleReconnect() {
        if (reconnectTimer == null) {
            reconnectTimer = new Timer("WebSocket Reconnect Timer");
        }
        reconnectTimer.schedule(new TimerTask() {
            @Override
            public void run() {
                logger.info("Attempting to reconnect WebSocket...");
                reconnect();
            }
        }, 5000); // Reconectar después de 5 segundos
    }

    private void cancelReconnectTimer() {
        if (reconnectTimer != null) {
            reconnectTimer.cancel();
            reconnectTimer = null;
        }
    }

    private void reconnect() {
        if (client != null && !client.isOpen()) {
            try {
                logger.info("Reconnecting to WebSocket: {}", WEBSOCKET_URI);
                client.reconnectBlocking();
            } catch (InterruptedException e) {
                logger.error("WebSocket reconnection was interrupted", e);
                Thread.currentThread().interrupt();
            }
        }
    }

    public void close() {
        isClosing = true;
        cancelReconnectTimer();
        if (client != null) {
            client.close();
        }
    }
}
