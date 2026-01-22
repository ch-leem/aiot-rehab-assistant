package com.example.user.service;

import com.example.iot.domain.Patient;
import com.example.iot.domain.SessionSummary;
import com.example.iot.domain.Therapist;
import com.example.iot.repository.PatientRepository;
import com.example.iot.repository.SessionSummaryRepository;
import com.example.iot.repository.TherapistRepository;
import com.example.user.dto.PatientReportResponse;
import com.example.user.dto.TherapistDashboardResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDate;
import java.time.Period;
import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class TherapistService {

    private final TherapistRepository therapistRepository;
    private final PatientRepository patientRepository;
    private final SessionSummaryRepository summaryRepository;

    /**
     * 치료사 대시보드 - 담당 환자 목록 조회 (검색어 포함 가능)
     */
    public TherapistDashboardResponse getDashboard(Long therapistId, String searchName) {
        Therapist therapist = therapistRepository.findById(therapistId)
                .orElseThrow(() -> new IllegalArgumentException("치료사를 찾을 수 없습니다."));

        List<Patient> patients;
        if (searchName != null && !searchName.isEmpty()) {
            patients = patientRepository.findByTherapist_IdAndNameContaining(therapistId, searchName);
        } else {
            patients = patientRepository.findByTherapist_Id(therapistId);
        }

        return TherapistDashboardResponse.builder()
                .therapistId(therapist.getId())
                .therapistName(therapist.getName())
                .patients(patients.stream().map(this::mapToListItem).collect(Collectors.toList()))
                .build();
    }

    /**
     * 특정 환자의 리포트 상세 데이터 조회
     */
    public PatientReportResponse getPatientReport(Long patientId) {
        Patient patient = patientRepository.findById(patientId)
                .orElseThrow(() -> new IllegalArgumentException("환자를 찾을 수 없습니다."));

        // 가장 최근의 요약 정보를 가져온다고 가정 (ID 기준 최신순)
        SessionSummary summary = summaryRepository.findFirstBySequence_Patient_IdOrderByIdDesc(patientId)
                .orElse(null);

        return PatientReportResponse.builder()
                .patientId(patient.getId())
                .patientName(patient.getName())
                .totalTrials(summary != null ? summary.getTotalTrials() : 0L)
                .successTrials(summary != null ? summary.getSuccessTrials() : 0L)
                .avgAngle(summary != null ? summary.getAvgAngle() : 0.0)
                .inTargetRate(summary != null ? summary.getInTargetRate() : 0.0)
                .stabilityLevel(summary != null ? summary.getStabilityLevel() : "데이터 없음")
                .build();
    }

    private TherapistDashboardResponse.PatientListItem mapToListItem(Patient patient) {
        int age = 0;
        if (patient.getBirthDate() != null) {
            age = Period.between(patient.getBirthDate(), LocalDate.now()).getYears();
        }

        return TherapistDashboardResponse.PatientListItem.builder()
                .patientId(patient.getId())
                .name(patient.getName())
                .gender(patient.getGender() != null ? patient.getGender().name() : null)
                .age(age)
                .diseaseName(patient.getDiseaseName())
                .build();
    }
}