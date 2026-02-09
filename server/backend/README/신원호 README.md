## 0. 담당자 소개

- 담당자: 신원호
- 담당 영역: BE(USER/AIOT 서버)

## 1. 공통 내용

### 1-1. 개발 환경 및 기술 스택
1) Backend (AoT / User) 
    - Spring Boot : 3.4.1
    - Java : 17
    - Gradle : 8.6

2) Ingest / HeartBeat
    - FastAPI (Python) : 3.11
    - Redis : 7

3) DB
    - PostgreSQL

4) Infra
    - Docker Compose
    - Nginx (Reverse Proxy + SSE 설정)
    - Jenkins

### 1-2. 실행 환경 및 실행 방법
1)  요구 사항

Java 17, Docker, Docker Compose, (Python 3.10+)

2) 환경 변수
    - .env 
    ```
    POSTGRES_DB=rehab
    POSTGRES_USER=app
    POSTGRES_PASSWORD=G2WhXPnBrUR2tVPMC5pphBERTDY
    POSTGRES_PORT=5432

    DB_PORT=5432
    REDIS_PORT=6379
    USER_API_PORT=8080
    IOT_API_PORT=8081
    FRONTEND_PORT=3000

    INGEST_PORT=8002
    LATEST_TTL_SECONDS=0

    VITE_API_USER_BASE_URL=/iot-api/
    VITE_API_IOT_BASE_URL=/api/user/

    GMS_KEY=S14P12A203-a732b88b-4f73-4f47-9b98-9f1e9dafc20e

    ACTIVE_TRY_KEY=ingest:active_try
    REDIS_AGG_PREFIX=agg:try
    AGG_METRICS=strength=sensor.strength,l_ankle_x=position.left.left_ankle.x,l_ankle_y=position.left.left_ankle.y,l_ankle_z=position.left.left_ankle.z,r_ankle_x=position.right.right_ankle.x,r_ankle_y=position.right.right_ankle.y,r_ankle_z=position.right.right_ankle.z,power=sensor.power,trunk_forward_tilt=deg.mid.trunk_forward_tilt,pelvis_level=deg.mid.pelvis_level,l_elbow_extension=deg.left.elbow_extension,r_elbow_extension=deg.right.elbow_extension
    ```

    - /frontend/.env
    ```
    VITE_API_USER_BASE_URL=/iot-api/
    VITE_API_IOT_BASE_URL=/api/user/
    ```

3) 실행 순서
    - 로컬 실행

        1번 도커 실행
        ```
        docker compose up -d --build
        ```
        2번 nginx reload
        ```
        docker exec -it rehab-nginx nginx -s reload
        ```

    - ec2 내 실행 (수동 빌드)

        1번 도커 실행
        ```
        sudo -u appsvc -H bash -lc 'cd /opt/myapp/S14P11A203 && docker compose up -d --build'
        ```
        2번 nginx reload
        ```
        sudo -u appsvc -H bash -lc 'cd /opt/myapp/S14P11A203 && docker exec -it rehab-nginx nginx -s reload'
        ```

    
4) 파일 구조 및 역할
    ```
    project-root/
        docker-compose.yml
            nginx/
                conf.d/
                default.conf  
            backend/
                backend-iot/          # spring IoT 서버 
                backend-user/         # spring user 서버
            ingest/
                main.py               # FastAPI ingest
            frontendTest/
                main.py               # FastAPI 실시간 서버

    ```


## 2. Backend (User/AIoT) 상세 내용

### 2-1. 서비스 책임 범위

1) AIoT Server (Spring Boot)
    - **재활 운동 라이프사이클 관리**: Sequence(1회 처방 운동 전체) → Session(개별 운동 종류) → Try(운동 동작 1회)의 상태 관리 및 데이터 저장
    - **운동 결과 판정 시스템**: Ingest 서버의 집계 데이터를 기반으로 정밀 점수(DB용)와 피드백 점수(FE용) 이중 산출
    - **리포트 생성 트리거**: 운동 종료 시점을 감지하여 GMS(LLM) 분석 요청 및 비동기 리포트 생성

