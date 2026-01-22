package com.example.user.controller;

import com.example.user.dto.*;
import com.example.user.service.ExerciseService;
import com.example.user.service.PatientService;
import com.example.user.service.SequenceService;
import com.example.user.service.SessionService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/patients")
@RequiredArgsConstructor
public class PatientController {

    private final PatientService patientService;
    private final SequenceService sequenceService;
    private final SessionService sessionService;
    private final ExerciseService exerciseService;

    @GetMapping("/{patientId}")
    public ResponseEntity<ApiResponse<PatientResponse>> getPatient(@PathVariable Long patientId) {
        PatientResponse data = patientService.getPatientDetail(patientId);
        return ResponseEntity.ok(ApiResponse.success(data));
    }

    @GetMapping("/{patientId}/sequences")
    public ResponseEntity<ApiResponse<List<SequenceResponse>>> getPatientSequences(@PathVariable Long patientId) {
        List<SequenceResponse> data = sequenceService.getPatientSequences(patientId);
        return ResponseEntity.ok(ApiResponse.success(data));
    }

    @GetMapping("/sequences/{sequenceId}")
    public ResponseEntity<ApiResponse<SequenceDetailResponse>> getSequenceDetail(@PathVariable Long sequenceId) {
        SequenceDetailResponse data = sequenceService.getSequenceDetail(sequenceId);
        return ResponseEntity.ok(ApiResponse.success(data));
    }

    @GetMapping("/sessions/{sessionId}")
    public ResponseEntity<ApiResponse<SessionDetailResponse>> getSessionDetail(@PathVariable Long sessionId) {
        SessionDetailResponse data = sessionService.getSessionDetail(sessionId);
        return ResponseEntity.ok(ApiResponse.success(data));
    }

    @GetMapping("/{patientId}/exercises")
    public ResponseEntity<ApiResponse<List<PatientExerciseConfigResponse>>> getPatientExercises(@PathVariable Long patientId) {
        List<PatientExerciseConfigResponse> data = exerciseService.getPatientExerciseConfigs(patientId);
        return ResponseEntity.ok(ApiResponse.success(data));
    }
}