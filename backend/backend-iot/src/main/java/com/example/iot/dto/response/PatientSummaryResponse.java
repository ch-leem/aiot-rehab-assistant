package com.example.iot.dto.response;

import com.example.iot.domain.constant.RehabPhase;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Set;

public record PatientSummaryResponse (
    Long patientId,
    Long therapistId,
    String name,
    
    @JsonProperty("disease_name")
    String diseaseName, 

    @JsonProperty("rehab_phase")
    RehabPhase rehabPhase,

    String therapistName,
    Set<Long> exerciseIds
){}