2) User Server (Spring Boot)
    - **사용자 도메인 관리**: 환자/치료사 계정 정보 및 권한 관리
    - **운동 처방 매핑**: `ExercisePatientMapping`을 통해 환자별 맞춤 운동 목록 조회 및 AIoT 서버에 메타데이터 제공
    - **재활 리포트 열람**: LLM을 통해 재활 운동을 종료한 환자의 리포트를 작성하고, 의료인이 이를 열람 및 참고

3) Common DB (PostgreSQL)
    - **데이터 무결성 보장**: User(조회)와 AIoT(제어) 모듈이 물리적으로 단일 DB를 공유하여, 운동 종료 및 리포트 생성 시점의 트랜잭션 정합성 확보
    - **동시성 제어**: 비관적 락(Pessimistic Lock)을 활용하여 중복 데이터 생성 방지

### 2-2. Backend 핵심 로직 및 데이터 흐름

2) 시퀀스 및 트라이 관리 프로세스
    - **Try Pre-generation (선행 생성)**
      - 시퀀스 시작(`startSequence`) 요청 시, 설정된 목표 횟수만큼 `Try` 엔티티를 미리 생성
      - 생성된 Try ID 리스트를 반환하여 프론트엔드 및 Ingest 서버와의 ID 동기화 보장
    
    - **운동 종료 및 점수 판정 (Finish Try)**
      - Ingest 서버(Redis)로부터 수신된 데이터를 바탕으로 점수 계산
      - **이중 판정 로직 적용**:
        - **DB 판정**: (`targetvalue`)(이상적인 상태의 기준)를 기준으로 70점을 합격선으로 설정, 가중치를 반영한 엄격한 성공/실패 기록
        - **FE 판정**: (`threshold`)(환자가 정상상태가 아님을 감안한 다소 느슨한 기준)를 기준으로 100점을 합격선으로 설정, 사용자 피드백을 위한 분기 점수 계산

3) 시퀀스 종료 및 리포트 생성 (Async Architecture)
    - **종료 감지 (Sequence Completion Check)**
      - 매 Try 종료 시마다 `checkSequenceCompletion` 실행
    
    - **비동기 리포트 생성 파이프라인**
      1. **Lock 획득**: DB 레벨의 `Pessimistic Write Lock`을 통해 동시 요청 차단
      2. **상태 마킹**: Sequence 종료 시간(`endedAt`) 기록
      3. **Async 호출**: 사용자에게는 즉시 응답을 보내고, `@Async` 스레드에서 GMS(LLM) API 호출
      4. **결과 저장**: LLM 분석 결과를 파싱하여 `PatientRehabReport` 및 `SessionSummary` 테이블에 저장

### 2-3. 트러블슈팅

1) 임상적 정확성과 사용자 경험 간의 판정 로직 충돌
- **고민**
  - **DB 저장용**: 재활 의학적 가중치가 반영된 엄격한 점수(70점 기준)가 필요
  - **사용자 피드백용**: 환자의 동기 부여를 위해 관대한 기준(Threshold 기반 100점)의 즉각적인 피드백 필요
  - 단일 로직 적용 시, "DB에는 실패로 기록되나 화면에는 성공으로 표시"되는 데이터 괴리 발생
- **해결**
  - **이중 판정 전략(Dual Scoring Strategy)** 도입
  - `TryService` 내에서 `dbJudge`(정밀 판정)와 `frontJudge`(피드백 판정)를 분리하여 계산
  - DB에는 임상 데이터를 보존하고, API 응답으로는 UX 친화적인 결과를 반환하여 두 가지 요구사항을 모두 충족

2) 복합 계층 구조 조회 시 N+1 성능 이슈
- **고민**
  - 리포트 생성을 위해 `Sequence` 데이터를 조회할 때, 하위 엔티티인 `Session`, `Try`, `GoalResult`를 순회하면서 불필요한 SELECT 쿼리가 수십 회 발생
- **원인**
  - JPA의 지연 로딩(Lazy Loading) 전략으로 인해, 루프를 돌 때마다 연관된 하위 데이터를 가져오기 위한 추가 쿼리가 실행됨
- **해결**
  - `SessionRepository`에 `JOIN FETCH`를 적용한 커스텀 쿼리(`findAllDetailBySequenceId`) 구현
  - 단 한 번의 쿼리로 시퀀스 내의 모든 계층 데이터를 조인하여 가져오도록 최적화 (쿼리 수행 횟수 1/N로 감소)

