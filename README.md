# AX Discovery Portal

> **멀티에이전트 기반 사업기회 포착 엔진** - AX BD팀
> **Status**: ✅ Monorepo 전환 완료 | 🚧 Phase 2 In Progress (Integration)

Claude Agent SDK를 활용한 멀티에이전트 시스템으로, BD팀의 사업기회 포착 활동을 **Activity → Signal → Scorecard → Brief → Validation(S2) → Pilot-ready(S3)** 파이프라인으로 자동화합니다.

**🎉 새로운 기능**: pnpm workspace 기반 Monorepo 구조로 전환하여 **Web/Mobile 동시 지원** 가능

## 🎯 PoC 목표 (6주)

| 지표 | 주간 목표 |
|------|----------|
| Activity | 20+ |
| Signal | 30+ |
| Brief | 6+ |
| S2 (Validated) | 2~4 |

| 리드타임 | 목표 |
|----------|------|
| Signal → Brief | ≤ 7일 |
| Brief → S2 착수 | ≤ 14일 |

## 🏗️ Architecture

### Monorepo 구조

```
ax-discovery-portal/ (Monorepo Root)
├── apps/
│   └── web/                    # Next.js 15 (PWA) ✅ 구현 완료
├── packages/
│   ├── shared/
│   │   ├── api-client/        # FastAPI 클라이언트 ✅
│   │   ├── types/             # TypeScript 타입 정의 ✅
│   │   ├── utils/             # 유틸리티 함수 ✅
│   │   └── config/            # 공통 설정 ✅
│   └── ui/                     # shadcn/ui 컴포넌트 ✅
├── backend/                    # FastAPI 서버 (기존)
└── .claude/                    # Claude Code 설정 (기존)
```

### 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Layer (Monorepo)                  │
│    apps/web (Next.js PWA) ← packages/ui, api-client, types │
└─────────────────────────────────────────────────────────────┘
                              │ REST API
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Backend API (FastAPI)                   │
│  /api/inbox  /api/scorecard  /api/brief  /api/plays        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Agent Runtime                            │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ Orchestrator │ │  Evaluator   │ │ BriefWriter  │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ExternalScout │ │ConfluenceSync│ │  Governance  │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
└─────────────────────────────────────────────────────────────┘
                              │ MCP Protocol
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCP Integrations                         │
│           Confluence / Teams / Calendar                     │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Node.js** 20+
- **Python** 3.11+
- **pnpm** 9.15.4+
- Anthropic API Key
- Confluence API Token

### Installation

```bash
# 1. Clone repository
git clone https://github.com/AX-BD-Team/ax-discovery-portal.git
cd ax-discovery-portal

# 2. Frontend 의존성 설치 (pnpm workspace)
pnpm install

# 3. Backend 의존성 설치 (Python venv)
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cd ..

# 4. 환경 변수 설정
cp .env.example .env
cp apps/web/.env.local.example apps/web/.env.local
# .env 파일들을 편집하여 API 키 등 설정

# 5. 실행
# Terminal 1: Backend
pnpm backend:dev

# Terminal 2: Frontend
pnpm dev:web
```

**접속 확인**:
- Frontend: http://localhost:3000
- Backend API Docs: http://localhost:8000/docs
- Backend Health: http://localhost:8000/health

자세한 Monorepo 설정 가이드는 [MONOREPO_SETUP.md](./MONOREPO_SETUP.md)를 참조하세요.

### Claude Code Integration

```bash
# Commands 사용
/ax:seminar-add https://event.example.com/ai-summit
/ax:triage --signal-id SIG-2025-001
/ax:brief --signal-id SIG-2025-001
/ax:kpi-digest
```

### ⚠️ 현재 구현 상태

**🎉 완성된 기능**:
- ✅ **Monorepo 구조**: pnpm workspace + Turborepo
- ✅ **Frontend 프레임워크**: Next.js 15 (App Router, PWA)
- ✅ **공유 패키지**:
  - `@ax/api-client`: FastAPI 클라이언트 (ky 기반)
  - `@ax/types`: TypeScript 타입 정의 (백엔드 스키마 동기화)
  - `@ax/utils`: 유틸리티 함수 (날짜, 포맷, 검증)
  - `@ax/config`: 공통 설정 (환경변수, 상수)
  - `@ax/ui`: shadcn/ui 컴포넌트 (Button, Card, Dialog 등)
