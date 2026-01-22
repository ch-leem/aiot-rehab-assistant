package com.example.iot.init;

import com.example.iot.domain.Patient;
import com.example.iot.domain.constant.Gender;
import com.example.iot.domain.constant.RehabPhase;
import com.example.iot.repository.PatientRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.time.LocalDate;
import java.util.List;

@Component
@RequiredArgsConstructor
public class PatientInitializer implements CommandLineRunner {

    private final PatientRepository patientRepository;

    @Override
    public void run(String... args) {
        if (patientRepository.count() > 0) return;

        // 예: new Patient("홍길동", LocalDate.of(1998, 3, 1), Gender.MALE, "010-....")
        Patient p1 = Patient.builder()
                .name("홍길동")
                .birthDate(LocalDate.of(1994, 5, 20))
                .gender(Gender.MALE)
                .rehabPhase(RehabPhase.MIDDLE)
                .build();
        patientRepository.save(p1);

        Patient p2 = Patient.builder()
                .name("김철수")
                .birthDate(LocalDate.of(1999, 2, 10))
                .gender(Gender.MALE)
                .rehabPhase(RehabPhase.MIDDLE)
                .build();
        patientRepository.save(p2);

    }
}