package com.example.iot.service;

import com.example.iot.domain.Exercise;
import com.example.iot.domain.ExercisePatientMapping;
import com.example.iot.domain.Patient;
import com.example.iot.domain.constant.Side;
import com.example.iot.dto.request.PatientExerciseAssignRequest;
import com.example.iot.repository.ExercisePatientMappingRepository;
import com.example.iot.repository.ExerciseRepository;
import com.example.iot.repository.PatientRepository;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
public class PatientExerciseService {
    private final ExercisePatientMappingRepository exercisePatientMappingRepository;
    private final PatientRepository patientRepository;
    private final ExerciseRepository exerciseRepository;

    public PatientExerciseService(
            ExercisePatientMappingRepository patientExerciseRepository,
            PatientRepository patientRepository,
            ExerciseRepository exerciseRepository) {
        this.exercisePatientMappingRepository = patientExerciseRepository;
        this.patientRepository = patientRepository;
        this.exerciseRepository = exerciseRepository;
    }

    public List<Exercise> getExercisesByPatient(Long patientId) {
        return exercisePatientMappingRepository.findByPatient_Id(patientId)
                .stream()
                .map(ExercisePatientMapping::getExercise)
                .toList();
    }

    @Transactional
    public void addExerciseToPatient(
            Long patientId,
            Long exerciseId,
            PatientExerciseAssignRequest request
    ) {
        Patient patient = patientRepository.findById(patientId)
                .orElseThrow(() -> new IllegalArgumentException("환자를 찾을 수 없습니다."));

        Exercise exercise = exerciseRepository.findById(exerciseId)
                .orElseThrow(() -> new IllegalArgumentException("운동을 찾을 수 없습니다."));

        Side side = Side.valueOf(request.getSide().toUpperCase());

        ExercisePatientMapping mapping = new ExercisePatientMapping(exercise, patient, side);

        mapping.setGoalSensor(request.getGoalSensor());
        mapping.setGoalVision(request.getGoalVision());

        exercisePatientMappingRepository.save(mapping);
    }
}

