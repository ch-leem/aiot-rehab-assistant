package com.example.iot.service;

import com.example.iot.domain.Exercise;
import com.example.iot.domain.ExercisePatientMapping;
import com.example.iot.repository.ExercisePatientMappingRepository;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class PatientExerciseService {
    private final ExercisePatientMappingRepository exercisePatientMappingRepository;

    public PatientExerciseService(ExercisePatientMappingRepository repo) {
        this.exercisePatientMappingRepository = repo;
    }

    public List<Exercise> getExercisesByPatient(Long patientId) {
        return exercisePatientMappingRepository.findByPatient_Id(patientId)
                .stream()
                .map(ExercisePatientMapping::getExercise)
                .toList();
    }
}
