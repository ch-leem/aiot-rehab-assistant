package com.example.user.dto;

import com.example.iot.domain.Patient;
import lombok.Builder;
import lombok.Getter;

import java.time.LocalDate;
import java.time.Period;

@Getter
@Builder
public class PatientResponse {
    private Long id;
    private String name;
    private int age;
    private String gender;
    private String diseaseName;
    private String rehabPhase;

    public static PatientResponse from(Patient patient) {
        int calculatedAge = 0;
        if (patient.getBirthDate() != null) {
            calculatedAge = Period.between(patient.getBirthDate(), LocalDate.now()).getYears();
        }

        return PatientResponse.builder()
                .id(patient.getId())
                .name(patient.getName())
                .age(calculatedAge)
                .gender(patient.getGender())
                .diseaseName(patient.getDiseaseName())
                .rehabPhase(patient.getRehabPhase())
                .build();
    }
}