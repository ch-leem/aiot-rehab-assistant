package com.example.iot.controller;

import com.example.iot.domain.Patient;
import com.example.iot.service.PatientService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/patients")
public class PatientController {
    private final PatientService patientService;

    public PatientController(PatientService patientService) {
        this.patientService = patientService;
    }


    @PostMapping
    public Patient createPatient(@RequestBody Patient patient) {
        return patientService.createPatient(patient);
    }

    // 환자 정보 조회
    @GetMapping("/{patientId}")
    public Patient getPatient(@PathVariable Long patientId) {
        return patientService.getPatient(patientId);
    }
}
