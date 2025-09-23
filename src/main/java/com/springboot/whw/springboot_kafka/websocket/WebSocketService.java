package com.springboot.whw.springboot_kafka.websocket;

import lombok.extern.slf4j.Slf4j;
import org.java_websocket.handshake.ServerHandshake;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.ScheduledFuture;
import java.util.concurrent.TimeUnit;

@Slf4j
@Service
public class WebSocketService {

    private static final String WEBSOCKET_URI = "wss://dev-iot.quinta.tech/ws/java";
    private volatile BridgeWebSocketClient client;
    private final ScheduledExecutorService scheduler = Executors.newSingleThreadScheduledExecutor();
    private ScheduledFuture<?> keepaliveTask;

    @PostConstruct
    public void start() {
        connect();
    }

    private void connect() {
        try {
            log.info("Initializing WebSocket connection to {}", WEBSOCKET_URI);
            client = new BridgeWebSocketClient(new URI(WEBSOCKET_URI)) {
                @Override
                public void onOpen(ServerHandshake handshakedata) {
                    super.onOpen(handshakedata);
                    // When connection opens, start the keepalive task
                    startKeepalive();
                }

                @Override
                public void onClose(int code, String reason, boolean remote) {
                    super.onClose(code, reason, remote);
                    // When connection closes, stop the keepalive task and schedule reconnect
                    stopKeepalive();
                    log.warn("WebSocket connection closed. Code: {}, Reason: {}. Attempting to reconnect...", code, reason);
                    scheduleReconnect();
                }
            };
            // We are now using a manual keepalive, so the automatic ping/pong is disabled.
            client.connect();
        } catch (URISyntaxException e) {
            log.error("Invalid WebSocket URI", e);
        }
    }

    public void sendMessage(String message) {
        if (client != null && client.isOpen()) {
            client.send(message);
        } else {
            log.warn("Cannot send message. WebSocket is not connected or client is null.");
        }
    }

    private void scheduleReconnect() {
        if (client != null && !client.isClosing() && !client.isOpen()) {
            scheduler.schedule(this::connect, 5, TimeUnit.SECONDS);
        }
    }

    private void startKeepalive() {
        log.info("Starting manual keepalive task. Sending a message every 25 seconds.");
        keepaliveTask = scheduler.scheduleAtFixedRate(() -> {
            try {
                if (client != null && client.isOpen()) {
                    // Send a simple text message to keep the connection alive
                    client.send("{\"type\":\"ping\"}");
                }
            } catch (Exception e) {
                log.error("Failed to send keepalive message", e);
            }
        }, 25, 25, TimeUnit.SECONDS);
    }

    private void stopKeepalive() {
        if (keepaliveTask != null && !keepaliveTask.isDone()) {
            log.info("Stopping manual keepalive task.");
            keepaliveTask.cancel(true);
        }
    }

    public BridgeWebSocketClient getClient() {
        return client;
    }
}
