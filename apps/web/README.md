# AX Discovery Portal - Web Application

Next.js 15 기반 웹 애플리케이션

## 구현된 페이지

### ✅ Inbox (/inbox)
**Signal 관리 및 Triage 페이지**

#### 주요 기능
1. **Signal 목록 조회**
   - TanStack Query를 사용한 실시간 데이터 fetching
   - 상태별, 소스별 필터링
   - 키워드 검색
   - 탭별 그룹화 (All, New, Scored, Brief)

2. **Signal 생성**
   - 모달 다이얼로그로 새 Signal 추가
   - 필수 필드: Title, Source, Channel, Pain Point
   - 선택 필드: Customer Segment, Proposed Value, KPI Hypothesis, Tags

3. **Signal 상세 보기** (/inbox/[id])
   - Signal 전체 정보 표시
   - Evidence 목록
   - Scorecard 정보 (평가 완료 시)
   - 상태별 액션 버튼

4. **Triage 실행**
   - NEW 상태의 Signal에 대해 Scorecard 평가 트리거
   - 자동으로 목록 새로고침

5. **Stats Dashboard**
   - 전체 Signal 수
   - 상태별 Signal 개수

#### 사용된 기술
- **데이터 fetching**: TanStack Query (React Query)
- **API 클라이언트**: `@ax/api-client`
- **타입**: `@ax/types`
- **UI 컴포넌트**: `@ax/ui` (shadcn/ui)
- **유틸리티**: `@ax/utils` (날짜 포맷, 상태 색상 등)
- **아이콘**: lucide-react

#### 파일 구조
```
apps/web/src/app/inbox/
├── page.tsx                          # 메인 Inbox 페이지
├── [id]/
│   └── page.tsx                      # Signal 상세 페이지
└── components/
    ├── signal-card.tsx               # Signal 카드 컴포넌트
    └── create-signal-dialog.tsx      # Signal 생성 다이얼로그
```

## 다음 구현 예정

### 🚧 Scorecard (/scorecard)
- Scorecard 목록
- 평가 상세 보기
- 점수 분포 차트

### 🚧 Brief (/brief)
- Brief 목록
- Brief 생성 및 편집
- Confluence 발행

### 🚧 Play Dashboard (/plays)
- Play별 진행 현황
- KPI 대시보드

## 개발 가이드

### 새 페이지 추가
1. `apps/web/src/app/[page-name]/page.tsx` 생성
2. API 클라이언트 사용: `import { api } from '@ax/api-client'`
3. 타입 import: `import type { TypeName } from '@ax/types'`
4. UI 컴포넌트 사용: `import { Button } from '@ax/ui'`

### API 호출 패턴
```typescript
import { useQuery, useMutation } from '@tanstack/react-query'
import { inboxApi } from '@ax/api-client'

// 데이터 조회
const { data, isLoading } = useQuery({
  queryKey: ['signals'],
  queryFn: inboxApi.getSignals,
})

// 데이터 변경
const mutation = useMutation({
  mutationFn: inboxApi.createSignal,
  onSuccess: () => {
    queryClient.invalidateQueries({ queryKey: ['signals'] })
  },
})
```

## 접속
- **개발 서버**: http://localhost:3002
- **Inbox**: http://localhost:3002/inbox
