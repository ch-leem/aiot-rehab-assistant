package com.example.iot.controller;

import com.example.iot.dto.response.SequenceCompareResponse;
import com.example.iot.service.SequenceCompareService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/sequences")
public class SequenceCompareController {

    private final SequenceCompareService sequenceCompareService;

    public SequenceCompareController(SequenceCompareService sequenceCompareService) {
        this.sequenceCompareService = sequenceCompareService;
    }

    /**
     * 현재 시퀀스 기준으로 이전 시퀀스와 goal 비교
     *
     * POST /api/sequences/{patientId}/{currentSequenceId}/compare-previous
     */
    @PostMapping("/{patientId}/{currentSequenceId}/compare-previous")
    public ResponseEntity<SequenceCompareResponse> compareWithPrevious(
            @PathVariable Long patientId,
            @PathVariable Long currentSequenceId
    ) {
        SequenceCompareResponse response =
                sequenceCompareService.compareWithPrevious(patientId, currentSequenceId);

        return ResponseEntity.ok(response);
    }
}