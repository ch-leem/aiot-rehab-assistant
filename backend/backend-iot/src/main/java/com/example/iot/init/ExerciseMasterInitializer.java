package com.example.iot.init;

import com.example.iot.domain.Exercise;
import com.example.iot.domain.Sensor;
import com.example.iot.repository.ExerciseRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
@RequiredArgsConstructor
public class ExerciseMasterInitializer implements CommandLineRunner {

    private final ExerciseRepository exerciseRepository;

    @Override
    public void run(String... args) {

        if(exerciseRepository.count() > 0) return;

        List<Exercise> exercises = List.of(
                new Exercise("한 쪽 발로 서기", "한 쪽 발로 잘 설 수 있는지를 확인해봅시다."),
                new Exercise("앞으로 숙이기", "전신 운동")
        );

        exerciseRepository.saveAll(exercises);
    }
}
