
# 2. 각 파트별 README

- 담당 : 이혜연
- README 작성 방향성 : 공통 내용 모두 반영 + 각 파트별 특이사항, 넣고 싶은 내용 다 정리

## 2-1. 공통 내용

### 1. 개발 환경 및 기술 스택
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

### 2. 실행 환경 및 실행 방법
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

### 3. 서비스 책임 범위

1) AIoT Server (Spring Boot)
    - 사용자/치료사/환자 도메인, 세션/시퀀스/Try 결과를 저장하고 조회
    - 정형 데이터 REST API 제공

2) Ingest Server (FastAPI)
    - 임베디드 → WebSocket으로 센서·비전 JSON 수집
    - Redis에 최신값/집계값 저장 및 Try 단위 집계 처리
    - 프론트로 SSE 스트리밍 제공

3) Heartbeat Server (FastAPI)
    - 임베디드 연결 상태 관리
    - 제어 명령(시작/중지 등) 전달을 위한 WebSocket 양방향 채널
    - 중복 연결 방지 및 연결 lifecycle 관리

4) Nginx Reverse Proxy
    - Path 기반 라우팅(/api/user, /iot-api, /api/ingest, /jenkins)
    - SSE 엔드포인트 버퍼링 OFF 및 타임아웃 튜닝
    - TLS Termination + Certbot 인증서 적용

5) Jenkins CI/CD
    - Git 체크아웃 → 빌드/도커 이미지 갱신 → docker compose 재기동 → nginx reload
    - 배포 작업 표준화

### 4. Ingest 서버 데이터 파이프라인

1) Real-time Ingest & Redis Storage Flow
    - 프레임 수신 (POST /ingest/stream) <br>
    ```
    1. 클라이언트(임베디드/중간 서버)가 frames[] JSON payload를 전송
    2. Ingest 서버는 payload를 JSON 문자열로 직렬화하여 Redis 저장
    3. 저장은 2가지 레벨로 분리된다:
        Global 레벨(try 무관): 최근 값/전체 스트림
        Try 레벨(활성 try 존재 시): try별 최근 값/스트림/RAW/집계
    ```
    - 실시간 프론트 구독 (GET /events) <br>
        - 프론트는 SSE로 /events를 구독
        - 서버는 ingest될 때마다 구독자 큐에 최신 payload를 push하여 즉시 전달
    

2) Keyspace Spec
- Global 레벨

| Key             | Type   | 내용                                      | 생성/갱신 시점              | TTL                |
| --------------- | ------ | --------------------------------------- | --------------------- | ------------------ |
| `ingest:stream` | Stream | `{ts_ms, client_ip, payload(JSON str)}` | 매 `/ingest/stream` 요청 | MAXLEN=5000 (trim) |
| `ingest:latest` | String | 가장 최근 payload(JSON str)                 | 매 `/ingest/stream` 요청 | (없음)               |

- 활성 Try 제어

| Key                 | Type   | 내용           | 생성/갱신 시점                                 | TTL  |
| ------------------- | ------ | ------------ | ---------------------------------------- | ---- |
| `ingest:active_try` | String | 현재 활성 try_id | `/try/start`에서 set, `/try/stop`에서 delete | (없음) |

- Try 레벨 (active_try 가 존재할 경우) (try가 시작된 경우)

| Key                          | Type            | 내용                                     | 생성/갱신 시점                         | TTL                      |
| ---------------------------- | --------------- | -------------------------------------- | -------------------------------- | ------------------------ |
| `frames:try:{try_id}:stream` | Stream          | try 단위 프레임 스트림                         | active_try 존재 + `/ingest/stream` | MAXLEN=5000 (trim)       |
| `frames:try:{try_id}:latest` | String          | try 단위 최근 payload                      | active_try 존재 + `/ingest/stream` | (없음)                     |
| `try:{try_id}:raw`           | List            | try 동안 들어온 payload를 raw로 rpush         | active_try 존재 + `/ingest/stream` | `RAW_TTL_SEC` (기본 3600s) |
| `agg:try:{try_id}`           | Hash            | 집계 결과 저장소(sum/count/min/max + prev 좌표) | active_try 존재 + `/ingest/stream` | (없음 / 필요 시 추가 가능)        |
| `ingest:pub`                 | Pub/Sub channel | payload publish                        | active_try 존재 + `/ingest/stream` | (채널)                     |

