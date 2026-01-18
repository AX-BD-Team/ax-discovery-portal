# Troubleshooting Guide

로컬 개발 환경에서 발생할 수 있는 문제와 해결 방법을 정리합니다.

## 목차

- [CORS 에러](#cors-에러)
- [PostgreSQL 연결 문제](#postgresql-연결-문제)
- [psycopg async 호환성 문제](#psycopg-async-호환성-문제)

---

## CORS 에러

### 증상

브라우저 콘솔에 다음과 같은 에러가 표시됩니다:

```
Access to fetch at 'http://localhost:8000/api/...' from origin 'http://localhost:4000'
has been blocked by CORS policy: Response to preflight request doesn't pass access
control check: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

### 원인

프론트엔드 개발 서버의 포트(예: 4000)가 백엔드 CORS 허용 목록에 없습니다.

### 해결 방법

`backend/api/main.py`의 `CORS_ORIGINS` 리스트에 해당 포트를 추가합니다:

```python
CORS_ORIGINS = [
    # Development
    "http://localhost:3000",
    "http://localhost:4000",  # 추가
    "http://127.0.0.1:4000",  # 추가
    # ...
]
```

변경 후 백엔드 서버를 재시작합니다.

---

## PostgreSQL 연결 문제

### 증상

`/ready` 엔드포인트에서 다음과 같은 응답이 반환됩니다:

```json
{
  "status": "degraded",
  "components": {
    "database": "error: ..."
  }
}
```

### 원인

1. PostgreSQL이 실행 중이지 않음
2. DATABASE_URL이 잘못 설정됨

### 해결 방법

#### 1. Docker로 PostgreSQL 시작

```bash
# Docker Desktop 실행 후
docker run -d \
  --name ax-postgres \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=ax_discovery \
  -p 5432:5432 \
  postgres:15
```

#### 2. .env 파일 설정

로컬 개발 시:
```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ax_discovery
```

원격 서버 (Render) 사용 시:
```env
DATABASE_URL=postgresql+asyncpg://user:password@host/database
```

#### 3. 마이그레이션 실행

```bash
python -m alembic upgrade head
```

#### 4. 컨테이너 관리 명령어

```bash
# 상태 확인
docker ps --filter name=ax-postgres

# 로그 확인
docker logs ax-postgres

# 중지
docker stop ax-postgres

# 재시작
docker start ax-postgres

# 삭제 (데이터 포함)
docker rm -f ax-postgres
```

---

## psycopg async 호환성 문제

### 증상

`/ready` 엔드포인트에서 다음과 같은 에러가 반환됩니다:

```json
{
  "components": {
    "database": "error: (psycopg.InterfaceError) Psycopg cannot use the 'P..."
  }
}
```

전체 에러 메시지:
```
psycopg.InterfaceError: Psycopg cannot use the 'Pool' class in async mode.
Use 'AsyncPool' instead.
```

### 원인

`psycopg[binary]` 패키지는 C extension을 사용하는데, 이는 SQLAlchemy의 async 모드와 호환되지 않습니다.

### 해결 방법

#### 방법 1: asyncpg 드라이버 사용 (권장)

1. asyncpg 설치:
```bash
pip install asyncpg
```

2. DATABASE_URL을 asyncpg 드라이버로 변경:
```env
# 변경 전
DATABASE_URL=postgresql+psycopg://...

# 변경 후
DATABASE_URL=postgresql+asyncpg://...
```

3. `backend/database/session.py`에서 자동 변환 로직 확인:
```python
# psycopg → asyncpg 자동 변환
if _raw_url.startswith("postgresql+psycopg://"):
    DATABASE_URL = _raw_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
```

#### 방법 2: 환경 변수 명시적 설정

서버 시작 시 환경 변수를 명시적으로 설정:

```bash
# Windows
set DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ax_discovery
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000

# Linux/Mac
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/ax_discovery \
python -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8000
```

### 참고: 드라이버 비교

| 드라이버 | 패키지 | async 지원 | 비고 |
|---------|--------|-----------|------|
| psycopg (binary) | `psycopg[binary]` | ❌ | C extension, sync 전용 |
| psycopg (pure) | `psycopg` | ⚠️ | Pure Python, 느림 |
| asyncpg | `asyncpg` | ✅ | async 전용, 권장 |

---

## 빠른 진단 명령어

```bash
# 서버 상태 확인
curl http://localhost:8000/ready

# PostgreSQL 컨테이너 상태
docker ps --filter name=ax-postgres

# 데이터베이스 직접 연결 테스트
python -c "
import asyncpg
import asyncio
async def test():
    conn = await asyncpg.connect('postgresql://postgres:postgres@localhost:5432/ax_discovery')
    result = await conn.fetchval('SELECT 1')
    print('DB 연결 성공:', result)
    await conn.close()
asyncio.run(test())
"

# Python 프로세스 확인 (Windows)
tasklist | findstr python

# 포트 사용 확인 (Windows)
netstat -ano | findstr :8000
netstat -ano | findstr :5432
```

---

## 관련 파일

| 파일 | 설명 |
|------|------|
| `backend/api/main.py` | CORS 설정 |
| `backend/database/session.py` | DB 연결 설정 |
| `.env` | 환경 변수 |
| `.env.example` | 환경 변수 예시 |
