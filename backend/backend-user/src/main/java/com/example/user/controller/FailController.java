package com.example.user.controller;

import com.example.user.service.FailService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;


@RestController
@RequiredArgsConstructor
@RequestMapping("/tries")
public class FailController {

    private final FailService failService;

    @GetMapping("/{tryId}/fail")
    public ResponseEntity<?> getFailByTry(@PathVariable Long tryId) {
        return failService.getFailIdByTryId(tryId)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }
}
