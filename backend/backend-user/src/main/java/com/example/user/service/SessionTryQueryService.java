package com.example.user.service;

import com.example.iot.domain.Try;
import com.example.iot.domain.constant.TryResult;
import com.example.iot.repository.TryRepository;
import com.example.user.dto.FailedTryIdsResponse;
import org.springframework.transaction.annotation.Transactional;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.List;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true) // 조회 성능 최적화 및 DB 락 방지
public class SessionTryQueryService {

    private final TryRepository tryRepository;

    @Transactional(readOnly = true)
    public FailedTryIdsResponse getFailedTryIds(Long sessionId) {
        List<Try> failed = tryRepository.findBySession_IdAndResult(sessionId, TryResult.FAIL);
        // 또는: findBySession_IdAndFailIsNotNull(sessionId)

        List<Long> ids = failed.stream().map(Try::getId).toList();

        return new FailedTryIdsResponse(sessionId, ids, ids.size());
    }
}
