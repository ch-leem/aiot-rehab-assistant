package com.example.iot.controller;

import com.example.iot.dto.request.SequenceStartRequest;
import com.example.iot.dto.response.SequenceStartResponse;
import com.example.iot.dto.response.SessionTryCountResponse;
import com.example.iot.service.SequenceAverageService;
import com.example.iot.service.SequenceService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.math.BigDecimal;
import java.util.List;

@RestController
@RequestMapping("/api/sequence")
public class SequenceController {

    private final SequenceService sequenceService;

    private final SequenceAverageService sequenceAverageService;

    public SequenceController(
            SequenceService sequenceService,
            SequenceAverageService sequenceAverageService
                              ) {
        this.sequenceService = sequenceService;
        this.sequenceAverageService = sequenceAverageService;
    }

    @PostMapping("/{patientId}")
    public ResponseEntity<SequenceStartResponse> startSequence(
            @PathVariable Long patientId,
            @RequestBody(required = false) SequenceStartRequest body
    ) {
        SequenceStartResponse res = sequenceService.startSequence(patientId, body);
        return ResponseEntity.ok(res);
    }

    @GetMapping("/{sequenceId}/average")
    public ResponseEntity<List<SessionTryCountResponse>> getSessionTryCounts(
            @PathVariable Long sequenceId
    ) {
        return ResponseEntity.ok(sequenceAverageService.getSessionTryCounts(sequenceId));
    }

}