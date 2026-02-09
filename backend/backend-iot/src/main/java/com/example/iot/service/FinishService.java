package com.example.iot.service;


import com.example.iot.domain.Sequence;
import com.example.iot.domain.Session;
import com.example.iot.dto.response.SequenceFinishResponse;
import com.example.iot.dto.response.SessionFinishResponse;
import com.example.iot.repository.SequenceRepository;
import com.example.iot.repository.SessionRepository;
import jakarta.transaction.Transactional;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
public class FinishService {

    private final SessionRepository sessionRepository;
    private final SequenceRepository sequenceRepository;

    public FinishService(SessionRepository sessionRepository,
                         SequenceRepository sequenceRepository) {
        this.sessionRepository = sessionRepository;
        this.sequenceRepository = sequenceRepository;
    }

    /**
     * 세션 종료:
     * - Session.endedAt 업데이트
     * - 해당 Session이 속한 Sequence.endedAt도 업데이트(요구사항)
     */
    @Transactional
    public SessionFinishResponse finishSession(Long sessionId) {
        Session session = sessionRepository.findById(sessionId)
                .orElseThrow(() -> new IllegalArgumentException("Session not found: " + sessionId));

//        Sequence seq = session.getSequence(); // Session -> Sequence 연관관계 필요
//        if (seq == null) {
//            throw new IllegalStateException("Session has no sequence. sessionId=" + sessionId);
//        }

        LocalDateTime now = LocalDateTime.now();

        // 이미 종료된 경우 재호출 정책: 그대로 반환(원하면 예외로 막아도 됨)
        if (session.getEndedAt() == null) {
            session.setEndedAt(now);
        }

        // 요구사항대로: 세션 종료 시 시퀀스 endedAt도 갱신(최신 활동 시각)
        //seq.setEndedAt(now);

        // save 호출은 선택(트랜잭션 + dirty checking이면 없어도 됨)
        sessionRepository.save(session);
        //sequenceRepository.save(seq);

        return new SessionFinishResponse(
                session.getId(),
                //seq.getId(),
                session.getEndedAt()
                //seq.getEndedAt()
        );
    }

    /**
     * 시퀀스 종료:
     * - Sequence.endedAt 업데이트
     */
    @Transactional
    public SequenceFinishResponse finishSequence(Long sequenceId) {
        Sequence seq = sequenceRepository.findById(sequenceId)
                .orElseThrow(() -> new IllegalArgumentException("Sequence not found: " + sequenceId));

        LocalDateTime now = LocalDateTime.now();

        // 이미 종료된 경우 재호출 정책: 그대로 반환(원하면 예외로 막아도 됨)
        if (seq.getEndedAt() == null) {
            seq.setEndedAt(now);
        } else {
            // 요구사항이 "호출하면 무조건 업데이트"면 아래로 바꾸면 됨:
            // seq.setEndedAt(now);
        }

        sequenceRepository.save(seq);

        return new SequenceFinishResponse(seq.getId(), seq.getEndedAt());
    }
}