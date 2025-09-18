package com.springboot.whw.springboot_kafka;

import com.springboot.whw.springboot_kafka.kafka.KafkaSendResultHandler;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.kafka.core.KafkaTemplate;

/**
 * @author whw
 * @Description kafka全局回调测试类
 * @createTime 2022/11/19 22:58
 */
@SpringBootTest
public class KafkaListenerTest {

    @Autowired
    private KafkaTemplate kafkaTemplate;

    @Autowired
    private KafkaSendResultHandler producerListener;

    @Test
    public void sendListenerTest() throws InterruptedException {
        kafkaTemplate.setProducerListener(producerListener);
        kafkaTemplate.send("test", "data_102");
        Thread.sleep(1000L);
    }
}
