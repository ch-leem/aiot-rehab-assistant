package com.example.iot.repository;

import com.example.iot.domain.Try;
import com.example.iot.domain.constant.TryResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface TryRepository extends JpaRepository<Try, Long> {

    //세션 id에 맞는 Try정도 가져오기
    List<Try> findBySessionId(Long sessionId);

    //Session아이디 몇 개인지 count
    int countBySession_Id(Long sessionId);
    //성공 횟수 세기
//    long countBySession_IdCountSuccess(Long sessionId);
    //실패 횟수 세기
    //long countBySession_IdCountFail(Long sessionId);
    List<Try> findBySession_IdAndResult(Long sessionId, TryResult result);

    boolean existsBySession_IdAndEndedAtIsNull(Long sessionId);

    long countBySession_Sequence_IdAndEndedAtIsNotNull(Long sequenceId);
}
