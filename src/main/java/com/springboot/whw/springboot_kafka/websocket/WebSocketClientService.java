package com.springboot.whw.springboot_kafka.websocket;

import lombok.extern.slf4j.Slf4j;
import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.Timer;
import java.util.TimerTask;

@Slf4j
@Service
public class WebSocketClientService {

    private static final String WEBSOCKET_URI = "wss://iot.quinta.tech/ws/java";
    private WebSocketClient client;
    private Timer reconnectTimer;
    private boolean isClosing = false;

    @PostConstruct
    public void connect() {
        try {
            URI uri = new URI(WEBSOCKET_URI);
            client = new WebSocketClient(uri) {
                @Override
                public void onOpen(ServerHandshake handshakedata) {
                    log.info("WebSocket connection opened to {}", WEBSOCKET_URI);
                    cancelReconnectTimer();
                }

                @Override
                public void onMessage(String message) {
                    log.info("Received message from WebSocket: {}", message);
                }

                @Override
                public void onClose(int code, String reason, boolean remote) {
                    log.warn("WebSocket connection closed. Code: {}, Reason: {}, Remote: {}", code, reason, remote);
                    if (!isClosing) {
                        scheduleReconnect();
                    }
                }

                @Override
                public void onError(Exception ex) {
                    log.error("WebSocket error", ex);
                }
            };
            log.info("Attempting to connect to WebSocket: {}", WEBSOCKET_URI);
            client.connect();
        } catch (URISyntaxException e) {
            log.error("Invalid WebSocket URI", e);
        }
    }

    public void sendMessage(String message) {
        if (client != null && client.isOpen()) {
            client.send(message);
        } else {
            log.warn("WebSocket is not connected. Message not sent: {}", message);
        }
    }

    private void scheduleReconnect() {
        if (reconnectTimer == null) {
            reconnectTimer = new Timer("WebSocket Reconnect Timer");
        }
        reconnectTimer.schedule(new TimerTask() {
            @Override
            public void run() {
                log.info("Attempting to reconnect WebSocket...");
                reconnect();
            }
        }, 5000); // Reconnect after 5 seconds
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
                log.info("Reconnecting to WebSocket: {}", WEBSOCKET_URI);
                client.reconnectBlocking();
            } catch (InterruptedException e) {
                log.error("WebSocket reconnection was interrupted", e);
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