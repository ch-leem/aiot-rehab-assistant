package com.example.iot.service;

import com.example.iot.domain.ExercisePatientMapping;
import com.example.iot.domain.Patient;
import com.example.iot.domain.Therapist;
import com.example.iot.dto.response.PatientSummaryResponse;
import com.example.iot.repository.ExercisePatientMappingRepository;
import com.example.iot.repository.PatientRepository;
import com.example.iot.repository.TherapistRepository;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class PatientService {

    private final PatientRepository patientRepository;
    private final TherapistRepository therapistRepository;
    private final ExercisePatientMappingRepository exercisePatientMappingRepository;

    public PatientService(PatientRepository patientRepository,
                          TherapistRepository therapistRepository,
                          ExercisePatientMappingRepository exercisePatientMappingRepository) {
        this.patientRepository = patientRepository;
        this.therapistRepository = therapistRepository;
        this.exercisePatientMappingRepository = exercisePatientMappingRepository;
    }

    public Patient getPatient(Long patientId) {
        return patientRepository.findById(patientId)
                .orElseThrow(() -> new IllegalArgumentException("환자 없음"));
    }

    public Patient createPatient(Patient patient) {
        return patientRepository.save(patient);
    }

    public PatientSummaryResponse getPatientSummary(Long patientId, Long therapistId) {

        // 1) 환자 조회 (치료사 검증 없음)
        Patient patient = patientRepository.findById(patientId)
                .orElseThrow(() -> new IllegalArgumentException("Patient not found: " + patientId));

        // 2) 치료사 이름 조회 (요청으로 받은 therapistId 기준)
        Therapist therapist = therapistRepository.findById(therapistId)
                .orElseThrow(() -> new IllegalArgumentException("Therapist not found: " + therapistId));

        // 3) 환자 운동 ID 리스트 조회
        List<Long> exerciseIds = exercisePatientMappingRepository.findExerciseIdsByPatientId(patientId);

        // 4) DTO로 반환
        return new PatientSummaryResponse(
                patient.getId(),
                therapistId,
                patient.getName(),
                patient.getDiseaseName(),
                patient.getRehabPhase(),
                therapist.getName(),
                exerciseIds
        );
    }

}
