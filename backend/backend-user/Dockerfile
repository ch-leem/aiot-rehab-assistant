# =========================
# 1단계: 빌드
# =========================
FROM eclipse-temurin:17-jdk AS builder

WORKDIR /app

# backend 루트 전체(gradlew, settings.gradle, common-db 포함)가 들어온다고 가정
COPY . .

# gradlew 실행 안정화: (1) bash 설치 (2) CRLF 제거 (3) bash로 실행
RUN apt-get update \
    && apt-get install -y --no-install-recommends bash dos2unix \
    && rm -rf /var/lib/apt/lists/*

RUN dos2unix ./gradlew || true
RUN chmod +x ./gradlew

# 멀티모듈: backend-user 모듈만 빌드
RUN bash ./gradlew :backend-user:clean :backend-user:bootJar -x test --no-daemon

# =========================
# 2단계: 실행
# =========================
FROM eclipse-temurin:17-jre

WORKDIR /app

# 빌드된 jar만 복사
COPY --from=builder /app/backend-user/build/libs/*.jar app.jar

EXPOSE 8080
ENTRYPOINT ["java","-jar","/app/app.jar"]
