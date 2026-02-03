package com.example.user.controller;

import com.example.user.dto.FailedTryIdsResponse;
import com.example.user.service.SessionTryQueryService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequiredArgsConstructor
@RequestMapping("/sessions")
public class SessionTryController {

    private final SessionTryQueryService sessionTryQueryService;

    @GetMapping("/{sessionId}/failed-tries")
    public FailedTryIdsResponse getFailedTries(@PathVariable Long sessionId) {
        return sessionTryQueryService.getFailedTryIds(sessionId);
    }
}