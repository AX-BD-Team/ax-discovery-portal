# Boilerplate 사용 가이드

> Claude Agent SDK 기반 멀티에이전트 프로젝트 템플릿

## 빠른 시작

### 1. 템플릿 복사

```bash
# 새 프로젝트 디렉토리 생성
cp -r boilerplate/ /path/to/new-project/
cd /path/to/new-project/

# Git 초기화
git init
```

### 2. 플레이스홀더 교체

아래 플레이스홀더를 프로젝트에 맞게 교체하세요:

| 플레이스홀더 | 설명 | 예시 |
|-------------|------|------|
| `{{PROJECT_NAME}}` | 프로젝트 이름 | `ax-discovery-portal` |
| `{{PROJECT_DESCRIPTION}}` | 프로젝트 설명 | `멀티에이전트 기반 사업기회 포착 엔진` |
| `{{project-name}}` | 패키지 이름 (kebab-case) | `ax-discovery-portal` |
| `{{project-cli}}` | CLI 명령어 | `ax-portal` |
| `{{author-name}}` | 저자/팀 이름 | `AX BD Team` |
| `{{org}}` | GitHub 조직 | `AX-BD-Team` |

```bash
# 일괄 교체 (sed 사용)
find . -type f -name "*.md" -o -name "*.json" -o -name "*.toml" -o -name "*.yaml" | \
  xargs sed -i 's/{{PROJECT_NAME}}/your-project-name/g'
```

### 3. 환경 설정

```bash
# 환경 변수 설정
cp .env.example .env
# .env 파일 편집하여 API 키 등 설정

# Python 가상환경 설정
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Node.js 패키지 설치 (프론트엔드 사용 시)
pnpm install
```

### 4. 프로젝트 커스터마이징

#### A. 도메인 온톨로지 정의

`backend/database/models/entity.py`에서 EntityType 정의:

```python
class EntityType(enum.Enum):
    # 프로젝트 도메인에 맞게 정의
    SIGNAL = "Signal"
    BRIEF = "Brief"
    ORGANIZATION = "Organization"
    # ...
```

`backend/database/models/triple.py`에서 PredicateType 정의:

```python
class PredicateType(enum.Enum):
    # 엔티티 간 관계 정의
    GENERATES = "generates"  # Activity -> Signal
    TARGETS = "targets"      # Signal -> Organization
    # ...
```

#### B. 에이전트 정의

`.claude/agents/` 디렉토리에 에이전트 추가:

```bash
cp .claude/agents/_AGENT_TEMPLATE.md .claude/agents/my_agent.md
# 템플릿 내용 수정
```

#### C. Skill 정의

`.claude/skills/` 디렉토리에 Skill 추가:

```bash
cp -r .claude/skills/_skill-template/ .claude/skills/my-skill/
# SKILL.md 내용 수정
```

#### D. Eval Task 정의

`evals/tasks/` 디렉토리에 평가 Task 추가:

```bash
cp evals/tasks/workflow/_task_template.yaml evals/tasks/workflow/my-task.yaml
# Task 내용 수정
```

---

## 디렉토리 구조

```
{{project-name}}/
├── .claude/                     # Claude Code 설정
│   ├── agents/                  # 에이전트 정의
│   │   ├── _AGENT_TEMPLATE.md   # 에이전트 템플릿
│   │   └── orchestrator.md      # 기본 오케스트레이터
│   ├── skills/                  # Skill 정의
│   │   └── _skill-template/     # Skill 템플릿
│   ├── commands/                # Command 정의
│   ├── prompts/                 # LLM 프롬프트 템플릿
│   │   ├── entity-extraction.md
│   │   ├── relation-extraction.md
│   │   └── entity-resolution.md
│   ├── hooks/                   # Tool use 훅
│   └── settings.json            # Claude Code 설정
│
├── backend/                     # FastAPI 백엔드
│   ├── api/                     # REST API
│   │   └── routers/             # 라우터
│   ├── agent_runtime/           # 에이전트 런타임
│   │   ├── ontology/            # Ontology-LLM 구조
│   │   │   └── validator.py     # Triple 검증기
│   │   └── workflows/           # 워크플로
│   ├── database/                # 데이터베이스
│   │   ├── models/              # SQLAlchemy 모델
│   │   │   ├── entity.py        # Entity 모델
│   │   │   └── triple.py        # Triple 모델
│   │   └── repositories/        # 리포지토리
│   ├── evals/                   # Eval 런타임
│   └── core/                    # 설정, 로깅
│
├── evals/                       # 평가 정의 (YAML)
│   ├── schemas/                 # JSON Schema
│   │   ├── task.schema.json
│   │   └── suite.schema.json
│   ├── suites/                  # 평가 스위트
│   │   ├── regression/
│   │   └── capability/
│   ├── tasks/                   # 평가 과제
│   │   ├── workflow/
│   │   └── agents/
│   └── rubrics/                 # LLM Judge 루브릭
│
├── tests/                       # pytest 테스트
├── docs/                        # 문서
├── CLAUDE.md                    # 프로젝트 개발 문서
├── pyproject.toml               # Python 설정
├── package.json                 # Node.js 설정
└── .env.example                 # 환경 변수 예시
```

---

## 핵심 컴포넌트

### 1. SSDD 방법론

**SSDD (Skillful Spec-Driven Development)** = SDD + Claude Skills Integration

- 명세 기반 개발
- Claude Skills로 반복 작업 자동화
- 체계적인 버전 관리

### 2. Ontology-LLM 구조

- **Entity**: 도메인 개체 (노드)
- **Triple**: 관계 (엣지) - Subject-Predicate-Object
- **Validator**: 관계 제약 검증
- **LLM 프롬프트**: 엔티티/관계 추출

### 3. AI 에이전트 평가 (Evals)

- **Task**: 단일 테스트 케이스
- **Suite**: Task 묶음 (regression/capability)
- **Grader**: 채점 로직 (deterministic/LLM/human)
- **Trial**: 비결정성 처리 (pass@k)

### 4. Agent/Skill 시스템

- **Agent**: 특정 역할 담당 (orchestrator, 도메인 에이전트)
- **Skill**: 반복 작업 자동화 (/wrap-up, /health-check)
- **Command**: 사용자 명령어 인터페이스

---

## 다음 단계

1. [ ] 플레이스홀더 교체
2. [ ] 도메인 온톨로지 정의 (EntityType, PredicateType)
3. [ ] 첫 번째 에이전트 정의
4. [ ] 첫 번째 Skill 정의
5. [ ] Eval Task 작성
6. [ ] CI/CD 설정

---

## 참고 자료

- [Claude Agent SDK 문서](https://docs.anthropic.com/claude/docs/agent-sdk)
- [Anthropic Engineering: Evaluating AI Agents](https://www.anthropic.com/engineering/evaluating-ai-agents)
- 원본 프로젝트: `ax-discovery-portal`
