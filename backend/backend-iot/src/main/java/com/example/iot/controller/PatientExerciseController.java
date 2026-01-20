package com.example.iot.controller;

import com.example.iot.domain.Exercise;
import com.example.iot.service.PatientExerciseService;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;

@RestController
@RequestMapping("/api/patients")
public class PatientExerciseController {
    private final PatientExerciseService patientExerciseService;

    public PatientExerciseController(PatientExerciseService service) {
        this.patientExerciseService = service;
    }

    // 환자의 운동 목록 조회
    @GetMapping("/{patientId}/exercises")
    public List<Exercise> getPatientExercises(@PathVariable Long patientId) {
        return patientExerciseService.getExercisesByPatient(patientId);
    }

}
