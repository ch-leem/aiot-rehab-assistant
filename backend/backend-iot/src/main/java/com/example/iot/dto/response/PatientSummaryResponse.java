package com.example.iot.dto.response;

import com.example.iot.domain.constant.RehabPhase;

import java.util.List;

public record PatientSummaryResponse (
    Long patientId,
    Long therapistId,
    String name,
    String disease_name,
    RehabPhase rehab_phase,
    String therapistName,
    List<Long> exerciseIds
){}
