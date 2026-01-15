# 1단계: 빌드
FROM eclipse-temurin:17-jdk AS builder

WORKDIR /app

# Spring 프로젝트 전체 복사
COPY . .

# Gradle Wrapper 실행 권한 + 빌드
RUN chmod +x ./gradlew \
    && ./gradlew clean bootJar -x test

# 2단계: 실행
FROM eclipse-temurin:17-jre

WORKDIR /app

# 빌드된 jar만 복사
COPY --from=builder /app/build/libs/*.jar app.jar

EXPOSE 8080

ENTRYPOINT ["java","-jar","/app/app.jar"]
