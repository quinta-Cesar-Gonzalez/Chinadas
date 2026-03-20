package com.springboot.whw.springboot_kafka.kafka.consumer;

import com.springboot.whw.springboot_kafka.kafka.MQTopic;
import com.springboot.whw.springboot_kafka.websocket.WebSocketClientService;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.json.JSONObject;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.kafka.support.Acknowledgment;
import org.springframework.stereotype.Component;

/**
 * Kafka consumer que reenvía mensajes al WebSocket.
 * Usa manual acknowledgment: el offset SOLO se confirma si el mensaje
 * fue enviado exitosamente, evitando pérdida de datos.
 */
@Component
public class KafkaConsumer {

    private static final Logger logger = LoggerFactory.getLogger(KafkaConsumer.class);

    @Autowired
    private WebSocketClientService webSocketClientService;

    @KafkaListener(topics = {MQTopic.TOPIC_SENSOR, MQTopic.TOPIC_GPS, MQTopic.TOPIC_LOAD})
    public void onMessage(ConsumerRecord<?, ?> record, Acknowledgment ack) {
        boolean success = processAndSendMessage(record);
        if (success) {
            // Confirmamos el offset SOLO si el mensaje fue entregado o encolado en buffer
            ack.acknowledge();
        } else {
            // Si el buffer está lleno y el mensaje fue descartado, Kafka reintentará
            logger.error("Mensaje no pudo ser procesado, offset NO confirmado. Kafka reintentará. topic={}, offset={}",
                    record.topic(), record.offset());
        }
    }

    private boolean processAndSendMessage(ConsumerRecord<?, ?> record) {
        String topic = record.topic();
        String payload = record.value().toString();

        String webSocketTopic = mapKafkaTopicToWebSocketTopic(topic);
        if (webSocketTopic == null) {
            logger.warn("No WebSocket topic mapping found for Kafka topic: {}", topic);
            // No hay mapping, no tiene sentido reintentar: confirmar y descartar
            return true;
        }

        try {
            JSONObject jsonPayload = new JSONObject();
            jsonPayload.put("topic", webSocketTopic);
            jsonPayload.put("payload", new JSONObject(payload));

            String messageToSend = jsonPayload.toString();
            logger.info("Sending message to WebSocket: {}", messageToSend);
            return webSocketClientService.sendMessage(messageToSend);
        } catch (Exception e) {
            logger.error("Error creating WebSocket message for topic={}", topic, e);
            return false;
        }
    }

    private String mapKafkaTopicToWebSocketTopic(String kafkaTopic) {
        if (kafkaTopic.startsWith("topic-gps")) {
            return "gps";
        } else if (kafkaTopic.startsWith("topic-sensor")) {
            return "sensor";
        } else if (kafkaTopic.startsWith("topic-load")) {
            return "load";
        }
        return null;
    }
}
