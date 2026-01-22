package com.example.iot.redis;

public final class RedisKeys {
    private RedisKeys() {}

    public static String latestKey(String deviceId, String joint) {
        return "latest:device:" + deviceId + ":joint:" + joint;
    }
}