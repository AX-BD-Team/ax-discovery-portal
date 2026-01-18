# AX Discovery Portal - Evals (AI 에이전트 평가)

> AI 에이전트 품질을 자동으로 평가하는 플랫폼

## 디렉토리 구조

```
evals/
├── schemas/                    # JSON Schema 정의
│   ├── task.schema.json       # Task YAML 스키마
│   ├── suite.schema.json      # Suite YAML 스키마
│   └── grader.schema.json     # Grader 설정 스키마
├── suites/                     # 평가 스위트
│   ├── regression/            # 회귀 테스트 (CI 게이트)
│   │   └── workflow-regression.yaml
│   └── capability/            # 역량 테스트 (품질 추적)
│       └── brief-capability.yaml
├── tasks/                      # 개별 Task 정의
│   ├── workflow/              # 워크플로 테스트
│   │   ├── wf01-seminar-basic.yaml
│   │   ├── wf02-brief-generation.yaml
│   │   └── scorecard-accuracy.yaml
│   ├── coding/                # 코딩 테스트 (예정)
│   └── conversational/        # 대화형 테스트 (예정)
├── graders/                    # 커스텀 채점기 (예정)
└── rubrics/                    # LLM Judge 루브릭
    └── brief_quality.md
```

## 핵심 개념

| 개념 | 설명 |
|------|------|
| **Task** | 단일 테스트 케이스 (입력 + 성공 기준) |
| **Trial** | Task의 1회 실행 시도 (비결정성 → 복수 실행) |
| **Suite** | Task 묶음 (regression vs capability) |
| **Grader** | 채점 로직 (deterministic / LLM / human) |
| **Transcript** | 실행 기록 (도구 호출, 중간 상태) |
| **Outcome** | 최종 결과 상태 (검증 대상) |

## 빠른 시작

### 1. Task 작성

```yaml
# evals/tasks/workflow/my-task.yaml
task:
  id: my-task
  type: workflow
  desc: "테스트 설명"
  suite: workflow_regression

  inputs:
    prompt: "에이전트에게 전달할 프롬프트"

  graders:
    - type: deterministic_tests
      config:
        test_files: ["tests/test_my_feature.py"]

  scoring:
    mode: weighted
    pass_threshold: 0.8
```

### 2. Suite에 추가

```yaml
# evals/suites/regression/workflow-regression.yaml
suite:
  tasks:
    - path: "evals/tasks/workflow/my-task.yaml"
```

### 3. 실행 (예정)

```bash
# 단일 Task 실행
ax-eval run evals/tasks/workflow/my-task.yaml

# Suite 실행
ax-eval run-suite evals/suites/regression/workflow-regression.yaml

# CI 게이트 체크
ax-eval gate --suite workflow_regression
```

## 채점기 유형

### Deterministic (결정적)

| 유형 | 용도 |
|------|------|
| `deterministic_tests` | pytest, jest 등 테스트 실행 |
| `static_analysis` | ruff, mypy, eslint 등 정적 분석 |
| `string_match` | 문자열 포함/일치 검사 |
| `regex_match` | 정규식 패턴 매칭 |
| `state_check` | DB/파일/API 상태 검증 |

### LLM-as-Judge

| 유형 | 용도 |
|------|------|
| `llm_rubric` | 루브릭 기반 다차원 평가 |
| `llm_assertion` | 자연어 assertion 검증 |
| `llm_pairwise` | 두 결과 비교 평가 |
| `llm_reference` | 레퍼런스와 비교 |

### Human Review

| 유형 | 용도 |
|------|------|
| `human_review` | SME 스팟체크, 합치도(IAA) 관리 |

## 비결정성 처리

```yaml
trials:
  k: 5  # 5회 실행
```

- **pass@k**: k번 중 1번만 성공해도 통과 (한 번의 성공이 가치)
- **pass^k**: k번 모두 성공해야 통과 (매번 신뢰성 필요)

## 채점 원칙

1. **Outcome 중심**: 도구 호출 순서가 아닌 최종 결과 검증
2. **부분 점수**: 이진(pass/fail)보다 연속적 개선 신호
3. **Anti-cheat**: 에이전트가 평가를 우회하지 못하도록 설계

## 스키마 검증

```bash
# Task YAML 검증
npx ajv validate -s evals/schemas/task.schema.json -d evals/tasks/**/*.yaml

# Suite YAML 검증
npx ajv validate -s evals/schemas/suite.schema.json -d evals/suites/**/*.yaml
```

## 참고 문서

- [설계안 v1.0](../docs/AI%20에이전트%20평가(Evals)%20플랫폼%20시스템%20설계안%20v1.0.pdf)
- [Anthropic Engineering: Evaluating AI Agents](https://www.anthropic.com/engineering/evaluating-ai-agents)
- [project-todo.md Phase 5](../project-todo.md)
