# Monorepo Setup Guide

AX Discovery Portal은 **pnpm workspace** 기반 Monorepo 구조로 구성되어 있습니다.

## 프로젝트 구조

```
ax-discovery-portal/
├── apps/
│   └── web/                    # Next.js 웹 애플리케이션 (PWA)
├── packages/
│   ├── shared/
│   │   ├── api-client/        # FastAPI 클라이언트
│   │   ├── types/             # TypeScript 타입 정의
│   │   ├── utils/             # 유틸리티 함수
│   │   └── config/            # 공통 설정
│   └── ui/                     # shadcn/ui 기반 공통 UI 컴포넌트
├── backend/                    # Python FastAPI 서버
├── .claude/                    # Claude Code 설정
├── pnpm-workspace.yaml         # pnpm workspace 설정
├── package.json                # Root package.json
└── turbo.json                  # Turborepo 설정
```

## 기술 스택

### Frontend (Monorepo)
- **Package Manager**: pnpm 9.15.4+
- **Build Tool**: Turborepo 2.3.3+
- **Framework**: Next.js 15.1.4
- **Language**: TypeScript 5.7.2
- **UI Library**: shadcn/ui (Radix UI + Tailwind CSS)
- **State Management**: Zustand 5.0.2
- **Data Fetching**: TanStack Query 5.64.2
- **HTTP Client**: ky 1.7.3
- **Styling**: Tailwind CSS 3.4.17
- **PWA**: next-pwa 5.6.0

### Backend
- **Runtime**: Python 3.11+
- **Framework**: FastAPI 0.115.0+
- **Server**: Uvicorn 0.32.0+
- **Database**: PostgreSQL (planned)
- **ORM**: SQLAlchemy 2.0.0+ (asyncio)
- **Agent SDK**: Claude Agent SDK (TBD)

## 설치 및 실행

### 1. 사전 요구사항

```bash
# Node.js 20+ 설치 확인
node --version  # v20.0.0 이상

# pnpm 설치 (없는 경우)
npm install -g pnpm@9.15.4

# Python 3.11+ 설치 확인
python --version  # 3.11 이상
```

### 2. 의존성 설치

```bash
# Frontend (pnpm workspace)
pnpm install

# Backend (Python venv)
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 3. 환경 변수 설정

#### Frontend (.env.local)
```bash
# apps/web/.env.local 생성
cp apps/web/.env.local.example apps/web/.env.local

# 내용 확인/수정
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### Backend (.env)
```bash
# 루트 디렉토리에 .env 생성
cp .env.example .env

# Anthropic API Key 등 설정
ANTHROPIC_API_KEY=sk-ant-...
CONFLUENCE_BASE_URL=https://your-domain.atlassian.net
CONFLUENCE_API_TOKEN=...
```

### 4. 개발 서버 실행

#### 옵션 1: 개별 실행

```bash
# Terminal 1 - Backend
pnpm backend:dev
# 또는
cd backend && uvicorn backend.api.main:app --reload

# Terminal 2 - Frontend
pnpm dev:web
# 또는
cd apps/web && pnpm dev
```

> **Note**: `uvicorn` 명령어가 실행되지 않는 경우, 가상 환경이 활성화되어 있는지 확인하세요. 자세한 내용은 [Troubleshooting](#uvicorn-command-not-found) 섹션을 참조하세요.

#### 옵션 2: 동시 실행 (권장)

```bash
# 루트 디렉토리에서
pnpm dev &  # Frontend 백그라운드 실행
pnpm backend:dev  # Backend 포그라운드 실행
```

### 5. 접속 확인

- **Frontend**: http://localhost:3000
- **Backend API Docs**: http://localhost:8000/docs
- **Backend Health**: http://localhost:8000/health

## 개발 워크플로우

### 패키지 간 의존성 관리

```bash
# 새 패키지 추가
pnpm add <package> --filter @ax/web

# workspace 패키지 참조
pnpm add @ax/types --filter @ax/api-client --workspace

# 전체 빌드
pnpm build

# 타입 체크
pnpm type-check

# Lint
pnpm lint
```

### 새 공통 컴포넌트 추가

1. `packages/ui/src/components/` 에 컴포넌트 작성
2. `packages/ui/src/index.ts` 에서 export
3. `apps/web` 에서 `import { Component } from '@ax/ui'`로 사용

### 새 API 엔드포인트 추가

1. `backend/api/routers/` 에 라우터 작성
2. `backend/api/main.py` 에서 라우터 등록
3. `packages/shared/api-client/src/endpoints/` 에 클라이언트 함수 작성
4. `packages/shared/types/src/` 에 TypeScript 타입 정의
5. `apps/web` 에서 사용

## Monorepo의 장점

### 1. 코드 재사용
- `@ax/types`: 백엔드 JSON 스키마와 동기화된 TypeScript 타입
- `@ax/ui`: Web/Mobile에서 동일한 UI 컴포넌트 사용
- `@ax/api-client`: API 호출 로직 중앙 관리

### 2. 타입 안정성
- 백엔드 스키마 → TypeScript 타입 자동 동기화
- 컴파일 타임에 API 계약 검증

### 3. 개발 경험
- 단일 명령어로 전체 프로젝트 빌드/테스트
- pnpm workspace로 의존성 공유
- Turborepo로 빌드 캐싱 및 병렬 처리

## Troubleshooting

### pnpm 설치 오류

```bash
# pnpm 캐시 삭제
pnpm store prune

# node_modules 재설치
rm -rf node_modules
rm pnpm-lock.yaml
pnpm install
```

### TypeScript 경로 인식 오류

```bash
# TypeScript 서버 재시작 (VS Code)
Ctrl+Shift+P → "TypeScript: Restart TS Server"

# 또는 tsconfig.json 수정 후
pnpm type-check
```

### Backend CORS 오류

```bash
# backend/api/main.py의 CORS_ORIGINS에 포트 추가
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    # 추가 포트
]
```

### Uvicorn Command Not Found
`uvicorn` 명령어를 찾을 수 없다는 오류가 발생하는 경우 (Windows):

**방법 1: 가상 환경 활성화 후 실행 (권장)**
```powershell
# 가상 환경 활성화
.\backend\.venv\Scripts\Activate.ps1

# 서버 실행
uvicorn backend.api.main:app --reload --port 8000
```

**방법 2: 가상 환경의 Python으로 직접 실행**
```powershell
& .\backend\.venv\Scripts\python.exe -m uvicorn backend.api.main:app --reload --port 8000
```

## 배포

### Frontend (Vercel/Netlify)

```bash
# 빌드
pnpm build:web

# 빌드 결과: apps/web/.next/
# Vercel: Root Directory를 "apps/web"로 설정
```

### Backend (Docker)

```bash
# Docker 이미지 빌드 (TBD)
docker build -t ax-discovery-portal-backend ./backend

# 실행
docker run -p 8000:8000 ax-discovery-portal-backend
```

## 추가 리소스

- [pnpm Workspace 문서](https://pnpm.io/workspaces)
- [Turborepo 문서](https://turbo.build/repo/docs)
- [Next.js Monorepo 가이드](https://nextjs.org/docs/advanced-features/multi-zones)
- [shadcn/ui 문서](https://ui.shadcn.com)
