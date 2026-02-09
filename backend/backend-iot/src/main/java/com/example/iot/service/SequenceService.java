package com.example.iot.service;

import com.example.iot.domain.*;
import com.example.iot.dto.request.SequenceStartRequest;
import com.example.iot.dto.response.SequenceStartResponse;
import com.example.iot.dto.response.SessionTryResponse;
import com.example.iot.repository.*;
import jakarta.transaction.Transactional;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;
import java.util.*;

@Slf4j
@Service
public class SequenceService {

    private static final int DEFAULT_TRY_COUNT = 10;

    private final PatientRepository patientRepo;
    private final ExercisePatientMappingRepository mappingRepo;
    private final SequenceRepository sequenceRepo;
    private final SessionRepository sessionRepo;
    private final TryRepository tryRepo;
    private final PatientRehabReportService reportService;

    public SequenceService(
            PatientRepository patientRepo,
            ExercisePatientMappingRepository mappingRepo,
            SequenceRepository sequenceRepo,
            SessionRepository sessionRepo,
            TryRepository tryRepo,
            PatientRehabReportService reportService
    ) {
        this.patientRepo = patientRepo;
        this.mappingRepo = mappingRepo;
        this.sequenceRepo = sequenceRepo;
        this.sessionRepo = sessionRepo;
        this.tryRepo = tryRepo;
        this.reportService = reportService;
    }

    @Transactional
    public SequenceStartResponse startSequence(Long patientId, SequenceStartRequest request) {

        int finalTryCount = (request != null && request.tryCount() != null)
                ? request.tryCount()
                : DEFAULT_TRY_COUNT;

        Patient patient = patientRepo.findById(patientId)
                .orElseThrow(() -> new IllegalArgumentException("Patient not found: " + patientId));

        List<ExercisePatientMapping> mappings =
                mappingRepo.findByPatient_Id(patientId);

        if (mappings.isEmpty()) {
            throw new IllegalStateException("No exercises mapped for patientId=" + patientId);
        }

        // 1) Sequence 생성
        Sequence sequence = sequenceRepo.save(new Sequence(patient));
        Set<Exercise> exerciseSet = new TreeSet<>((o1, o2) -> (int) (o1.getId() - o2.getId()));
        for(ExercisePatientMapping m : mappings) {
            exerciseSet.add(m.getExercise());
        }

        List<SessionTryResponse> sessionResponses = new ArrayList<>();

        // 2) Session + Try 생성
        for (Exercise m : exerciseSet) {
            Session session = new Session(sequence, m);
            session.setTotalTries(finalTryCount);
            session = sessionRepo.save(session);

            List<Try> tries = new ArrayList<>();
            for (int i = 1; i <= finalTryCount; i++) {
                tries.add(new Try(session));
            }

            // saveAll 후에 try.id 채워짐
            List<Try> savedTries = tryRepo.saveAll(tries);

            List<Long> tryIds = savedTries.stream()
                    .map(Try::getId)
                    .toList();

            sessionResponses.add(new SessionTryResponse(session.getId(), tryIds));
        }

        tryRepo.flush();

        return new SequenceStartResponse(sequence.getId(), sessionResponses);
    }

    @Transactional
    public void checkSequenceCompletion(Long sequenceId) {
        List<Session> sessions = sessionRepo.findAllDetailBySequenceId(sequenceId);

        // 1. 전체 목표 개수 계산
        long totalTargetCount = sessions.stream()
                .mapToLong(Session::getTotalTries)
                .sum();

        // 2. 실제 완료된(endedAt이 찍힌) 트라이 개수 확인 (Repository에 메서드 추가 필요)
        long finishedCount = tryRepo.countBySession_Sequence_IdAndEndedAtIsNotNull(sequenceId);

        log.info("시퀀스 완료 체크 - ID: {}, 진행: {}/{}", sequenceId, finishedCount, totalTargetCount);

        // 3. 목표치에 근접했거나(유령 트라이 감안 -2) 모두 완료되면 종료
        // (프런트엔드 누락 이슈 방어 로직)
        if (finishedCount >= totalTargetCount - 2) {
            this.completeSequence(sequenceId);
        }
    }

    @Transactional
    public void completeSequence(Long sequenceId) {
        log.info("!!! 리포트 생성 트리거 진입 - 락 획득 시도 !!!");

        // 1. 락 획득 (여기서 동시 요청들은 대기 상태가 됨)
        Sequence sequence = sequenceRepo.findByIdWithLock(sequenceId)
                .orElseThrow(() -> new IllegalArgumentException("Sequence not found"));

        // 2. 이미 처리되었는지 확인 (Check)
        if (sequence.getEndedAt() != null) {
            log.warn("이미 처리된 시퀀스입니다. (중복 요청 방어)");
            return;
        }

        // 3. 종료 마킹 (Act)
        sequence.setEndedAt(LocalDateTime.now());
        // saveAndFlush는 @Transactional 안에서 불필요하지만 명시적으로 둬도 무방함

        log.info("Sequence 종료 마킹 완료. 리포트 생성 시작.");

        // 4. 리포트 생성 호출
        // (트랜잭션이 커밋되면서 락이 풀리고, 비동기 스레드는 작업을 이어감)
        reportService.createAndSaveReport(sequenceId);
    }
}