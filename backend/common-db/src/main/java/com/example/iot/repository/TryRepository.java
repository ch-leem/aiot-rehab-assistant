package com.example.iot.repository;

import com.example.iot.domain.Try;
import com.example.iot.domain.constant.TryResult;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface TryRepository extends JpaRepository<Try, Long> {

    List<Try> findBySessionId(Long sessionId);

    //Session아이디 몇 개인지 count
    long countBySession_Id(Long sessionId);
    //성공 횟수 세기
//    long countBySession_IdCountSuccess(Long sessionId);
    //실패 횟수 세기
    //long countBySession_IdCountFail(Long sessionId);
    List<Try> findBySession_IdAndResult(Long sessionId, TryResult result);
}