### 2-4. 아키텍처 의사결정

1) **User/AIoT 서버 분리 및 DB 공유 전략**
    - **배경**: User(조회 중심)와 AIoT(제어 중심)의 트래픽 성격이 달라 서버 분리가 필요했으나, 운동 종료 데이터의 정합성이 매우 중요함
    - **결정**: 논리적으로는 모듈을 분리하여 확장성을 확보하되, 물리적으로는 **단일 DB 공유 모델**을 채택. 복잡한 분산 트랜잭션 없이 DB Lock을 활용할 수 있는 실리적인 아키텍처 구현

2) **GMS 통신 비동기 처리**
    - **배경**: LLM 분석에 시간이 소요되어 사용자 UX(화면 전환)가 지연되는 문제 발생
    - **결정**: 운동 결과 저장과 리포트 생성을 분리. `@Async`를 통해 리포트 생성은 백그라운드에서 처리하고 사용자에게는 즉시 응답을 반환하여 대기 시간 제거

## 3. 기타 회고


## 3. 회고 (Retrospective)

1) 기획과 협업의 중요성 재확인
- **기획의 디테일과 변경**: 초기 기획 단계에서 DB 구조와 로직을 탄탄하게 잡았다고 생각했으나, 실제 개발 과정에서 빈번한 수정이 발생함. 특히 **User(조회)와 AIoT(제어)의 역할 분리**에 따른 DB 설계 변경이 잦았음.
- **협업 파트와의 의존성 확인**: 내 파트의 로직뿐만 아니라, **협업하는 파트(Frontend, Ingest)의 데이터 흐름과 예외 상황**을 미리 파악하지 못해 '유령 트라이' 같은 이슈를 겪음. 이를 통해 **인터페이스 정의서(API Spec)** 단계에서 상호 간의 로직을 크로스 체크하는 것이 필수적임을 깊이 체감함.

2) 네이밍(Naming)과 리팩터링의 상관관계
- **직관적인 네이밍의 중요성**: 패키지, 클래스, 메서드, 변수 등 코드 전반의 이름이 기능을 명확히 드러내지 않을 경우, 시간이 지난 후 작성자 본인조차 로직을 파악하는 데 큰 비용이 든다는 것을 깨달음.
- **기술 부채와 두려움**: 모호한 네이밍은 코드의 의도를 흐리게 만들어, 수정 시 발생할 수 있는 연쇄적인 사이드 이펙트(Ripple Effect)를 예측하기 어렵게 함. 이로 인해 리팩터링을 주저하게 되고, 결국 유지보수 난이도가 상승하는 악순환을 경험하며 **"Clean Code"**의 가치를 다시금 느낌.

3) (Spring Boot)과 AI의 활용
- **러닝 커브와 AI의 도움**: Java와 Spring Boot에 처음 도전하면서 기초 학습 후 AI 어시스턴트(Coding Assistant)를 적극 활용하여 개발 속도를 높임.
- **AI 활용의 한계와 깨달음**: AI는 코드를 빠르게 작성해 주지만, **"왜 이 문제가 발생했는가?"**에 대한 근본적인 원인 분석과 **"어떤 아키텍처가 적합한가?"**에 대한 판단은 결국 개발자의 몫임을 깨달음.
    - 특히, **DB 락(Lock)을 이용한 동시성 제어**나 **비동기 처리 설계** 같은 복잡한 문제는 시스템 전체를 이해하지 못하면 AI가 준 코드를 적용조차 할 수 없다는 것을 확인함.

4) 방어적 프로그래밍과 시스템 안정성
- **이상과 현실의 차이**: 로컬 테스트에서는 완벽했던 로직이 네트워크 지연이나 프론트엔드의 데이터 누락으로 인해 오작동하는 것을 경험함. (예: 시퀀스 마감 실패)
- **기술적 해결**: 단순히 "프론트에서 잘 보내주겠지"라고 믿는 것이 아니라, **서버 단에서 데이터 누락을 감안한 유연한 로직(Count 기반 판정)**과 **중복 요청을 차단하는 락(Lock)**을 도입. 이를 통해 **"신뢰할 수 있는 서버"**를 만드는 방어적 프로그래밍의 중요성을 배움.