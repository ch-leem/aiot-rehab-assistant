package com.example.iot.init;

import com.example.iot.domain.Therapist;
import com.example.iot.repository.TherapistRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.stereotype.Component;

import java.util.List;

@Component
@RequiredArgsConstructor
public class TherapistInitializer implements CommandLineRunner {

    private final TherapistRepository therapistRepository;

    @Override
    public void run(String... args) {

        if(therapistRepository.count() > 0) return;
        // ⚠️ 엔티티 생성자/필드 맞춰 조정
        // 예: new Therapist("관리자", "admin@rehab.local", Role.ADMIN, "LIC-0001")
        List<Therapist> therapists = List.of(
                new Therapist("관리자", "1"),
                new Therapist("테스트치료사", "2")
        );

        therapistRepository.saveAll(therapists);
    }
}