package com.example.iot.service;

import com.example.iot.domain.*;
import com.example.iot.domain.constant.TryResult; // Enum 추가
import com.example.iot.repository.*;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.TestPropertySource;
import org.springframework.transaction.annotation.Transactional;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.time.LocalDateTime;

import static org.assertj.core.api.Assertions.assertThat;

@SpringBootTest
@TestPropertySource(properties = {
        "spring.datasource.url=jdbc:h2:mem:testdb;DB_CLOSE_DELAY=-1;MODE=MySQL",
        "spring.datasource.driver-class-name=org.h2.Driver",
        "spring.datasource.username=sa",
        "spring.datasource.password=",
        "spring.jpa.hibernate.ddl-auto=create-drop",
        "spring.jpa.database-platform=org.hibernate.dialect.H2Dialect",
        "spring.jpa.properties.hibernate.default_batch_fetch_size=100",
        "spring.jpa.show-sql=true",
        "gms.api.key=dummy",
        "gms.api.url=http://localhost:8080",
        "openai.api-key=dummy",
        "GMS_KEY=dummy",
        "ingest.base-url=http://localhost:5000",
        "spring.data.redis.host=localhost",
        "spring.data.redis.port=6379",
        "jwt.secret=test-secret-key-value-must-be-very-very-long",
        "file.upload-dir=./uploads"
})
class SequenceServiceTest {

    @Autowired SequenceService sequenceService;
    @Autowired SessionRepository sessionRepo;
    @Autowired TryRepository tryRepo;
    @Autowired SequenceRepository sequenceRepo;
    @Autowired PatientRepository patientRepo;
    @Autowired ExerciseRepository exerciseRepo;

    private void setField(Object target, String fieldName, Object value) throws Exception {
        Class<?> clazz = target.getClass();
        while (clazz != null) {
            try {
                Field field = clazz.getDeclaredField(fieldName);
                field.setAccessible(true);
                field.set(target, value);
                return;
            } catch (NoSuchFieldException e) {
                clazz = clazz.getSuperclass(); // 못 찾으면 부모 클래스에서 다시 찾음
            }
        }
        throw new NoSuchFieldException("필드를 찾을 수 없음: " + fieldName);
    }

    private <T> T createEntity(Class<T> clazz) throws Exception {
        Constructor<T> constructor = clazz.getDeclaredConstructor();
        constructor.setAccessible(true);
        return constructor.newInstance();
    }

    @Test
    @DisplayName("마지막 Try 저장 후 시퀀스 종료가 정상적으로 감지되는지 확인")
    void checkCompletionTest() throws Exception {
        // 1. Patient 저장
        Patient patient = createEntity(Patient.class);
        setField(patient, "name", "테스터");

        // 에러 방지를 위해 존재 여부를 체크하며 세팅하거나,
        // 필수값이 아닌 필드는 과감히 생략합니다.
        try { setField(patient, "gender", com.example.iot.domain.constant.Gender.MALE); } catch (Exception e) {}
        try { setField(patient, "birthDate", java.time.LocalDate.now()); } catch (Exception e) {}
        try { setField(patient, "createdAt", LocalDateTime.now()); } catch (Exception e) {}

        patient = patientRepo.saveAndFlush(patient);

        // 2. Sequence 저장
        Sequence sequence = createEntity(Sequence.class);
        setField(sequence, "patient", patient);
        setField(sequence, "startedAt", LocalDateTime.now());
        sequence = sequenceRepo.saveAndFlush(sequence);

        // 3. Exercise 저장
        Exercise exercise = createEntity(Exercise.class);
        setField(exercise, "name", "테스트운동");
        exercise = exerciseRepo.saveAndFlush(exercise);

        // 4. Session 저장
        Session session = createEntity(Session.class);
        setField(session, "sequence", sequence);
        setField(session, "exercise", exercise);
        setField(session, "totalTries", 2);
        setField(session, "goal", "0");
        session = sessionRepo.saveAndFlush(session);

        Long sequenceId = sequence.getId();

        // 5. 첫 번째 시도 (필수 필드인 result 등 추가 주입)
        Try try1 = createEntity(Try.class);
        setField(try1, "session", session);
        setField(try1, "result", TryResult.SUCCESS);
        setField(try1, "totalScore", 85.0); // "score" -> "totalScore"로 변경
        tryRepo.saveAndFlush(try1);

        // 검증 1
        sequenceService.checkSequenceCompletion(sequenceId);
        Sequence check1 = sequenceRepo.findById(sequenceId).get();
        assertThat(check1.getEndedAt()).isNull();

        // 6. 두 번째 시도 (마지막 시도)
        Try try2 = createEntity(Try.class);
        setField(try2, "session", session);
        setField(try2, "result", TryResult.SUCCESS);
        setField(try2, "totalScore", 90.0); // "score" -> "totalScore"로 변경
        tryRepo.saveAndFlush(try2);

        // 7. 종료 체크 실행
        sequenceService.checkSequenceCompletion(sequenceId);

        // 8. 최종 결과 검증
        Sequence result = sequenceRepo.findById(sequenceId).get();
        System.out.println(">>> 최종 종료 시간: " + result.getEndedAt());

        assertThat(result.getEndedAt()).isNotNull();
    }
}