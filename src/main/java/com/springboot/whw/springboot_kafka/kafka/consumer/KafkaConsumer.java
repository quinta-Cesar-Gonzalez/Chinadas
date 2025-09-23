package com.springboot.whw.springboot_kafka.kafka.consumer;

import com.springboot.whw.springboot_kafka.kafka.MQTopic;
import com.springboot.whw.springboot_kafka.websocket.WebSocketService;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.json.JSONObject;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

@Slf4j
@Component
public class KafkaConsumer {

    @Autowired
    private WebSocketService webSocketService;

    @KafkaListener(topics = {MQTopic.TOPIC_SENSOR, MQTopic.TOPIC_GPS, MQTopic.TOPIC_LOAD})
    public void onMessage(ConsumerRecord<?, ?> record) {
        String topic = mapTopic(record.topic());
        if (topic == null) {
            log.warn("No topic mapping found for Kafka topic: {}", record.topic());
            return;
        }

        String payload = record.value().toString();

        try {
            JSONObject jsonPayload = new JSONObject(payload);
            JSONObject finalJson = new JSONObject();
            finalJson.put("topic", topic);
            finalJson.put("payload", jsonPayload);

            String messageToSend = finalJson.toString();
            log.info("Sending message to WebSocket: {}", messageToSend);
            webSocketService.sendMessage(messageToSend);
        } catch (Exception e) {
            log.error("Error creating or sending JSON message for topic {}", record.topic(), e);
        }
    }

    private String mapTopic(String kafkaTopic) {
        switch (kafkaTopic) {
            case MQTopic.TOPIC_GPS:
                return "gps";
            case MQTopic.TOPIC_SENSOR:
                return "sensor";
            case MQTopic.TOPIC_LOAD:
                return "load";
            default:
                return null;
        }
    }
}
