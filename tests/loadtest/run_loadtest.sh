#!/bin/bash
# AX Discovery Portal - 부하 테스트 실행 스크립트

set -e

# 기본값 설정
HOST="${HOST:-http://localhost:8000}"
USERS="${USERS:-10}"
SPAWN_RATE="${SPAWN_RATE:-2}"
DURATION="${DURATION:-60s}"
REPORT_DIR="${REPORT_DIR:-./loadtest_reports}"

# 리포트 디렉토리 생성
mkdir -p "$REPORT_DIR"

# 타임스탬프
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "======================================"
echo "AX Discovery Portal 부하 테스트"
echo "======================================"
echo "Host: $HOST"
echo "Users: $USERS"
echo "Spawn Rate: $SPAWN_RATE"
echo "Duration: $DURATION"
echo "======================================"

# 시나리오 선택
case "${1:-standard}" in
    quick)
        # 빠른 스모크 테스트 (30초, 5명)
        echo "Quick Test 실행..."
        locust -f tests/loadtest/locustfile.py \
            --host="$HOST" \
            --headless \
            -u 5 \
            -r 1 \
            -t 30s \
            --html="$REPORT_DIR/quick_${TIMESTAMP}.html" \
            HealthCheckUser ReadOnlyUser
        ;;

    standard)
        # 표준 부하 테스트 (60초, 10명)
        echo "Standard Test 실행..."
        locust -f tests/loadtest/locustfile.py \
            --host="$HOST" \
            --headless \
            -u "$USERS" \
            -r "$SPAWN_RATE" \
            -t "$DURATION" \
            --html="$REPORT_DIR/standard_${TIMESTAMP}.html"
        ;;

    stress)
        # 스트레스 테스트 (5분, 50명)
        echo "Stress Test 실행..."
        locust -f tests/loadtest/locustfile.py \
            --host="$HOST" \
            --headless \
            -u 50 \
            -r 5 \
            -t 5m \
            --html="$REPORT_DIR/stress_${TIMESTAMP}.html"
        ;;

    spike)
        # 스파이크 테스트 (2분, 100명 급격한 증가)
        echo "Spike Test 실행..."
        locust -f tests/loadtest/locustfile.py \
            --host="$HOST" \
            --headless \
            -u 100 \
            -r 50 \
            -t 2m \
            --html="$REPORT_DIR/spike_${TIMESTAMP}.html" \
            BurstUser
        ;;

    endurance)
        # 내구성 테스트 (30분, 20명 꾸준한 부하)
        echo "Endurance Test 실행..."
        locust -f tests/loadtest/locustfile.py \
            --host="$HOST" \
            --headless \
            -u 20 \
            -r 1 \
            -t 30m \
            --html="$REPORT_DIR/endurance_${TIMESTAMP}.html" \
            ApiUser ReadOnlyUser
        ;;

    ui)
        # 웹 UI 모드 (인터랙티브)
        echo "Locust 웹 UI 시작 (http://localhost:8089)..."
        locust -f tests/loadtest/locustfile.py \
            --host="$HOST" \
            --web-host="0.0.0.0"
        ;;

    *)
        echo "사용법: $0 {quick|standard|stress|spike|endurance|ui}"
        echo ""
        echo "시나리오:"
        echo "  quick     - 빠른 스모크 테스트 (30초, 5명)"
        echo "  standard  - 표준 부하 테스트 (60초, 10명)"
        echo "  stress    - 스트레스 테스트 (5분, 50명)"
        echo "  spike     - 스파이크 테스트 (2분, 100명)"
        echo "  endurance - 내구성 테스트 (30분, 20명)"
        echo "  ui        - 웹 UI 모드"
        echo ""
        echo "환경변수:"
        echo "  HOST       - 대상 호스트 (기본: http://localhost:8000)"
        echo "  USERS      - 동시 사용자 수 (기본: 10)"
        echo "  SPAWN_RATE - 초당 사용자 증가율 (기본: 2)"
        echo "  DURATION   - 테스트 시간 (기본: 60s)"
        exit 1
        ;;
esac

echo ""
echo "테스트 완료! 리포트: $REPORT_DIR/"
