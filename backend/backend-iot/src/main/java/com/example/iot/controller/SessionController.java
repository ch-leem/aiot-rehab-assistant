package com.example.iot.controller;

import com.example.iot.service.SessionService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/sessions")
@RequiredArgsConstructor
public class SessionController {

    private final SessionService sessionService;

    @PostMapping("/{sessionId}/start")
    public ResponseEntity<Void> startSession(@PathVariable Long sessionId) {
        sessionService.startSession(sessionId);
        return ResponseEntity.ok().build();
    }
}
