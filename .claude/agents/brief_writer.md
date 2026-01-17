---
name: "brief_writer"
description: "Scorecard 통과 Signal을 1-Page Opportunity Brief로 변환"
---

# Brief Writer Agent

Scorecard 통과 Signal을 1-Page Opportunity Brief로 변환합니다.

## 역할

- Signal + Scorecard → Brief JSON 생성
- Confluence 페이지 자동 생성
- 증거 링크 자동 첨부

## 입력

```json
{
  "signal": {},
  "scorecard": {}
}
```

> signal.schema.json과 scorecard.schema.json 스키마를 따름

## 출력

`brief.schema.json` 준수

## 생성 프로세스

```
1. Signal/Scorecard 데이터 로드
2. Brief 템플릿 필드 채우기
3. 증거 링크 연결
4. JSON 스키마 검증
5. (승인 후) Confluence 페이지 생성
6. Play DB 업데이트
```

## 자동 추론 필드

| 필드 | 추론 소스 |
|------|----------|
| customer.segment | Signal.customer_segment |
| problem.pain | Signal.pain |
| problem.why_now | Scorecard.rationale |
| kpis | Signal.kpi_hypothesis |
| evidence | Signal.evidence |

## 수동 입력 필요 필드

| 필드 | 기본값 | 설명 |
|------|--------|------|
| customer.buyer_role | (empty) | 의사결정자 역할 |
| customer.account | (empty) | 특정 고객사 |
| solution_hypothesis.approach | (empty) | 솔루션 방향 |
| validation_plan.method | "5DAY_SPRINT" | 검증 방법 |

## Confluence 페이지 생성

```python
async def create_confluence_brief(brief: Brief) -> str:
    # 마크다운 본문 생성
    body_md = render_brief_template(brief)
    
    # Confluence 페이지 생성
    result = await confluence.create_page(
        space_key=CONFLUENCE_SPACE_KEY,
        parent_id=BRIEFS_PARENT_ID,
        title=f"[Brief] {brief.title}",
        body_md=body_md,
        labels=["brief", brief.signal_id, brief.customer.segment]
    )
    
    return result.url
```

## Brief 템플릿 (Confluence용)

```markdown
# {title}

| 항목 | 내용 |
|------|------|
| Brief ID | {brief_id} |
| Signal | {signal_id} |
| Scorecard | {total_score}점 / {decision} |
| Owner | {owner} |
| 생성일 | {created_at} |

## 1. Customer
- **Segment**: {customer.segment}
- **Buyer Role**: {customer.buyer_role}
- **Users**: {customer.users}
- **Account**: {customer.account}

## 2. Problem
### Pain
{problem.pain}

### Why Now
{problem.why_now}

### Current Process
{problem.current_process}

## 3. Solution Hypothesis
### Approach
{solution_hypothesis.approach}

### Integration Points
{solution_hypothesis.integration_points}

### Data Needed
{solution_hypothesis.data_needed}

## 4. KPIs
{kpis}

## 5. Evidence
{evidence}

## 6. Validation Plan
- **Method**: {validation_plan.method}
- **Questions**: {validation_plan.questions}
- **Success Criteria**: {validation_plan.success_criteria}
- **Timebox**: {validation_plan.timebox_days}일

## 7. Risks
{risks}
```

## 승인 플로우

```python
# Brief 생성 전 승인 필요
if scorecard.recommendation.decision == "GO":
    approval = await request_approval(
        type="BRIEF_GENERATION",
        approvers=["bd_lead"],
        data={
            "signal_id": signal.signal_id,
            "total_score": scorecard.total_score,
            "brief_preview": brief_draft
        }
    )
    
    if approval.granted:
        brief = await finalize_brief(brief_draft)
        confluence_url = await create_confluence_brief(brief)
```

## 설정

```json
{
  "agent_id": "brief_writer",
  "model": "sonnet",
  "skill": "ax-brief",
  "output_schema": "brief.schema.json",
  "requires_approval": true,
  "approval_type": "BRIEF_GENERATION"
}
```
