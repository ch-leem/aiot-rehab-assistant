package com.example.iot.repository;

import com.example.iot.domain.Session;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface SessionRepository extends JpaRepository<Session, Long> {

    //시퀀스 id에 맞는 세션 데이터 가져오기
    List<Session> findBySequence_IdOrderByStartedAtAsc(Long sequenceId);

    @Query("""
        select s
        from Session s
        join fetch s.exercise e
        where s.sequence.id = :sequenceId
    """)
    List<Session> findBySequenceIdWithExercise(@Param("sequenceId") Long sequenceId);

}
