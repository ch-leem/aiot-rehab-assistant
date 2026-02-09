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
        // 1. Redis에서 최신 프레임(Latest)과 집계 데이터(Agg) 조회
        String rawFrame = redisService.getLatest();
        Map<Object, Object> rawAgg = redisService.getAgg(tryId);

        // 2. 로그로 데이터 수신 상태 확인
        log.info("운동 종료 요청 - tryId: {}", tryId);
        if (rawAgg != null) {
            log.info("수신된 집계 데이터(Agg) 요약: 가속도합={}, 카운트={}",
                    rawAgg.getOrDefault("sum.strength", "0"),
                    rawAgg.getOrDefault("count.strength", "0"));
        } else {
            log.warn("tryId: {}에 해당하는 Agg 데이터가 Redis에 없습니다.", tryId);
        }

        // 3. 디바이스/인제스트 서버에 종료 신호 전송
        ingestClient.stopTry();

        // 4. 서비스 호출 (수정된 파라미터 반영: rawFrame, rawAgg 전달)
        // 이제 TryService 내의 FrameAnalyzer가 이 데이터들을 요리합니다.
        TryFinishResponse response = tryService.finishTry(tryId, rawFrame, rawAgg);

        return ResponseEntity.ok(response);
    }

    /**
     * 운동 시도 시작
     */
    @PostMapping("/{tryId}/start")
    public ResponseEntity<TryStartResponse> start(@PathVariable Long tryId) {
        log.info("운동 시작 요청 - tryId: {}", tryId);
        ingestClient.startTry(String.valueOf(tryId));
        return ResponseEntity.ok(tryService.startTry(tryId));
    }
}