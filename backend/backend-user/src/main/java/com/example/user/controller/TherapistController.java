package com.example.user.controller;

import com.example.user.dto.PatientReportResponse;
import com.example.user.dto.TherapistDashboardResponse;
import com.example.user.service.TherapistService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/therapist")
@RequiredArgsConstructor
public class TherapistController {

    private final TherapistService therapistService;

    // 대시보드 목록 및 검색 (예: /api/therapist/1/dashboard?search=홍길동)
    @GetMapping("/{therapistId}/dashboard")
    public ResponseEntity<TherapistDashboardResponse> getDashboard(
            @PathVariable Long therapistId,
            @RequestParam(required = false) String search) {
        return ResponseEntity.ofNullable(therapistService.getDashboard(therapistId, search));
    }

    // 환자 클릭 시 리포트 정보 조회
    @GetMapping("/patient/{patientId}/report")
    public ResponseEntity<PatientReportResponse> getPatientReport(@PathVariable Long patientId) {
        return ResponseEntity.ok(therapistService.getPatientReport(patientId));
    }
}