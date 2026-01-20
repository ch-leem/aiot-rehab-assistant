package com.example.iot.controller;

import com.example.iot.service.RedisLatestService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequiredArgsConstructor
@RequestMapping("/api/iot")
public class IotLatestController {

    private final RedisLatestService redisLatestService;

    @GetMapping("/latest")
    public Map<String, Object> latest(
            @RequestParam String deviceId,
            @RequestParam String joint
    ) {
        String key = "latest:device:" + deviceId + ":joint:" + joint;
        String json = redisLatestService.getLatest(key);
        return Map.of("key", key, "value", json);
    }

}
