package com.example.iot.redis;

import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
@RequestMapping("/redis")
public class RedisStreamController {

    private final RedisStreamReadService streamService;

    @GetMapping("/streams/{streamKey}/latest")
    public ResponseEntity<String> latest(@PathVariable String streamKey) {
        String json = streamService.readLatestPayload(streamKey);
        if (json == null) return ResponseEntity.noContent().build();
        return ResponseEntity.ok(json);
    }
}