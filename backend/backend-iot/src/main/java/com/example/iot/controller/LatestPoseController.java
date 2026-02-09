package com.example.iot.controller;

import com.example.iot.redis.dto.LatestResponse;
import com.example.iot.service.LatestPoseService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/redis")
public class LatestPoseController {

    private final LatestPoseService latestPoseService;

    public LatestPoseController(LatestPoseService latestPoseService) {
        this.latestPoseService = latestPoseService;
    }

    @GetMapping("/latest")
    public ResponseEntity<?> getLatest(
            @RequestParam String deviceId,
            @RequestParam String joint
    ) {
        String key = latestPoseService.buildKey(deviceId, joint);

        return latestPoseService.getLatest(deviceId, joint)
                .<ResponseEntity<?>>map(v -> ResponseEntity.ok(new LatestResponse(true, key, v)))
                .orElseGet(() -> ResponseEntity.status(404).body(
                        java.util.Map.of("ok", false, "key", key, "message", "Not found")
                ));
    }
}