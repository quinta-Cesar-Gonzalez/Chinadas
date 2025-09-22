package com.springboot.whw.springboot_kafka.kafka.producer;

import com.springboot.whw.springboot_kafka.kafka.MQTopic;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.kafka.support.SendResult;
import org.springframework.util.concurrent.ListenableFutureCallback;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * @author whw
 * @Description kafka消息生产者Controller
 * @createTime 2022/11/19 12:32
 */
@RestController
@RequestMapping("kafka/producer")
public class KafkaProducer {

    @Autowired
    private KafkaTemplate<String, Object> kafkaTemplate;

    @RequestMapping("/send")
    public String sendMessage(String message) {
        kafkaTemplate.send(MQTopic.TEST, message);
        return "ok";
    }

    @RequestMapping("/send/callback")
    public String sendMessageCallback(String message) {
        kafkaTemplate.send(MQTopic.TEST, message).addCallback(success -> {
            String topic = success.getRecordMetadata().topic();
            int partition = success.getRecordMetadata().partition();
            long offset = success.getRecordMetadata().offset();
            System.out.println(String.format("发送成功，Topic=%s, 分区=%s, offset=%s",
                    topic, partition, offset));
        }, failure -> {
            System.out.println("发送失败：" + failure.getMessage());
        });
        return "send callback ok";
    }

    @RequestMapping("/send/future/callback")
    public String sendMessageFutureCallback(String message) {
        kafkaTemplate.send(MQTopic.TEST, message).addCallback(new ListenableFutureCallback<SendResult<String, Object>>() {
            @Override
            public void onFailure(Throwable ex) {
                System.out.println("发送失败：" + ex.getMessage());
            }

            @Override
            public void onSuccess(SendResult<String, Object> result) {
                String topic = result.getRecordMetadata().topic();
                int partition = result.getRecordMetadata().partition();
                long offset = result.getRecordMetadata().offset();
                System.out.println(String.format("发送成功，Topic=%s, 分区=%s, offset=%s",
                        topic, partition, offset));
            }
        });
        return "send future callback ok";
    }
}
