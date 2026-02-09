package com.example.user.controller;

import com.example.user.dto.*;
import com.example.user.service.ExerciseService;
import com.example.user.service.PatientService;
import com.example.user.service.SequenceService;
import com.example.user.service.SessionService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@Tag(name = "Patient API", description = "환자 상세 정보 및 운동 데이터 조회 API")
@RestController
@RequestMapping("/api/patients")
@RequiredArgsConstructor
@CrossOrigin(origins = "http://localhost:3000")
public class PatientController {

    private final PatientService patientService;
    private final SequenceService sequenceService;
    private final SessionService sessionService;
    private final ExerciseService exerciseService;

    @Operation(summary = "환자 기본 정보 조회", description = "환자 ID로 프로필 및 기본 정보를 조회합니다.")
    @GetMapping("/{patientId}")
    public ResponseEntity<ApiResponse<PatientResponse>> getPatient(@PathVariable Long patientId) {
        PatientResponse data = patientService.getPatientDetail(patientId);
        return ResponseEntity.ok(ApiResponse.success(data));
    }

    @Operation(summary = "환자의 모든 시퀀스 목록 조회", description = "특정 환자에게 할당된 전체 운동 시퀀스(처방) 리스트를 가져옵니다.")
    @GetMapping("/{patientId}/sequences")
    public ResponseEntity<ApiResponse<List<SequenceResponse>>> getPatientSequences(@PathVariable Long patientId) {
        List<SequenceResponse> data = sequenceService.getPatientSequences(patientId);
        return ResponseEntity.ok(ApiResponse.success(data));
    }

    @Operation(summary = "시퀀스 상세 정보 및 세션 목록 조회", description = "특정 시퀀스 ID에 포함된 상세 정보와 하위 세션 리스트를 조회합니다.")
    @GetMapping("/sequences/{sequenceId}")
    public ResponseEntity<ApiResponse<SequenceDetailResponse>> getSequenceDetail(@PathVariable Long sequenceId) {
        SequenceDetailResponse data = sequenceService.getSequenceDetail(sequenceId);
        return ResponseEntity.ok(ApiResponse.success(data));
    }

    @Operation(summary = "세션 상세 데이터 조회", description = "특정 세션(단일 운동 기록)의 상세 결과 및 그래프 데이터를 조회합니다.")
    @GetMapping("/sessions/{sessionId}")
    public ResponseEntity<ApiResponse<SessionDetailResponse>> getSessionDetail(@PathVariable Long sessionId) {
        SessionDetailResponse data = sessionService.getSessionDetail(sessionId);
        return ResponseEntity.ok(ApiResponse.success(data));
    }

    @Operation(summary = "환자별 운동 설정 조회", description = "환자에게 할당된 운동 종류와 각 운동의 가동 범위(ROM) 등 설정값을 조회합니다.")
    @GetMapping("/{patientId}/exercises")
    public ResponseEntity<ApiResponse<List<PatientExerciseConfigResponse>>> getPatientExercises(@PathVariable Long patientId) {
        List<PatientExerciseConfigResponse> data = exerciseService.getPatientExerciseConfigs(patientId);
        return ResponseEntity.ok(ApiResponse.success(data));
    }
}