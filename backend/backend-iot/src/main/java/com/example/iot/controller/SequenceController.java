package com.example.iot.controller;

import com.example.iot.dto.request.SequenceStartRequest;
import com.example.iot.dto.response.SequenceStartResponse;
import com.example.iot.service.SequenceService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/sequence")
public class SequenceController {

    private final SequenceService sequenceService;

    public SequenceController(SequenceService sequenceService) {
        this.sequenceService = sequenceService;
    }

    @PostMapping("/{patientId}")
    public ResponseEntity<SequenceStartResponse> startSequence(
            @PathVariable Long patientId,
            @RequestBody(required = false) SequenceStartRequest body
    ) {
        SequenceStartResponse res = sequenceService.startSequence(patientId, body);
        return ResponseEntity.ok(res);
    }
}