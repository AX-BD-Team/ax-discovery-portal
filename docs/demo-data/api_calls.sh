#!/bin/bash
# AX Discovery Portal - 데모 API 호출 스크립트
# Usage: ./api_calls.sh [scenario] [step]

API_URL="${API_URL:-https://ax-discovery-api.onrender.com}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 유틸리티 함수
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_step() {
    echo -e "${YELLOW}▶ Step $1: $2${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Health Check
health_check() {
    print_header "Health Check"
    response=$(curl -s "$API_URL/health")
    echo "$response" | python -m json.tool 2>/dev/null || echo "$response"

    if echo "$response" | grep -q "healthy"; then
        print_success "API 서버 정상"
    else
        print_error "API 서버 이상"
        exit 1
    fi
}

# 시나리오 1: 세미나 → Signal → Scorecard
scenario1() {
    print_header "시나리오 1: 세미나 → Signal → Scorecard"

    case "${1:-all}" in
        1|activity)
            print_step 1 "세미나 Activity 등록"
            curl -s -X POST "$API_URL/api/inbox/activity" \
                -H "Content-Type: application/json" \
                -d '{
                    "title": "AI 기반 스마트팩토리 혁신 세미나",
                    "activity_type": "seminar",
                    "date": "2026-01-15",
                    "attendee": "김민수",
                    "summary": "제조업 AI 도입 현황 및 KT의 기회 영역 발표. 중소제조업체의 품질검사 자동화 수요 급증.",
                    "key_insights": ["중소제조업 품질검사 자동화 수요 급증", "KT 5G + AI 조합으로 경쟁력 있는 솔루션 가능"]
                }' | python -m json.tool
            ;;
        2|signal)
            print_step 2 "Signal 목록 조회"
            curl -s "$API_URL/api/inbox?status=NEW&limit=5" | python -m json.tool
            ;;
        3|triage)
            print_step 3 "Scorecard 평가 (Triage)"
            curl -s -X POST "$API_URL/api/workflows/inbound-triage" \
                -H "Content-Type: application/json" \
                -d '{"signal_id": "SIG-2026-0115-001"}' | python -m json.tool
            ;;
        4|scorecard)
            print_step 4 "Scorecard 결과 조회"
            curl -s "$API_URL/api/scorecard?limit=5" | python -m json.tool
            ;;
        all)
            scenario1 1
            sleep 1
            scenario1 2
            sleep 1
            scenario1 3
            sleep 1
            scenario1 4
            ;;
    esac
}

# 시나리오 2: VoC → Brief → Confluence
scenario2() {
    print_header "시나리오 2: VoC → Brief → Confluence"

    case "${1:-all}" in
        1|voc)
            print_step 1 "VoC Mining 실행"
            curl -s -X POST "$API_URL/api/workflows/voc-mining" \
                -H "Content-Type: application/json" \
                -d '{
                    "source_type": "text",
                    "content": "에이텍제조: AI 품질검사 솔루션 문의. 현재 수작업으로 불량률 관리가 어려움.\n베스트물류: 물류센터 자동화에 관심 있음.\n씨테크제조: 스마트팩토리 구축 희망.\n델타유통: 재고 관리 AI 솔루션 필요.\n이테크제조: 품질검사 자동화 시급."
                }' | python -m json.tool
            ;;
        2|preview)
            print_step 2 "VoC 테마 추출 미리보기"
            curl -s -X POST "$API_URL/api/workflows/voc-mining/preview" \
                -H "Content-Type: application/json" \
                -d '{"source_type": "text", "source_id": "demo-voc"}' | python -m json.tool
            ;;
        3|brief)
            print_step 3 "Brief 생성"
            curl -s -X POST "$API_URL/api/brief" \
                -H "Content-Type: application/json" \
                -d '{
                    "title": "중소제조업 AI 품질검사 솔루션",
                    "signal_ids": ["SIG-2026-0115-001"],
                    "summary": "중소제조업체의 AI 품질검사 자동화 수요 급증"
                }' | python -m json.tool
            ;;
        4|sync)
            print_step 4 "Confluence 동기화"
            curl -s -X POST "$API_URL/api/workflows/confluence-sync/preview?target_type=brief&target_id=BRIEF-2026-0116-001" \
                -H "Content-Type: application/json" \
                -d '{}' | python -m json.tool
            ;;
        all)
            scenario2 1
            sleep 1
            scenario2 2
            sleep 1
            scenario2 3
            sleep 1
            scenario2 4
            ;;
    esac
}

