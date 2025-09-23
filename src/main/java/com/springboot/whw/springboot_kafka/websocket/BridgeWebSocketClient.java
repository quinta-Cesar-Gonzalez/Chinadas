package com.springboot.whw.springboot_kafka.websocket;

import lombok.extern.slf4j.Slf4j;
import org.java_websocket.client.WebSocketClient;
import org.java_websocket.handshake.ServerHandshake;

import java.net.URI;

@Slf4j
public class BridgeWebSocketClient extends WebSocketClient {

    public BridgeWebSocketClient(URI serverUri) {
        super(serverUri);
    }

    @Override
    public void onOpen(ServerHandshake handshakedata) {
        log.info("WebSocket connection opened. Status: {}", handshakedata.getHttpStatusMessage());
    }

    @Override
    public void onMessage(String message) {
        log.info("Received message from WebSocket: {}", message);
    }

    @Override
    public void onClose(int code, String reason, boolean remote) {
        log.warn("WebSocket connection closed. Code: {}, Reason: {}, Remote: {}", code, reason, remote);
    }

    @Override
    public void onError(Exception ex) {
        log.error("WebSocket error", ex);
    }
}