- ✅ 6개 에이전트 정의 (orchestrator, external_scout, scorecard_evaluator, brief_writer, confluence_sync, governance)
- ✅ 5개 Skills (ax-scorecard, ax-brief, ax-sprint, ax-seminar, ax-confluence)
- ✅ 4개 Commands (/ax:seminar-add, /ax:triage, /ax:brief, /ax:kpi-digest)
- ✅ 7개 JSON Schema 데이터 모델 (signal, scorecard, brief, validation, pilot_ready, play_record, action_log)
- ✅ 6개 워크플로우 골격 (WF-01~06)
- ✅ FastAPI API 라우터 4개 (inbox, scorecard, brief, play_dashboard)
- ✅ Confluence MCP 서버 (페이지 생성/수정/검색/append)
- ✅ pytest 테스트 케이스

**🚧 진행 중**:
- 🚧 데이터베이스 연동 (PostgreSQL + SQLAlchemy)
- 🚧 Claude Agent SDK 통합
- 🚧 Confluence Database API 구현
- 🚧 Teams 연동
- 🚧 프론트엔드 페이지 구현 (Inbox, Scorecard, Brief 등)

## 📁 Project Structure

```
ax-discovery-portal/ (Monorepo)
├── apps/
│   └── web/                   # Next.js 15 Web App (PWA)
│       ├── src/
│       │   ├── app/          # App Router
│       │   └── components/   # 페이지별 컴포넌트
│       ├── public/           # Static assets
│       ├── next.config.ts    # Next.js + PWA 설정
│       └── package.json
│
├── packages/
│   ├── shared/
│   │   ├── api-client/       # FastAPI 클라이언트
│   │   │   └── src/endpoints/ # API 엔드포인트별 클라이언트
│   │   ├── types/            # TypeScript 타입
│   │   │   └── src/          # signal, scorecard, brief, play 타입
│   │   ├── utils/            # 유틸리티
│   │   │   └── src/          # format, validation, cn
│   │   └── config/           # 공통 설정
│   │       └── src/          # env, constants
│   └── ui/                   # shadcn/ui 컴포넌트
│       └── src/components/   # Button, Card, Dialog 등
│
├── backend/
│   ├── api/                  # FastAPI Backend
│   │   ├── main.py          # App + CORS
│   │   └── routers/         # inbox, scorecard, brief, plays
│   ├── agent_runtime/        # Agent Runtime
│   │   ├── runner.py        # AgentRuntime
│   │   ├── models/          # JSON Schema
│   │   └── workflows/       # WF-01~06
│   └── integrations/         # MCP Servers
│       ├── mcp_confluence/  # Confluence MCP
│       └── mcp_teams/       # Teams MCP
│
├── .claude/
│   ├── settings.json         # Claude Code 설정
│   ├── mcp.json             # MCP 서버 설정
│   ├── skills/              # Skills (5개)
│   ├── agents/              # Agent 정의 (6개)
│   ├── commands/            # CLI Commands (4개)
│   └── hooks/               # Pre/Post Tool Hooks
│
├── tests/                    # Backend tests
├── pnpm-workspace.yaml       # pnpm workspace 설정
├── package.json              # Root package.json
└── turbo.json                # Turborepo 설정
```

## 🔧 Workflows

| ID | 이름 | 트리거 | 설명 |
|----|------|--------|------|
| WF-01 | Seminar Pipeline | `/ax:seminar-add` | 세미나 → Activity → AAR → Signal |
| WF-02 | Interview-to-Brief | `/ax:interview` | 인터뷰 → Signal → Scorecard → Brief |
| WF-03 | VoC Mining | `/ax:voc` | VoC → 테마화 → Signal |
| WF-04 | Inbound Triage | Intake Form | 중복 체크 → Scorecard → Brief |
| WF-05 | KPI Digest | 주간 배치 | 전환율/리드타임 리포트 |
| WF-06 | Confluence Sync | 모든 워크플로 | DB/Live doc 업데이트 |

## 📊 Scorecard 평가 기준 (100점)

| 차원 | 배점 |
|------|------|
| Problem Severity | 20점 |
| Willingness to Pay | 20점 |
| Data Availability | 20점 |
| Feasibility | 20점 |
| Strategic Fit | 20점 |

**Decision:** GO (70+) / PIVOT (50-69) / HOLD (30-49) / NO_GO (<30)

## 📄 License

MIT License - AX BD Team