3) 집계 로직
    - 공통 통계 (METRIC_PATHS 기반) <br>
    AGG_METRICS에 정의된 metric마다 아래 필드를 누적:<br>
    ```
    sum.{metric}
    count.{metric}
    min.{metric}
    max.{metric}
    ```
    - 발목 jitter 계산 (3D 이동량) <br>
    좌/우 발목 좌표에 대해 이전 프레임 좌표를 저장하고, 거리 변화량을 누적<br>
    이전 좌표: `prev.l_ankle.{x|y|z}`, `prev.r_ankle.{x|y|z}` <br>
    이동량 : `d = dist3(cur, prev)` <br>
    누적:
    ```
    sum.l_ankle_jitter
    sum_sq.l_ankle_jitter
    count.l_ankle_jitter
    max.l_ankle_jitter
    ```

4) 라이프사이클
    1. Try 시작: POST `/try/start { try_id }
        - `ingest:active_try` = try_id 설정
        - `agg:try:{try_id}` 삭제로 집계 초기화

    2. Ingest 수행: POST /ingest/stream
        - Global 저장(ingest:stream/latest)
        - active_try 존재 시 try별 저장(stream/latest/raw/agg)

    3. Try 종료: POST /try/stop
        - ingest:active_try 삭제 → 이후 데이터는 global에만 저장되고 try 집계는 중단

### 5. 트러블슈팅

1)  AIoT 서버
    - Spring Data JPA Repository 메서드 네이밍 이슈
        - 증상   <br>
        Repository 메서드 실행 시 의도한 조회 결과가 나오지 않거나,
        애플리케이션 실행 중 런타임 에러 발생 <br>

        - 원인   <br>
        Spring Data JPA의 메서드 네이밍 규칙을 정확히 이해하지 못한 상태에서  
  연관 엔티티 필드에 대한 조회 메서드를 정의. 특히, 연관관계 필드 접근 시  
  `{EntityField}_{SubField}` 형태의 네이밍 규칙을 인지하지 못함 <br>

        - 해결   <br>
        Spring Data JPA의 메서드 네이밍 규칙을 정리하여 사용 <br>

2) Ingest 서버
    - Redis 집계 로직 구현 이슈 <br>
        - 증상 <br>
        Ingest 서버에서 Redis에 누적되는 센서 데이터를 단순 통계(sum, count, min, max)만으로 처리해야 한다고 판단 <br>
        - 원인 <br>
        Redis의 Lua Script 및 커스텀 집계 로직에 대한 이해 부족으로, Redis에서 복합 집계 로직을 직접 구현할 수 있다는 점을 인지하지 못함.
        - 해결 <br>
        Redis Lua Script를 활용하여 커스텀 집계 로직을 구현함으로써 요구되는 집계 데이터를 서버 단에서 효율적으로 처리
        
3) HeartBeat 서버
    - WebSocket 중복 연결로 인한 통신 실패 <br>
        - 증상 <br>
        프론트엔드 – HeartBeat 서버, 임베디드 기기 – HeartBeat 서버 간 WebSocket 통신이 간헐적으로 끊기거나 데이터가 전달되지 않음 <br>
        - 원인 <br>
        프론트엔드에서 WebSocket을 이미 연결한 상태에서 중복으로 다시 연결을 시도했고, HeartBeat 서버에서 기존 임베디드 기기 WebSocket 연결을 유지하지 않고, 새로운 연결로 덮어씌우는 로직이 존재 <br>
        - 해결 <br>
        프론트엔드: WebSocket 단일 인스턴스 관리 및 중복 연결 방지
        클라이언트: WebSocket 연결 상태를 명확히 관리하도록 구조를 개선 <br>


4) 인프라 및 ec2 배포
    - Docker / 배포 환경 구분 미흡 <br>
        - 증상 <br>
        로컬, Docker, EC2 배포 환경 간 설정이 혼합되어 테스트 및 디버깅에 어려움 발생
        <br>
        - 원인 <br>
        초기 설계 단계에서 실행 환경별 설정 파일 및 실행 방식을 분리하지 않음 <br>
        - 해결 <br>
        application.local.yml과 docker-compose.local.yml 추가를 통한 환경을 분리 <br>
    - Nginx 설정 변경 후 반영되지 않는 문제  <br>
        - 증상 <br>
        nginx 설정 파일 수정 후에도 변경 사항이 적용되지 않음.
        <br>
        - 원인 <br>
        nginx 컨테이너 재빌드 없이 reload만 수행 <br>
        - 해결 <br>
        nginx 설정 변경 시 컨테이너 재빌드 후 reload 수행 <br>


## 2-2. 파트별 권장 내용


1) 통신 구조
    - 프론트엔드 - AIoT 서버(spring)
        - HTTP 기반의 RESTful API로 통신하여 정형 데이터를 전달

    - 프론트엔드 - ingest 서버
        - 임베디드 기기에서 수집된 센서·비전 데이터(JSON)를 SSE(Server-Sent Events) 기반 구독 방식으로 실시간 수신

    - 프론트엔드 - heartbeat 서버
        - WebSocket 기반 양방향 통신을 통해 임베디드 기기의 연결 상태 확인 및 제어 신호 전달을 수행

    - ingest 서버 - 임베디드 기기
        - WebSocket 통신을 통해 임베디드 기기에서 센서·비전 데이터(JSON)를 실시간으로 전달

    - heartbeat 서버 - 임베디드 기기
        - WebSocket 통신을 통해 임베디드 기기의 상태(heartbeat), 연결 유지 및 제어 명령을 주고받음

2) HTTPS/TLS
    - Certbot을 사용하여 도메인에 대한 SSL/TLS 인증서를 발급하고, Nginx에 적용하여 HTTPS 통신을 제공. 인증서는 자동 갱신(renew) 구조로 설정하여 운영 중 만료 이슈 방지
    내부 서비스 간 통신(Spring, FastAPI, Redis, PostgreSQL)은 Docker 내부 네트워크를 통해 HTTP 기반으로 통신하도록 구성.

3) Nginx 라우팅 규칙
- HTTP (80) → 인증서 발급/상태 확인

| Inbound (URL)                   | Method | 목적                        | Upstream                    | 비고           |
| ------------------------------- | ------ | ------------------------- | --------------------------- | ------------ |
| `/.well-known/acme-challenge/*` | GET    | Let’s Encrypt 인증(HTTP-01) | (static) `/var/www/certbot` | Certbot 검증용  |
| `/`                             | GET    | HTTP alive check          | (Nginx 자체 응답)               | `http ok` 반환 |


- HTTPS (443) → 서비스 라우팅 (TLS Termination)

| Inbound (URL)                     | Method   | 목적/설명                                     | Upstream(Target)         | Proxy Pass 결과 경로                                       |
| --------------------------------- | -------- | ----------------------------------------- | ------------------------ | ------------------------------------------------------ |
| `/test/*`                         | GET/WS   | 시그널링 서버 및 Heartbeat 서버 | `frontend-test:8080`     | `/test/abc` → `http://frontend-test:8080/abc`          |
| `/api/ingest/events` | GET      | **SSE 스트리밍 엔드포인트**                        | `ingest-api:8000/events` | `/api/ingest/events` → `http://ingest-api:8000/events` |
| `/jenkins/*`                      | GET/POST | Jenkins UI/API (path 기반)                  | `jenkins:8080/jenkins/`  | `/jenkins/abc` → `http://jenkins:8080/jenkins/abc`     |
| `/api/user/*`                     | ALL      | User API (Spring)                         | `user-api:8080`          | `/api/user/abc` → `http://user-api:8080/abc`           |
| `/api/iot/*`                      | ALL      | IoT API (Spring)                          | `iot-api:8080`           | `/api/iot/abc` → `http://iot-api:8080/abc`             |
| `/api/ingest/*`                   | ALL      | Ingest API (FastAPI REST)                 | `ingest-api:8000`        | `/api/ingest/abc` → `http://ingest-api:8000/abc`       |
| `/` (default)                     | GET      | 프론트엔드 정적/SPA 라우팅                          | `frontend:80`            | 그대로 프론트로 전달                                            |

---
