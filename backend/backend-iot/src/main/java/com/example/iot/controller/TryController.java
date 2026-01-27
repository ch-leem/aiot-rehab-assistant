package com.example.iot.controller;

import com.example.iot.dto.response.TryFinishResponse;
import com.example.iot.dto.response.TryStartResponse;
import com.example.iot.service.IngestRedisService;
import com.example.iot.service.TryService;
import lombok.RequiredArgsConstructor;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/tries")
@RequiredArgsConstructor // 생성자 주입 자동 생성
public class TryController {

    private final TryService tryService;
    private final IngestRedisService redisService; // Redis 조회용

    public TryController(TryService tryService,
                         IngestRedisService redisService,
                         StringRedisTemplate redisTemplate
                         ) {
        this.redisService = redisService;
        this.tryService = tryService;
    }
    /**
     * 운동 시도 종료
     * 프론트는 tryId만 보내고, 서버가 Redis에서 데이터를 직접 꺼내 서비스에 전달함
     */
    @PostMapping("/{tryId}/finish")
    public ResponseEntity<TryFinishResponse> finish(@PathVariable Long tryId) {
        // 1. Redis에서 해당 Try의 프레임 데이터 리스트 조회
        // 키 패턴은 "frames:try:{tryId}"로 가정
        String rawFrames = redisService.getLatest();

        // 2. 조회된 데이터를 포함하여 서비스 호출
        return ResponseEntity.ok(tryService.finishTry(tryId, rawFrames));
    }

    /**
     * 운동 시도 시작
     */
    @PostMapping("/{tryId}/start")
    public ResponseEntity<TryStartResponse> start(@PathVariable Long tryId) {
        return ResponseEntity.ok(tryService.startTry(tryId));
    }

}