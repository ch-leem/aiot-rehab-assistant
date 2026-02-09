package com.example.user.service;

import com.example.iot.domain.Patient;
import com.example.iot.domain.Sequence;
import com.example.iot.repository.SequenceRepository;
import com.example.iot.repository.SessionRepository;
import com.example.iot.repository.SessionSummaryRepository;
import com.example.user.dto.SequenceResponse;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.InjectMocks;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.BDDMockito.given;

@ExtendWith(MockitoExtension.class)
class SequenceServiceTest {

    @Mock private SequenceRepository sequenceRepository;
    @Mock private SessionSummaryRepository summaryRepository;
    @Mock private SessionRepository sessionRepository;

    @InjectMocks
    private SequenceService sequenceService;

    @Test
    @DisplayName("환자 ID로 시퀀스 목록을 조회하면 DTO 리스트로 변환된다")
    void getPatientSequencesTest() {
        // given
        Long patientId = 1L;
        Patient patient = Patient.builder()
                .id(patientId)
                .name("홍길동")
                .birthDate(null)
                .gender(null)
                .diseaseName(null)
                .rehabPhase(null)
                .createdAt(null)
                .build();

        // 1. 존재하는 생성자 public Sequence(Patient patient) 사용
        Sequence seq1 = new Sequence(patient);
        seq1.setId(101L);      // Setter 활용
        seq1.setFeedback("피드백1");

        Sequence seq2 = new Sequence(patient);
        seq2.setId(102L);      // Setter 활용
        seq2.setFeedback("피드백2");

        given(sequenceRepository.findByPatient_IdOrderByStartedAtDesc(patientId))
                .willReturn(List.of(seq2, seq1));

        // when
        List<SequenceResponse> responses = sequenceService.getPatientSequences(patientId);

        // then
        assertThat(responses).hasSize(2);
        assertThat(responses.get(0).getFeedback()).isEqualTo("피드백2");
    }
}