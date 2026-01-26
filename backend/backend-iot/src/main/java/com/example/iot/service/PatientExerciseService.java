package com.example.iot.service;

import com.example.iot.domain.*;
import com.example.iot.domain.constant.Side;
import com.example.iot.dto.request.PatientExerciseAssignRequest;
import com.example.iot.repository.*;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
public class PatientExerciseService {

    private final ExercisePatientMappingRepository exercisePatientMappingRepository;
    private final PatientRepository patientRepository;
    private final ExerciseRepository exerciseRepository;
    private final ExerciseGoalRepository exerciseGoalRepository;

    /**
     * 특정 환자에게 할당된 '중복되지 않은' 운동 목록 조회
     */
    public List<Exercise> getExercisesByPatient(Long patientId) {
        return exercisePatientMappingRepository.findByPatient_Id(patientId)
                .stream()
                .map(ExercisePatientMapping::getExercise)
                .distinct() // 목표별로 여러 행이 존재하므로 중복 제거가 필수입니다.
                .toList();
    }

    /**
     * 환자에게 운동 할당
     * 운동에 정의된 모든 목표(ExerciseGoal)를 환자별 매핑 테이블에 개별 저장합니다.
     */
    @Transactional
    public void addExerciseToPatient(
            Long patientId,
            Long exerciseId,
            PatientExerciseAssignRequest request
    ) {
        // 1. 환자 및 운동 존재 여부 검증
        Patient patient = patientRepository.findById(patientId)
                .orElseThrow(() -> new IllegalArgumentException("환자를 찾을 수 없습니다. ID: " + patientId));

        Exercise exercise = exerciseRepository.findById(exerciseId)
                .orElseThrow(() -> new IllegalArgumentException("운동을 찾을 수 없습니다. ID: " + exerciseId));

        // 2. 해당 운동의 표준 목표 리스트 조회
        List<ExerciseGoal> goals = exerciseGoalRepository.findByExercise(exercise);

        if (goals.isEmpty()) {
            throw new IllegalStateException("해당 운동에 설정된 목표(ExerciseGoal)가 없습니다.");
        }

        // 3. 각 목표별로 환자 맞춤형 매핑 생성 및 저장
        for (ExerciseGoal goal : goals) {
            // DTO의 맞춤 설정 리스트에서 현재 목표(goal_id)에 해당하는 수치가 있는지 검색
            // (참고: Request DTO에 List<CustomGoalRequest> 형태의 필드가 있다고 가정)
            Double customValue = null;
            if (request.getCustomGoals() != null) {
                customValue = request.getCustomGoals().stream()
                        .filter(cg -> cg.getGoalId().equals(goal.getGoalId()))
                        .map(PatientExerciseAssignRequest.CustomGoalRequest::getCustomTargetValue)
                        .findFirst()
                        .orElse(null); // 맞춤 수치가 없으면 null 유지 (나중에 기본값 사용)
            }

            ExercisePatientMapping mapping = new ExercisePatientMapping(
                    exercise,
                    patient,
                    goal,
                    request.getSide(),
                    customValue
            );

            exercisePatientMappingRepository.save(mapping);
        }
    }
}