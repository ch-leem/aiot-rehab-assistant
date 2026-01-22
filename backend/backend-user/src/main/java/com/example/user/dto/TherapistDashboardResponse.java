package com.example.user.dto;

import lombok.Builder;
import lombok.Getter;
import java.util.List;

@Getter
@Builder
public class TherapistDashboardResponse {
    private Long therapistId;
    private String therapistName;
    private List<PatientListItem> patients;

    @Getter
    @Builder
    public static class PatientListItem {
        private Long patientId;
        private String name;
        private String gender;
        private int age;
        private String diseaseName;
    }
}