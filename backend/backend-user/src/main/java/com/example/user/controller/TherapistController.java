package com.example.user.controller;

import com.example.user.dto.ApiResponse;
import com.example.user.dto.PatientReportResponse;
import com.example.user.dto.TherapistDashboardResponse;
import com.example.user.service.TherapistService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/therapist")
@RequiredArgsConstructor
// origins -> 이후 실제 도메인 주소로 변경할 것
@CrossOrigin(origins = "http://localhost:3000")
public class TherapistController {

    private final TherapistService therapistService;

    // 대시보드 목록 및 검색
    @GetMapping("/{therapistId}/dashboard")
    public ResponseEntity<ApiResponse<TherapistDashboardResponse>> getDashboard(
            @PathVariable Long therapistId,
            @RequestParam(required = false) String search) {
        
        TherapistDashboardResponse response = therapistService.getDashboard(therapistId, search);
        return ResponseEntity.ok(ApiResponse.success(response));
    }

    // 환자 클릭 시 리포트 정보 조회
    @GetMapping("/patient/{patientId}/report")
    public ResponseEntity<ApiResponse<PatientReportResponse>> getPatientReport(@PathVariable Long patientId) {
        
        PatientReportResponse response = therapistService.getPatientReport(patientId);
        return ResponseEntity.ok(ApiResponse.success(response));
    }
}