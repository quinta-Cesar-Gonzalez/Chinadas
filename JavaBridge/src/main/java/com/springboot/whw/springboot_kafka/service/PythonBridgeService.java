package com.springboot.whw.springboot_kafka.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;

import java.util.Collections;
import java.util.Map;

@Service
@Slf4j
public class PythonBridgeService {

    private final RestTemplate restTemplate;
    private final String pythonApiUrl = "http://localhost:8000/api/messages";

    @Autowired
    public PythonBridgeService(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
    }

    public void sendMessage(String message) {
        try {
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);

            // The payload should be a JSON object: {"message": "..."}
            // The message itself is a string, which might be JSON, so it needs to be wrapped.
            Map<String, String> body = Collections.singletonMap("message", message);

            HttpEntity<Map<String, String>> request = new HttpEntity<>(body, headers);

            log.info("Sending message to Python service at {}", pythonApiUrl);
            ResponseEntity<String> response = restTemplate.postForEntity(pythonApiUrl, request, String.class);

            if (response.getStatusCode().is2xxSuccessful()) {
                log.info("Successfully sent message to Python service. Response: {}", response.getBody());
            } else {
                log.error("Failed to send message to Python service. Status: {}, Body: {}", response.getStatusCode(), response.getBody());
            }
        } catch (Exception e) {
            log.error("Error sending message to Python service", e);
        }
    }
}
