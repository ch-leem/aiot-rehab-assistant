package com.example.user.config;

import com.example.iot.domain.Device;
import com.example.iot.domain.Patient;
import com.example.iot.repository.DeviceRepository;
import com.example.iot.repository.PatientRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.boot.CommandLineRunner;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.time.LocalDate;

@Configuration
@RequiredArgsConstructor
public class DataInitConfig {

    private final PatientRepository patientRepository;
    private final DeviceRepository deviceRepository;

    @Bean
    public CommandLineRunner initData() {
        return args -> {
            // 1. Builder 패턴을 사용하여 Patient 가짜 데이터 생성
            // Patient 엔티티에 @Builder가 선언되어 있어야 합니다.
            Patient p1 = Patient.builder()
                    .name("홍길동")
                    .birthDate(LocalDate.of(1994, 5, 20))
                    .gender("M")
                    .rehabPhase("mid")
                    .build();
            patientRepository.save(p1);

            Patient p2 = Patient.builder()
                    .name("김철수")
                    .birthDate(LocalDate.of(1999, 2, 10))
                    .gender("M")
                    .rehabPhase("mid")
                    .build();
            patientRepository.save(p2);

            System.out.println(">>> [backend-user] 테스트용 가짜 데이터 삽입 성공!");
        };
    }
}