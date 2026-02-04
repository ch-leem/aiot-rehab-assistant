package com.example.iot.service;

import com.example.iot.domain.Session;
import com.example.iot.repository.SessionRepository;
import jakarta.transaction.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.time.LocalDateTime;

@Service
@RequiredArgsConstructor
@Transactional
public class SessionService {

    private final SessionRepository sessionRepository;

    public void startSession(Long sessionId) {
        Session session = sessionRepository.findById(sessionId)
                .orElseThrow(() -> new IllegalArgumentException("세션이 존재하지 않습니다. id=" + sessionId));

        session.setStartedAt(LocalDateTime.now());
        // @Transactional이라 save() 없어도 됨 (dirty checking)
    }
}
