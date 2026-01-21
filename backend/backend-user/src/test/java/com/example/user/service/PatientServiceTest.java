package com.example.user.service;

import com.example.iot.domain.Patient;
import com.example.iot.repository.PatientRepository;
import com.example.user.dto.PatientResponse;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.util.Optional;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.BDDMockito.given;

@ExtendWith(MockitoExtension.class)
class PatientServiceTest {

    @Mock
    private PatientRepository patientRepository;

    @InjectMocks
    private PatientService patientService;

    @Test
    @DisplayName("환자 ID로 상세 정보를 조회하면 나이가 계산되어 반환된다")
    void getPatientDetailTest() {
        // given
        Long patientId = 1L;
        LocalDate birthDate = LocalDate.now().minusYears(30);

        // 필드 순서: id, name, birthDate, gender, diseaseName, rehabPhase, createdAt
        Patient patient = new Patient(
                patientId,
                "홍길동",
                birthDate,
                "M",
                "뇌졸중",
                "회복기",
                LocalDateTime.now() // createdAt 자리
        );

        given(patientRepository.findById(patientId)).willReturn(Optional.of(patient));

        // when
        PatientResponse response = patientService.getPatientDetail(patientId);

        // then
        assertThat(response.getAge()).isEqualTo(30);
    }
}