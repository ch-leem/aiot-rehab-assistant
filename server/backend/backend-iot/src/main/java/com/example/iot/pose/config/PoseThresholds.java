package com.example.iot.pose.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "pose")
public class PoseThresholds {

    /**
     * keypoint confidence 최소값
     */
    private double minConf = 0.30;

    public double getMinConf() {
        return minConf;
    }

    public void setMinConf(double minConf) {
        this.minConf = minConf;
    }
}