# 시나리오 3: Inbound → Triage → S2 승인
scenario3() {
    print_header "시나리오 3: Inbound → Triage → S2 승인"

    case "${1:-all}" in
        1|inbound)
            print_step 1 "Inbound 요청 접수"
            curl -s -X POST "$API_URL/api/inbox/inbound" \
                -H "Content-Type: application/json" \
                -d '{
                    "title": "삼성SDS 스마트팩토리 AI 품질검사 공동 사업 제안",
                    "requester_name": "이정훈",
                    "requester_company": "삼성SDS",
                    "requester_email": "jh.lee@samsung-sds.com",
                    "description": "삼성SDS MES와 KT AI 품질검사 솔루션 결합 제안. 삼성전자 협력사 200개사 대상.",
                    "urgency": "HIGH",
                    "expected_revenue": "100억원"
                }' | python -m json.tool
            ;;
        2|triage)
            print_step 2 "Triage 실행"
            curl -s -X POST "$API_URL/api/workflows/inbound-triage" \
                -H "Content-Type: application/json" \
                -d '{"signal_id": "SIG-2026-0116-INBD-001"}' | python -m json.tool
            ;;
        3|scorecard)
            print_step 3 "Scorecard 조회"
            curl -s "$API_URL/api/scorecard?limit=5" | python -m json.tool
            ;;
        4|kpi)
            print_step 4 "KPI Digest 조회"
            curl -s -X POST "$API_URL/api/workflows/kpi-digest" \
                -H "Content-Type: application/json" \
                -d '{"period_type": "weekly"}' | python -m json.tool
            ;;
        all)
            scenario3 1
            sleep 1
            scenario3 2
            sleep 1
            scenario3 3
            sleep 1
            scenario3 4
            ;;
    esac
}

# 전체 데모 실행
run_all() {
    print_header "AX Discovery Portal - 전체 데모"
    health_check
    scenario1 all
    scenario2 all
    scenario3 all
    print_header "데모 완료"
}

# 사용법 출력
usage() {
    echo "Usage: $0 [command] [step]"
    echo ""
    echo "Commands:"
    echo "  health      - Health check"
    echo "  s1, scenario1 [step] - 시나리오 1: 세미나 → Signal → Scorecard"
    echo "  s2, scenario2 [step] - 시나리오 2: VoC → Brief → Confluence"
    echo "  s3, scenario3 [step] - 시나리오 3: Inbound → Triage → S2"
    echo "  all         - 전체 데모 실행"
    echo ""
    echo "Steps (optional):"
    echo "  1, 2, 3, 4  - 특정 단계만 실행"
    echo "  all         - 전체 단계 실행 (기본값)"
    echo ""
    echo "Examples:"
    echo "  $0 health"
    echo "  $0 s1"
    echo "  $0 s1 2"
    echo "  $0 scenario2 all"
    echo "  $0 all"
    echo ""
    echo "Environment:"
    echo "  API_URL     - API 서버 URL (기본: https://ax-discovery-api.onrender.com)"
}

# 메인 로직
case "${1:-help}" in
    health)
        health_check
        ;;
    s1|scenario1)
        scenario1 "${2:-all}"
        ;;
    s2|scenario2)
        scenario2 "${2:-all}"
        ;;
    s3|scenario3)
        scenario3 "${2:-all}"
        ;;
    all)
        run_all
        ;;
    *)
        usage
        ;;
esac
