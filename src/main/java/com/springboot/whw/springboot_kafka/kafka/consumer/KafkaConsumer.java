package com.springboot.whw.springboot_kafka.kafka.consumer;

import com.springboot.whw.springboot_kafka.kafka.MQTopic;
import com.springboot.whw.springboot_kafka.websocket.WebSocketClientService;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
import org.json.JSONObject;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Component;

/**
 * @author whw
 * @Description kafka消息消费者
 * @createTime 2022/11/19 12:36
 */
@Slf4j
@Component
public class KafkaConsumer {

    @Autowired
    private WebSocketClientService webSocketClientService;

    @KafkaListener(topics = {MQTopic.TOPIC_SENSOR, MQTopic.TOPIC_GPS, MQTopic.TOPIC_LOAD})
    public void onMessage(ConsumerRecord<?, ?> record) {
        processAndSendMessage(record);
    }

    private void processAndSendMessage(ConsumerRecord<?, ?> record) {
        String topic = record.topic();
        String payload = record.value().toString();

        String webSocketTopic = mapKafkaTopicToWebSocketTopic(topic);
        if (webSocketTopic == null) {
            log.warn("No WebSocket topic mapping found for Kafka topic: {}", topic);
            return;
        }

        try {
            JSONObject jsonPayload = new JSONObject();
            jsonPayload.put("topic", webSocketTopic);
            jsonPayload.put("payload", new JSONObject(payload));

            String messageToSend = jsonPayload.toString();
            log.info("Sending message to WebSocket: {}", messageToSend);
            webSocketClientService.sendMessage(messageToSend);
        } catch (Exception e) {
            log.error("Error creating or sending WebSocket message", e);
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
