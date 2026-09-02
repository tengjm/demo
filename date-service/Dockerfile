ARG BASE_IMAGE=172.24.76.66:8088/ci-tools/eclipse-temurin:8-jre
FROM ${BASE_IMAGE}

LABEL org.opencontainers.image.title="date-service" \
      org.opencontainers.image.description="Spring Cloud date service"

WORKDIR /app

RUN groupadd --system app \
    && useradd --system --gid app --home-dir /app --shell /usr/sbin/nologin app \
    && mkdir -p /app /tmp \
    && chown -R app:app /app /tmp

COPY --chown=app:app target/date-service*.jar /app/app.jar

USER app

EXPOSE 8001

ENV JAVA_OPTS="-XX:+UseContainerSupport -XX:MaxRAMPercentage=75.0 -XX:InitialRAMPercentage=50.0 -XX:+ExitOnOutOfMemoryError -Djava.security.egd=file:/dev/./urandom -Djava.io.tmpdir=/tmp" \
    SERVER_PORT=8001

VOLUME ["/tmp"]

# HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
#  CMD curl -fsS "http://127.0.0.1:${SERVER_PORT}/actuator/health/liveness" >/dev/null || wget -qO- "http://127.0.0.1:${SERVER_PORT}/actuator/health/liveness" >/dev/null || exit 1

ENTRYPOINT ["sh","-c","exec java $JAVA_OPTS -jar /app/app.jar"]
