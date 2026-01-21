package com.example.iot.service;

import com.example.iot.domain.Exercise;
import com.example.iot.domain.Patient;
import com.example.iot.repository.ExerciseRepository;
import org.springframework.stereotype.Service;

@Service
public class ExerciseService {
    private final ExerciseRepository exerciseRepository;

    public ExerciseService(ExerciseRepository exerciseRepository) {
        this.exerciseRepository = exerciseRepository;
    }

    public Exercise getExercise(Long exerciseId) {
        return exerciseRepository.findById(exerciseId)
                .orElseThrow(() -> new IllegalArgumentException("운동 없음"));
    }

    //temp
    public Exercise createPatient(Exercise exercise) {
        return exerciseRepository.save(exercise);
    }
}
