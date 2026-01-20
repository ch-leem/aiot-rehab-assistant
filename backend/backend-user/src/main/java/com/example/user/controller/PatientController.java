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
    public ResponseEntity<PatientResponse> getPatient(@PathVariable Long patientId) {
        return ResponseEntity.ok(patientService.getPatientDetail(patientId));
    }

    @GetMapping("/{patientId}/sequences")
    public ResponseEntity<List<SequenceResponse>> getPatientSequences(@PathVariable Long patientId) {
        return ResponseEntity.ok(sequenceService.getPatientSequences(patientId));
    }

    @GetMapping("/sequences/{sequenceId}")
    public ResponseEntity<SequenceDetailResponse> getSequenceDetail(@PathVariable Long sequenceId) {
        return ResponseEntity.ok(sequenceService.getSequenceDetail(sequenceId));
    }

    @GetMapping("/sessions/{sessionId}")
    public ResponseEntity<SessionDetailResponse> getSessionDetail(@PathVariable Long sessionId) {
        return ResponseEntity.ok(sessionService.getSessionDetail(sessionId));
    }

    @GetMapping("/{patientId}/exercises")
    public ResponseEntity<List<PatientExerciseConfigResponse>> getPatientExercises(@PathVariable Long patientId) {
        return ResponseEntity.ok(exerciseService.getPatientExerciseConfigs(patientId));
    }
}