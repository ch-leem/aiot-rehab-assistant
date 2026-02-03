package com.example.iot.controller;

import com.example.iot.dto.request.SequenceStartRequest;
import com.example.iot.dto.response.PatientRehabReportResponse;
import com.example.iot.dto.response.SequenceStartResponse;
import com.example.iot.dto.response.SessionTryCountResponse;
import com.example.iot.service.PatientRehabReportService;
import com.example.iot.service.SequenceAverageService;
import com.example.iot.service.SequenceService;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Slf4j
@RestController
@RequestMapping("/api/sequence")
public class SequenceController {

    private final SequenceService sequenceService;
    private final SequenceAverageService sequenceAverageService;
    private final PatientRehabReportService reportService;

    public SequenceController(
            SequenceService sequenceService,
            SequenceAverageService sequenceAverageService,
            PatientRehabReportService reportService
    ) {
        this.sequenceService = sequenceService;
        this.sequenceAverageService = sequenceAverageService;
        this.reportService = reportService;
    }

    @PostMapping("/{patientId}")
    public ResponseEntity<SequenceStartResponse> startSequence(
            @PathVariable Long patientId,
            @RequestBody(required = false) SequenceStartRequest body
    ) {
        SequenceStartResponse res = sequenceService.startSequence(patientId, body);
        return ResponseEntity.ok(res);
    }

    @PostMapping("/{sequenceId}/complete")
    public ResponseEntity<String> completeSequence(@PathVariable Long sequenceId) {
        // 1. 시퀀스 종료 처리 및 비동기 AI 분석 시작
        sequenceService.completeSequence(sequenceId);

        // 2. 비동기이므로 분석 결과를 기다리지 않고 즉시 응답
        return ResponseEntity.accepted()
                .body("시퀀스가 종료되었습니다. AI 분석 리포트 생성이 시작되었습니다.");
    }

    @GetMapping("/{sequenceId}/report")
    public ResponseEntity<PatientRehabReportResponse> getReport(@PathVariable Long sequenceId) {
        // 이미 저장된 리포트를 DB에서 조회하여 반환
        return ResponseEntity.ok(reportService.getSavedReport(sequenceId));
    }

    @GetMapping("/{sequenceId}/average")
    public ResponseEntity<List<SessionTryCountResponse>> getSessionTryCounts(
            @PathVariable Long sequenceId
    ) {
        return ResponseEntity.ok(sequenceAverageService.getSessionTryCounts(sequenceId));
    }

}