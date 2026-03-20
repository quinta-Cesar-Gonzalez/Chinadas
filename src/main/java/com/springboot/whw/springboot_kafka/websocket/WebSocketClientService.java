package com.springboot.whw.springboot_kafka.websocket;

import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.concurrent.Executors;
import java.util.concurrent.LinkedBlockingQueue;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

@Service
public class WebSocketClientService {

    private static final Logger logger = LoggerFactory.getLogger(WebSocketClientService.class);
    private static final String WEBSOCKET_URI = "wss://iot.quinta.tech/ws/java";
    private static final int RECONNECT_DELAY_SECONDS = 5;
    private static final int BUFFER_CAPACITY = 1000;

    private WebSocketClient client;
    private final ScheduledExecutorService reconnectExecutor = Executors.newSingleThreadScheduledExecutor(
            r -> new Thread(r, "ws-reconnect-thread")
    );
    private volatile boolean isClosing = false;

    /** Cola de mensajes pendientes cuando el WebSocket está caído */
    private final LinkedBlockingQueue<String> messageQueue = new LinkedBlockingQueue<>(BUFFER_CAPACITY);

    @PostConstruct
    public void connect() {
        createAndConnect();
    }

    private void createAndConnect() {
        try {
            URI uri = new URI(WEBSOCKET_URI);
            client = new WebSocketClient(uri) {
                @Override
                public void onOpen(ServerHandshake handshakedata) {
                    logger.info("WebSocket connection opened to {}", WEBSOCKET_URI);
                    drainQueue();
                }

                @Override
                public void onMessage(String message) {
                    logger.info("Received message from WebSocket: {}", message);
                }

                @Override
                public void onClose(int code, String reason, boolean remote) {
                    logger.warn("WebSocket connection closed. Code: {}, Reason: {}, Remote: {}", code, reason, remote);
                    if (!isClosing) {
                        scheduleReconnect();
                    }
                }

                @Override
                public void onError(Exception ex) {
                    logger.error("WebSocket error", ex);
                }
            };

            logger.info("Attempting to connect to WebSocket: {}", WEBSOCKET_URI);
            client.connect();
        } catch (URISyntaxException e) {
            logger.error("Invalid WebSocket URI", e);
        }
    }

    /**
     * Envía un mensaje al WebSocket.
     * @return true si se envió directamente; false si fue encolado o descartado.
     */
    public boolean sendMessage(String message) {
        if (client != null && client.isOpen()) {
            client.send(message);
            return true;
        } else {
            boolean queued = messageQueue.offer(message);
            if (!queued) {
                logger.error("Buffer lleno ({}), mensaje descartado: {}", BUFFER_CAPACITY, message);
            } else {
                logger.warn("WebSocket caído. Mensaje encolado ({} en cola)", messageQueue.size());
            }
            return false;
        }
    }

    /**
     * Drena la cola de mensajes pendientes una vez que el WebSocket reconecta.
     */
    private void drainQueue() {
        int count = 0;
        String msg;
        while ((msg = messageQueue.poll()) != null) {
            client.send(msg);
            count++;
        }
        if (count > 0) {
            logger.info("Cola drenada: {} mensajes reenviados al WebSocket", count);
        }
    }

    private void scheduleReconnect() {
        reconnectExecutor.schedule(() -> {
            if (client != null && !client.isOpen()) {
                logger.info("Intentando reconectar al WebSocket: {}", WEBSOCKET_URI);
                try {
                    client.reconnectBlocking();
                } catch (InterruptedException e) {
                    logger.error("Reconexión WebSocket interrumpida", e);
                    Thread.currentThread().interrupt();
                }
            }
        }, RECONNECT_DELAY_SECONDS, TimeUnit.SECONDS);
    }

    public void close() {
        isClosing = true;
        reconnectExecutor.shutdownNow();
        if (client != null) {
            client.close();
        }
    }
}
