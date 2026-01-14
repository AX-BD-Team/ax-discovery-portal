# AX Discovery Portal

> **멀티에이전트 기반 사업기회 포착 엔진** - AX BD팀

Claude Agent SDK를 활용한 멀티에이전트 시스템으로, BD팀의 사업기회 포착 활동을 **Activity → Signal → Scorecard → Brief → Validation(S2) → Pilot-ready(S3)** 파이프라인으로 자동화합니다.

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

```
┌─────────────────────────────────────────────────────────────┐
│                        Client Layer                         │
│              Web (Next.js) / App (PWA/RN)                  │
└─────────────────────────────────────────────────────────────┘
                              │
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
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    MCP Integrations                         │
│           Confluence / Teams / Calendar                     │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+ (Web UI)
- Anthropic API Key
- Confluence API Token

### Installation

```bash
# Clone repository
git clone https://github.com/AX-BD-Team/ax-discovery-portal.git
cd ax-discovery-portal

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Run backend
uvicorn backend.api.main:app --reload
```

### Claude Code Integration

```bash
# Commands 사용
/ax:seminar-add https://event.example.com/ai-summit
/ax:triage --signal-id SIG-2025-001
/ax:brief --signal-id SIG-2025-001
/ax:kpi-digest
```

## 📁 Project Structure

```
ax-discovery-portal/
├── .claude/
│   ├── settings.json          # Claude Code 설정
│   ├── mcp.json               # MCP 서버 설정
│   ├── skills/                # Skills (템플릿/규칙)
│   ├── agents/                # Agent 정의
│   ├── commands/              # CLI Commands
│   └── hooks/                 # Pre/Post Tool Hooks
├── backend/
│   ├── api/                   # FastAPI Backend
│   ├── agent_runtime/         # Agent Runtime
│   └── integrations/          # MCP Servers
├── app/
│   ├── web/                   # Next.js Web App
│   └── mobile/                # React Native App
└── tests/
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
