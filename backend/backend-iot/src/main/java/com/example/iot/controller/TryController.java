package com.example.iot.controller;

import com.example.iot.dto.response.TryFinishResponse;
import com.example.iot.dto.response.TryStartResponse;
import com.example.iot.service.IngestClient;
import com.example.iot.service.IngestRedisService;
import com.example.iot.service.TryService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.Map;

@Slf4j
@RestController
@RequestMapping("/api/tries")
public class TryController {

    private final IngestClient ingestClient;
    private final TryService tryService;
    private final IngestRedisService redisService; // Redis 조회용

    public TryController(TryService tryService,
                         IngestRedisService redisService,
                         IngestClient ingestClient
                         ) {
        this.redisService = redisService;
        this.tryService = tryService;
        this.ingestClient = ingestClient;
    }
    /**
     * 운동 시도 종료
     * 프론트는 tryId만 보내고, 서버가 Redis에서 데이터를 직접 꺼내 서비스에 전달함
     */
    @PostMapping("/{tryId}/finish")
    public ResponseEntity<TryFinishResponse> finish(@PathVariable Long tryId) {
        // 1. Redis에서 해당 Try의 프레임 데이터 리스트 조회
        // 키 패턴은 "frames:try:{tryId}"로 가정
        // 일단 있는 값 다 가져오기
        String rawFrame = redisService.getLatest();
        Map<Object, Object> rawAgg = redisService.getAgg(tryId);
        //로그로 최종확인
        log.info("rawAgg = {}", (String) rawAgg.getOrDefault("sum.strength", "0"));
        log.info("request = {}", rawFrame);
        //끝났음 신호
        ingestClient.stopTry();
        // 2. 조회된 데이터를 포함하여 서비스 호출
        return ResponseEntity.ok(tryService.finishTry(tryId, rawFrame));
    }

    /**
     * 운동 시도 시작
     */
    @PostMapping("/{tryId}/start")
    public ResponseEntity<TryStartResponse> start(@PathVariable Long tryId) {
        ingestClient.startTry(String.valueOf(tryId));
        return ResponseEntity.ok(tryService.startTry(tryId));
    }

}