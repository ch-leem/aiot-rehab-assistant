package com.example.user.controller;

import com.example.user.dto.PatientResponse;
import com.example.user.service.PatientService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/patients")
@RequiredArgsConstructor
public class PatientController {

    private final PatientService patientService;

    @GetMapping("/{patientId}")
    public ResponseEntity<PatientResponse> getPatient(@PathVariable Long patientId) {
        return ResponseEntity.ok(patientService.getPatientDetail(patientId));
    }
}