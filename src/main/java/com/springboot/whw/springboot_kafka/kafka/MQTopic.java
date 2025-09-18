package com.springboot.whw.springboot_kafka.kafka;

/**
 * @author whw
 * @Description kafka主题定义
 * @createTime 2022/11/19 13:06
 */
public interface MQTopic {

    /**
     * test主题
     */
    String TEST = "test";

    /**
     * test主题
     */
    String TOPIC_SENSOR = "topic-sensor-218";

    /**
     * test主题
     */
    String TOPIC_GPS = "topic-gps-218";

    /**
     * test主题
     */
    String TOPIC_LOAD = "topic-load-218";
}
