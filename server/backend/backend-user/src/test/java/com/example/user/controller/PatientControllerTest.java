package com.example.user.controller;

import com.example.user.dto.*;
import com.example.user.service.ExerciseService;
import com.example.user.service.PatientService;
import com.example.user.service.SequenceService;
import com.example.user.service.SessionService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.autoconfigure.ImportAutoConfiguration;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import java.util.List;

import static org.mockito.BDDMockito.given;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultHandlers.print;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@WebMvcTest(PatientController.class)
@ImportAutoConfiguration(exclude = {
        org.springframework.boot.autoconfigure.orm.jpa.HibernateJpaAutoConfiguration.class,
        org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration.class
})
class PatientControllerTest {

    @Autowired
    private MockMvc mockMvc;

    // 스프링 부트 3.4+ 최신 방식: @MockBean 대신 @MockitoBean 사용
    @MockitoBean private PatientService patientService;
    @MockitoBean private SequenceService sequenceService;
    @MockitoBean private ExerciseService exerciseService;
    @MockitoBean private SessionService sessionService;

    @Test
    @DisplayName("1. 환자 상세 정보 조회 API 테스트")
    void getPatientDetailTest() throws Exception {
        Long patientId = 1L;
        PatientResponse response = PatientResponse.builder()
                .name("홍길동")
                .age(30)
                .diseaseName("뇌졸중")
                .build();

        given(patientService.getPatientDetail(patientId)).willReturn(response);

        mockMvc.perform(get("/api/patients/{patientId}", patientId))
                .andDo(print())
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.name").value("홍길동"))
                .andExpect(jsonPath("$.age").value(30));
    }

    @Test
    @DisplayName("2. 환자 맞춤 운동 설정 조회 API 테스트")
    void getPatientExercisesTest() throws Exception {
        Long patientId = 1L;
        PatientExerciseConfigResponse config = PatientExerciseConfigResponse.builder()
                .exerciseName("무릎 굽히기")
                .side("Left")
                .build();

        given(exerciseService.getPatientExerciseConfigs(patientId)).willReturn(List.of(config));

        mockMvc.perform(get("/api/patients/{patientId}/exercises", patientId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].exerciseName").value("무릎 굽히기"))
                .andExpect(jsonPath("$[0].side").value("Left"));
    }

    @Test
    @DisplayName("3. 환자별 시퀀스(회차) 목록 조회 API 테스트")
    void getPatientSequencesTest() throws Exception {
        Long patientId = 1L;
        SequenceResponse seq = SequenceResponse.builder()
                .sequenceId(100L)
                .feedback("매우 양호")
                .build();

        given(sequenceService.getPatientSequences(patientId)).willReturn(List.of(seq));

        mockMvc.perform(get("/api/patients/{patientId}/sequences", patientId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$[0].sequenceId").value(100))
                .andExpect(jsonPath("$[0].feedback").value("매우 양호"));
    }

    @Test
    @DisplayName("4. 특정 시퀀스 상세 정보 조회 API 테스트")
    void getSequenceDetailTest() throws Exception {
        Long sequenceId = 100L;
        SequenceDetailResponse detail = SequenceDetailResponse.builder()
                .sequenceId(sequenceId)
                .feedback("회복 속도가 빠릅니다")
                .build();

        given(sequenceService.getSequenceDetail(sequenceId)).willReturn(detail);

        mockMvc.perform(get("/api/patients/sequences/{sequenceId}", sequenceId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.sequenceId").value(100))
                .andExpect(jsonPath("$.feedback").value("회복 속도가 빠릅니다"));
    }

    @Test
    @DisplayName("5. 특정 세션 상세 시도(Try) 기록 조회 API 테스트")
    void getSessionDetailTest() throws Exception {
        Long sessionId = 500L;
        SessionDetailResponse sessionDetail = SessionDetailResponse.builder()
                .sessionId(sessionId)
                .exerciseName("팔 벌리기")
                .goal("10회")
                .build();

        given(sessionService.getSessionDetail(sessionId)).willReturn(sessionDetail);

        mockMvc.perform(get("/api/patients/sessions/{sessionId}", sessionId))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.sessionId").value(500))
                .andExpect(jsonPath("$.exerciseName").value("팔 벌리기"));
    }
}