package com.springboot.whw.springboot_kafka.kafka;

import org.apache.kafka.clients.producer.ProducerRecord;
import org.apache.kafka.clients.producer.RecordMetadata;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.kafka.support.ProducerListener;
import org.springframework.stereotype.Component;

/**
 * @author whw
 * @Description kafka消息发送全局回调处理类
 * @createTime 2022/11/19 22:51
 */
@Component
public class KafkaSendResultHandler implements ProducerListener {

    private static final Logger log = LoggerFactory.getLogger(KafkaSendResultHandler.class);


    @Override
    public void onSuccess(ProducerRecord producerRecord, RecordMetadata recordMetadata) {
        log.info("Message send success: " + producerRecord.toString());
    }

    @Override
    public void onError(ProducerRecord producerRecord, RecordMetadata recordMetadata, Exception exception) {
        log.info("Message send error: " + producerRecord.toString());
    }
}
