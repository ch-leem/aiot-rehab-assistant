package com.example.user.service;

import com.example.iot.domain.*;
import com.example.iot.repository.*;
import com.example.user.dto.FailIdResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.Optional;
import org.springframework.transaction.annotation.Transactional;

@Service
@RequiredArgsConstructor
@Transactional(readOnly = true)
public class FailService {

    private final TryRepository tryRepository;

    public Optional<FailIdResponse> getFailIdByTryId(Long tryId) {
        return tryRepository.findById(tryId)
                .map(Try::getFail)          // Try → Fail
                .map(Fail::getId)           // Fail → id
                .map(String::valueOf)       // (혹시 문자열이 아닐까봐}
                .map(FailIdResponse::new);  // fail _id에 넣기
    }
}