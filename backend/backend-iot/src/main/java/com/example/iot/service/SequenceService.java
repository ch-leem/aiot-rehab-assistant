package com.example.iot.service;

import com.example.iot.domain.*;
import com.example.iot.dto.request.SequenceStartRequest;
import com.example.iot.dto.response.SequenceStartResponse;
import com.example.iot.dto.response.SessionTryResponse;
import com.example.iot.repository.*;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
public class SequenceService {

    private static final int DEFAULT_TRY_COUNT = 10;

    private final PatientRepository patientRepo;
    private final ExercisePatientMappingRepository mappingRepo;
    private final SequenceRepository sequenceRepo;
    private final SessionRepository sessionRepo;
    private final TryRepository tryRepo;

    public SequenceService(
            PatientRepository patientRepo,
            ExercisePatientMappingRepository mappingRepo,
            SequenceRepository sequenceRepo,
            SessionRepository sessionRepo,
            TryRepository tryRepo
    ) {
        this.patientRepo = patientRepo;
        this.mappingRepo = mappingRepo;
        this.sequenceRepo = sequenceRepo;
        this.sessionRepo = sessionRepo;
        this.tryRepo = tryRepo;
    }

    @Transactional
    public SequenceStartResponse startSequence(Long patientId, SequenceStartRequest request) {

        int tryCount = (request != null && request.tryCount() != null)
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

        List<SessionTryResponse> sessionResponses = new ArrayList<>();

        // 2) Session + Try 생성
        for (ExercisePatientMapping m : mappings) {

            Session session = sessionRepo.save(
                    new Session(sequence, m.getExercise())
            );

            List<Try> tries = new ArrayList<>();
            for (int i = 1; i <= tryCount; i++) {
                tries.add(new Try(session));
            }

            // saveAll 후에 try.id 채워짐
            List<Try> savedTries = tryRepo.saveAll(tries);

            List<Long> tryIds = savedTries.stream()
                    .map(Try::getId)
                    .toList();

            sessionResponses.add(
                    new SessionTryResponse(session.getId(), tryIds)
            );
        }

        return new SequenceStartResponse(
                sequence.getId(),
                sessionResponses
        );
    }
}