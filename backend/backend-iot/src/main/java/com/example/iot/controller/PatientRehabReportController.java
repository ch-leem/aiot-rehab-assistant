package com.example.iot.controller;

import com.example.iot.service.PatientRehabReportService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/rehab/reports")
@RequiredArgsConstructor
public class PatientRehabReportController {

    private final PatientRehabReportService reportService;

    /**
     * [POST] AI 재활 분석 리포트 생성 요청
     * 특정 시퀀스가 종료된 후, 이 API를 호출하여 AI 분석을 실행합니다.
     */
    @PostMapping("/generate/{sequenceId}")
    public ResponseEntity<String> generateReport(@PathVariable Long sequenceId) {
        try {
            // 이 메서드는 데이터 조립 -> GMS 호출 -> 저장을 한 번에 수행합니다.
            reportService.createAndSaveReport(sequenceId);
            return ResponseEntity.accepted()
                    .body("리포트 생성 요청이 접수되었습니다. 잠시 후 조회가 가능합니다. ID: " + sequenceId);
        } catch (Exception e) {
            return ResponseEntity.internalServerError()
                    .body("리포트 생성 중 오류 발생: " + e.getMessage());
        }
    }

    /**
     * [GET] 생성된 리포트 상세 조회
     * 저장된 JSON 리포트를 그대로 반환하거나, 특정 요약본을 반환합니다.
     */
    @GetMapping("/{sequenceId}")
    public ResponseEntity<?> getReport(@PathVariable Long sequenceId) {
        // 이 부분은 기존에 작성했던 SequenceService나
        // ReportRepository를 통해 저장된 데이터를 반환하도록 구현하면 됩니다.
        return ResponseEntity.ok(reportService.getSavedReport(sequenceId));
    }
}