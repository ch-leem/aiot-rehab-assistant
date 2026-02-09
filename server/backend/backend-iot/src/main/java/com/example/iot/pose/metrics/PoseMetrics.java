package com.example.iot.pose.metrics;

import java.util.Collections;
import java.util.EnumMap;
import java.util.Map;

public class PoseMetrics {

    private final EnumMap<PoseMetricType, Double> values = new EnumMap<>(PoseMetricType.class);

    public void put(PoseMetricType type, Double value) {
        if (value != null) values.put(type, value);
    }

    public Double get(PoseMetricType type) {
        return values.get(type);
    }

    public Map<PoseMetricType, Double> asMap() {
        return Collections.unmodifiableMap(values);
    }
}