package com.springboot.whw.springboot_kafka.kafka.consumer;

import com.springboot.whw.springboot_kafka.kafka.MQTopic;
import com.springboot.whw.springboot_kafka.service.PythonBridgeService;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
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

    private final PythonBridgeService pythonBridgeService;

    @Autowired
    public KafkaConsumer(PythonBridgeService pythonBridgeService) {
        this.pythonBridgeService = pythonBridgeService;
    }

    @KafkaListener(topics = {MQTopic.TOPIC_SENSOR})
    public void onSensorMessage(ConsumerRecord<?, ?> record) {
        log.info("Sensor Message Received: Topic={}, Partition={}, Content={}",
                record.topic(), record.partition(), record.value());
        pythonBridgeService.sendMessage(record.value().toString());
    }

    @KafkaListener(topics = {MQTopic.TOPIC_GPS})
    public void onGpsMessage(ConsumerRecord<?, ?> record) {
        log.info("GPS Message Received: Topic={}, Partition={}, Content={}",
                record.topic(), record.partition(), record.value());
        pythonBridgeService.sendMessage(record.value().toString());
    }

    @KafkaListener(topics = {MQTopic.TOPIC_LOAD})
    public void onLoadMessage(ConsumerRecord<?, ?> record) {
        log.info("Load Message Received: Topic={}, Partition={}, Content={}",
                record.topic(), record.partition(), record.value());
        pythonBridgeService.sendMessage(record.value().toString());
    }
}
