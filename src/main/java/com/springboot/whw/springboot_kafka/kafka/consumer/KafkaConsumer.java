package com.springboot.whw.springboot_kafka.kafka.consumer;

import com.springboot.whw.springboot_kafka.kafka.MQTopic;
import lombok.extern.slf4j.Slf4j;
import org.apache.kafka.clients.consumer.ConsumerRecord;
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

    @KafkaListener(topics = {MQTopic.TOPIC_SENSOR})
    public void onSensorMessage(ConsumerRecord<?, ?> record) {
        log.info("Sensor Message: Topic={}, Partition={}, Content={}",
                record.topic(), record.partition(), record.value());
    }

    @KafkaListener(topics = {MQTopic.TOPIC_GPS})
    public void onGpsMessage(ConsumerRecord<?, ?> record) {
        log.info("GPS Message: Topic={}, Partition={}, Content={}",
                record.topic(), record.partition(), record.value());
    }

    @KafkaListener(topics = {MQTopic.TOPIC_LOAD})
    public void onLoadMessage(ConsumerRecord<?, ?> record) {
        log.info("Load Message: Topic={}, Partition={}, Content={}",
                record.topic(), record.partition(), record.value());
    }
}
