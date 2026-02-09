package com.example.iot.controller;

import com.example.iot.dto.response.RecentGoalsByExerciseResponse;
import com.example.iot.service.RecentGoalsService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/sequences")
public class RecentGoalsController {

    private final RecentGoalsService recentGoalsService;

    public RecentGoalsController(RecentGoalsService recentGoalsService) {
        this.recentGoalsService = recentGoalsService;
    }

    @GetMapping("/{patientId}/{currentSequenceId}/goals/recent")
    public ResponseEntity<RecentGoalsByExerciseResponse> recent5Goals(
            @PathVariable Long patientId,
            @PathVariable Long currentSequenceId
    ) {
        return ResponseEntity.ok(
                recentGoalsService.getRecent5GoalsByExercise(patientId, currentSequenceId)
        );
    }
}