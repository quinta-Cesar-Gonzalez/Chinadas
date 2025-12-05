package com.springboot.whw.springboot_kafka.websocket;

import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;

import javax.annotation.PostConstruct;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.Timer;
import java.util.TimerTask;

@Service
public class WebSocketClientService {

    private static final Logger logger = LoggerFactory.getLogger(WebSocketClientService.class);
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
                    logger.info("WebSocket connection opened to {}", WEBSOCKET_URI);
                    cancelReconnectTimer();
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

    public void sendMessage(String message) {
        if (client != null && client.isOpen()) {
            client.send(message);
        } else {
            logger.warn("WebSocket is not connected. Message not sent: {}", message);
        }
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
