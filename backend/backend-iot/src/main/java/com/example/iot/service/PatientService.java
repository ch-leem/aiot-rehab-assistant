package com.example.iot.service;

import com.example.iot.domain.Patient;
import com.example.iot.repository.PatientRepository;
import org.springframework.stereotype.Service;

@Service
public class PatientService {

    private final PatientRepository patientRepository;

    public PatientService(PatientRepository patientRepository) {
        this.patientRepository = patientRepository;
    }

    public Patient getPatient(Long patientId) {
        return patientRepository.findById(patientId)
                .orElseThrow(() -> new IllegalArgumentException("환자 없음"));
    }

    public Patient createPatient(Patient patient) {
        return patientRepository.save(patient);
    }
}
