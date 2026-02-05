package com.example.iot.service;

import com.example.iot.domain.*;
import com.example.iot.dto.request.SequenceStartRequest;
import com.example.iot.dto.response.SequenceStartResponse;
import com.example.iot.dto.response.SessionTryResponse;
import com.example.iot.repository.*;
import jakarta.transaction.Transactional;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionSynchronization;
import org.springframework.transaction.support.TransactionSynchronizationManager;

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

        // 1. 모든 세션이 끝났는지 확인 (예: 10/10, 10/10 ...)
        boolean isAllFinished = sessions.stream().allMatch(s -> {
            // 이 세션에 속한 트라이 중 아직 끝나지 않은(endedAt IS NULL) 트라이가 있는지 확인
            boolean hasUnfinishedTry = tryRepo.existsBySession_IdAndEndedAtIsNull(s.getId());
            return !hasUnfinishedTry;
        });

        // 2. 조건이 맞으면 이미 작성하신 '마감 실행' 메서드 호출
        log.info("시퀀스 완료 체크 - ID: {}, 완료여부: {}", sequenceId, isAllFinished);

        if (isAllFinished) {
            this.completeSequence(sequenceId);
        }
    }

    @Transactional
    public void completeSequence(Long sequenceId) {
        log.info("!!! 리포트 생성 트리거 진입 !!!");
        Sequence sequence = sequenceRepo.findById(sequenceId)
                .orElseThrow(() -> new IllegalArgumentException("Sequence not found: " + sequenceId));

        // 1. 종료 시간 기록 (마감 처리)
        if (sequence.getEndedAt() == null) {
            sequence.setEndedAt(LocalDateTime.now());
            sequenceRepo.saveAndFlush(sequence);
            log.info("Sequence 종료 시간 저장 완료");
        }

        // 2. DB 트랜잭션이 완전히 '커밋'된 후 AI 리포트 생성을 시작합니다.
        reportService.createAndSaveReport(sequenceId);
        log.info("리포트 생성 비동기 호출 완료 - 호출 후 메서드 종료");
    }
}