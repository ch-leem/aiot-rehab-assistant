package com.example.iot.controller;

import com.example.iot.dto.response.TryFinishResponse;
import com.example.iot.service.TryService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/tries")
public class TryController {

    private final TryService tryService;

    public TryController(TryService tryService) {
        this.tryService = tryService;
    }

    @PostMapping("/{tryId}/finish")
    public ResponseEntity<TryFinishResponse> finish(@PathVariable Long tryId) {
        return ResponseEntity.ok(tryService.finishTry(tryId));
    }

}