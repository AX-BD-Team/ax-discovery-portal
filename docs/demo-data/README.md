# 데모 샘플 데이터

> PoC 최종 발표용 데모 데이터 (v0.5.0)

## 📁 파일 구조

```
demo-data/
├── README.md                    # 이 파일
├── scenario1_seminar.json       # 시나리오 1: 세미나 데이터
├── scenario2_voc.csv            # 시나리오 2: VoC CSV 데이터
├── scenario2_voc_analysis.json  # 시나리오 2: VoC 분석 결과
├── scenario3_inbound.json       # 시나리오 3: Inbound 요청
└── api_calls.sh                 # API 호출 스크립트
```

---

## 시나리오 1: 세미나 → Signal → Scorecard

### 데이터 파일
- `scenario1_seminar.json`

### API 호출 순서

```bash
# 1. Activity 등록 (세미나)
curl -X POST "https://ax-discovery-api.onrender.com/api/inbox/activity" \
  -H "Content-Type: application/json" \
  -d @scenario1_seminar.json

# 2. Signal 조회
curl "https://ax-discovery-api.onrender.com/api/inbox?status=NEW"

# 3. Scorecard 평가 (Triage)
curl -X POST "https://ax-discovery-api.onrender.com/api/workflows/inbound-triage" \
  -H "Content-Type: application/json" \
  -d '{"signal_id": "SIG-2026-0115-001"}'

# 4. Scorecard 결과 조회
curl "https://ax-discovery-api.onrender.com/api/scorecard/SIG-2026-0115-001"
```

---

## 시나리오 2: VoC → Brief → Confluence

### 데이터 파일
- `scenario2_voc.csv` - VoC 원본 데이터
- `scenario2_voc_analysis.json` - 예상 분석 결과

### API 호출 순서

```bash
# 1. VoC Mining 실행
curl -X POST "https://ax-discovery-api.onrender.com/api/workflows/voc-mining" \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "text",
    "content": "에이텍제조: AI 품질검사 솔루션 문의. 현재 수작업으로 불량률 관리가 어려움.\n베스트물류: 물류센터 자동화에 관심 있음. 인건비 상승으로 무인화 적극 검토 중.\n씨테크제조: 스마트팩토리 구축 희망. 정부 지원사업 연계 가능 여부 문의.\n델타유통: 재고 관리 AI 솔루션 필요. 현재 엑셀로 관리하여 오류 빈번.\n이테크제조: 품질검사 자동화 시급. 인력 부족으로 검사 품질 저하."
  }'

# 2. 테마 추출 결과 확인 (Preview)
curl -X POST "https://ax-discovery-api.onrender.com/api/workflows/voc-mining/preview" \
  -H "Content-Type: application/json" \
  -d '{"source_type": "text", "source_id": "demo-voc"}'

# 3. Brief 생성
curl -X POST "https://ax-discovery-api.onrender.com/api/brief" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "중소제조업 AI 품질검사 솔루션",
    "signal_ids": ["SIG-2026-0115-001", "SIG-2026-0116-VOC-001"],
    "summary": "중소제조업체의 AI 품질검사 자동화 수요 급증"
  }'

# 4. Confluence 동기화
curl -X POST "https://ax-discovery-api.onrender.com/api/workflows/confluence-sync/brief" \
  -H "Content-Type: application/json" \
  -d '{"brief_id": "BRIEF-2026-0116-001"}'
```

---

## 시나리오 3: Inbound → Triage → S2 승인

### 데이터 파일
- `scenario3_inbound.json`

### API 호출 순서

```bash
# 1. Inbound 요청 접수
curl -X POST "https://ax-discovery-api.onrender.com/api/inbox/inbound" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "삼성SDS 스마트팩토리 AI 품질검사 공동 사업 제안",
    "requester_name": "이정훈",
    "requester_company": "삼성SDS",
    "requester_email": "jh.lee@samsung-sds.com",
    "description": "삼성SDS의 제조 MES 솔루션과 KT의 AI 품질검사 솔루션을 결합한 통합 솔루션 개발 제안",
    "urgency": "HIGH",
    "expected_revenue": "100억원/년"
  }'

# 2. Triage 실행
curl -X POST "https://ax-discovery-api.onrender.com/api/workflows/inbound-triage" \
  -H "Content-Type: application/json" \
  -d '{"signal_id": "SIG-2026-0116-INBD-001"}'

# 3. Scorecard 조회
curl "https://ax-discovery-api.onrender.com/api/scorecard/SIG-2026-0116-INBD-001"

# 4. S2 승인 처리
curl -X PATCH "https://ax-discovery-api.onrender.com/api/brief/BRIEF-2026-0116-001/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "S2_VALIDATED", "approved_by": "김팀장"}'

# 5. KPI Digest 조회
curl -X POST "https://ax-discovery-api.onrender.com/api/workflows/kpi-digest" \
  -H "Content-Type: application/json" \
  -d '{"period_type": "weekly"}'
```

---

## 🔧 데모 환경 설정

### 환경 변수

```bash
export API_URL="https://ax-discovery-api.onrender.com"
# 로컬 테스트 시
# export API_URL="http://localhost:8000"
```

### 헬스 체크

```bash
curl "$API_URL/health"
# Expected: {"status":"healthy","version":"0.4.0",...}
```

---

## 📊 예상 데모 결과

### 시나리오 1 결과
- Activity: ACT-2026-0115-001
- Signal: SIG-2026-0115-001
- Scorecard: 80점 (GO)

### 시나리오 2 결과
- 테마 3개 추출 (품질검사, 물류자동화, 재고관리)
- Signal: SIG-2026-0116-VOC-001
- Brief: BRIEF-2026-0116-001
- Confluence 페이지 생성

### 시나리오 3 결과
- Signal: SIG-2026-0116-INBD-001
- Scorecard: 88점 (GO)
- S2 승인 완료
- KPI: 모든 주간 목표 달성

---

## ⚠️ 주의사항

1. **데모 전 데이터 초기화**: 기존 테스트 데이터 정리 필요
2. **Confluence 연동**: 실제 Confluence 환경 설정 필요
3. **Teams 알림**: Webhook URL 설정 필요
4. **백업 계획**: API 장애 시 JSON 파일로 시연
