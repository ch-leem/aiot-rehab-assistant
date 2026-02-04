package com.example.iot.controller;

import com.example.iot.domain.Exercise;
import com.example.iot.domain.Patient;
import com.example.iot.service.ExerciseService;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/exercises")
public class ExerciseController {
    private final ExerciseService exerciseService;

    private ExerciseController(ExerciseService exerciseService) {
        this.exerciseService = exerciseService;
    }

    public static ExerciseController createExerciseController(ExerciseService exerciseService) {
        return new ExerciseController(exerciseService);
    }

    // 운동 정보 조회
    @GetMapping("/{exerciseId}")
    public Exercise getExercise(@PathVariable Long exerciseId) {
        return exerciseService.getExercise(exerciseId);
    }

    //운동 추가
    @PostMapping
    public Exercise createPatient(@RequestBody Exercise exercise) {
        return exerciseService.createPatient(exercise);
    }
}
