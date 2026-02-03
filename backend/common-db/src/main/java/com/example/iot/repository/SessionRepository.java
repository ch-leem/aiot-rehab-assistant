package com.example.iot.repository;

import com.example.iot.domain.Session;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

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


    // 세션 + 트라이 + 목표결과를 한 번에 조회 (N+1 문제 방지)
    @Query("""
    select se from Session se
    join fetch se.exercise ex
    join fetch se.sequence sq
    where sq.id in :sequenceIds
    """)
    List<Session> findBySequenceIdsWithExercise(List<Long> sequenceIds);

    @Query("""
    select distinct s from Session s
    join fetch s.exercise e
    left join fetch s.tries t
    left join fetch t.goalResults gr
    left join fetch gr.exerciseGoal
    where s.sequence.id = :sequenceId
    order by s.id asc
""")
    List<Session> findAllDetailBySequenceId(@Param("sequenceId") Long sequenceId);

    // 특정 시퀀스 내에서 특정 운동(Exercise)에 해당하는 세션 찾기
    Optional<Session> findFirstBySequenceIdAndExerciseId(Long sequenceId, Long exerciseId);
}
