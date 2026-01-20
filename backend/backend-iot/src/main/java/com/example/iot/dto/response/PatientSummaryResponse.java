package com.example.iot.dto.response;

import java.util.List;

public record PatientSummaryResponse (
    Long patientId,
    Long therapistId,
    String name,
    String disease_name,
    String rehab_phase,
    String therapistName,
    List<Long> exerciseIds
){}
