package com.example.iot.controller;

import com.example.iot.dto.response.SequenceFinishResponse;
import com.example.iot.dto.response.SessionFinishResponse;
import com.example.iot.service.FinishService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class FinishController {

    private final FinishService finishService;

    public FinishController(FinishService finishService) {
        this.finishService = finishService;
    }

    // POST /api/sessions/{sessionId}/finish
    @PostMapping("/sessions/{sessionId}/finish")
    public ResponseEntity<SessionFinishResponse> finishSession(@PathVariable Long sessionId) {
        return ResponseEntity.ok(finishService.finishSession(sessionId));
    }

    // POST /api/sequences/{sequenceId}/finish
    @PostMapping("/sequences/{sequenceId}/finish")
    public ResponseEntity<SequenceFinishResponse> finishSequence(@PathVariable Long sequenceId) {
        return ResponseEntity.ok(finishService.finishSequence(sequenceId));
    }
}