# /ax:seminar-add Command

세미나 URL을 입력하면 Activity를 생성하고 AAR 템플릿을 준비합니다.

## 사용법

```
/ax:seminar-add <URL> [--theme <themes>] [--play <play_id>]
```

## 인자

| 인자 | 필수 | 설명 | 예시 |
|------|------|------|------|
| `URL` | ✅ | 세미나 URL | https://event.example.com/... |
| `--theme` | | 관심 테마 (쉼표 구분) | AI,금융,자동화 |
| `--play` | | Play ID | EXT_Desk_D01_Seminar |

## 실행 워크플로

**WF-01 Seminar Pipeline**

```
1. URL 메타데이터 추출
2. Activity 생성
3. AAR 템플릿 생성
4. Confluence Live doc 기록
5. (선택) 캘린더 등록
```

## 출력

```
✅ Activity 생성 완료

📅 세미나: AI Summit 2025 - 금융AI 트랙
📍 일시: 2025-01-20 14:00
🏢 주최: TechConf Korea

📝 Activity ID: ACT-2025-001
📂 Play: EXT_Desk_D01_Seminar

📋 AAR 템플릿이 준비되었습니다:
https://confluence.../aar-ACT-2025-001

➡️ 참석 후 '/ax:aar ACT-2025-001' 명령으로 AAR 작성을 시작하세요.
```

## 예시

```bash
# 기본 사용
/ax:seminar-add https://event.example.com/ai-summit-2025

# 테마 지정
/ax:seminar-add https://event.example.com/ai-summit-2025 --theme AI,금융

# Play ID 지정
/ax:seminar-add https://event.example.com/ai-summit-2025 --play EXT_Desk_D01_Seminar
```

## 에러 처리

| 에러 | 메시지 | 해결 방법 |
|------|--------|----------|
| URL 파싱 실패 | "URL에서 정보를 추출할 수 없습니다" | 수동 입력 프롬프트 |
| 중복 Activity | "이미 등록된 세미나입니다" | 기존 Activity 링크 |
| Confluence 연결 실패 | "Confluence 연결 실패" | 재시도 또는 로컬 저장 |

## 관련 커맨드

- `/ax:aar <activity_id>` - AAR 작성 시작
- `/ax:triage` - Signal 평가 큐로 이동
