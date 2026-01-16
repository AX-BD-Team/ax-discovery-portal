"""
WF-06 Confluence Sync 워크플로

Signal/Scorecard/Brief/Play 데이터를 Confluence에 동기화
"""

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

logger = structlog.get_logger()


# ============================================================
# Enums & Data Models
# ============================================================


class SyncTargetType(str, Enum):
    """동기화 대상 타입"""

    SIGNAL = "signal"
    SCORECARD = "scorecard"
    BRIEF = "brief"
    PLAY = "play"
    ACTIVITY = "activity"
    ALL = "all"


class SyncAction(str, Enum):
    """동기화 액션"""

    CREATE_PAGE = "create_page"
    UPDATE_PAGE = "update_page"
    APPEND_LOG = "append_log"
    UPDATE_TABLE = "update_table"


@dataclass
class SyncTarget:
    """동기화 대상"""

    target_type: SyncTargetType
    target_id: str
    data: dict[str, Any]
    action: SyncAction = SyncAction.CREATE_PAGE
    play_id: str | None = None
    page_id: str | None = None


@dataclass
class SyncInput:
    """동기화 입력"""

    targets: list[SyncTarget] = field(default_factory=list)
    sync_type: str = "realtime"
    play_id: str | None = None
    dry_run: bool = False


@dataclass
class SyncResult:
    """동기화 결과 (단일 대상)"""

    target_type: SyncTargetType
    target_id: str
    action: SyncAction
    status: str
    page_id: str | None = None
    page_url: str | None = None
    error: str | None = None


@dataclass
class SyncOutput:
    """동기화 출력"""

    results: list[SyncResult] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=lambda: {
        "total": 0,
        "success": 0,
        "failed": 0,
        "skipped": 0,
    })


# ============================================================
# Page Formatters
# ============================================================


def format_signal_page(signal: dict[str, Any]) -> str:
    """Signal 페이지 Markdown 포맷"""
    signal_id = signal.get("signal_id", "N/A")
    title = signal.get("title", "N/A")
    source = signal.get("source", "N/A")
    channel = signal.get("channel", "N/A")
    play_id = signal.get("play_id", "N/A")
    status = signal.get("status", "NEW")
    pain = signal.get("pain", "N/A")
    evidence = signal.get("evidence", [])
    tags = signal.get("tags", [])
    created_at = signal.get("created_at", "N/A")

    evidence_md = ""
    if evidence:
        evidence_md = "\n".join([
            f"- [{e.get('title', 'Link')}]({e.get('url', '#')}) - {e.get('note', '')}"
            for e in evidence
        ])
    else:
        evidence_md = "- 없음"

    tags_str = ", ".join(tags) if tags else "없음"

    return f"""# {title}

## 기본 정보

| 항목 | 값 |
|------|-----|
| Signal ID | {signal_id} |
| Play ID | {play_id} |
| Source | {source} |
| Channel | {channel} |
| Status | {status} |
| Created | {created_at} |

## Pain Point

{pain}

## Evidence

{evidence_md}

## Tags

{tags_str}
"""


def format_scorecard_page(scorecard: dict[str, Any]) -> str:
    """Scorecard 페이지 Markdown 포맷"""
    signal_id = scorecard.get("signal_id", "N/A")
    total_score = scorecard.get("total_score", 0)
    dimensions = scorecard.get("dimensions", {})
    decision = scorecard.get("decision", "PENDING")
    rationale = scorecard.get("rationale", "N/A")

    dimensions_md = ""
    for dim_name, dim_data in dimensions.items():
        display_name = dim_name.replace("_", " ").title()
        score = dim_data.get("score", 0) if isinstance(dim_data, dict) else dim_data
        dimensions_md += f"| {display_name} | {score} |\n"

    return f"""# Scorecard: {signal_id}

## 총점

**{total_score}점** / 100점

## 차원별 점수

| 차원 | 점수 |
|------|------|
{dimensions_md}

## 결정

**{decision}**

## 근거

{rationale}
"""


def format_brief_page(brief: dict[str, Any]) -> str:
    """Brief 페이지 Markdown 포맷"""
    brief_id = brief.get("brief_id", "N/A")
    title = brief.get("title", "N/A")
    signal_id = brief.get("signal_id", "N/A")
    status = brief.get("status", "DRAFT")
    executive_summary = brief.get("executive_summary", "N/A")
    problem_statement = brief.get("problem_statement", "N/A")
    proposed_solution = brief.get("proposed_solution", "N/A")
    expected_impact = brief.get("expected_impact", "N/A")
    next_steps = brief.get("next_steps", "N/A")
    created_at = brief.get("created_at", "N/A")

    return f"""# {title}

## 기본 정보

| 항목 | 값 |
|------|-----|
| Brief ID | {brief_id} |
| Signal ID | {signal_id} |
| Status | {status} |
| Created | {created_at} |

## Executive Summary

{executive_summary}

## Problem Statement

{problem_statement}

## Proposed Solution

{proposed_solution}

## Expected Impact

{expected_impact}

## Next Steps

{next_steps}
"""


def format_activity_log(activity: dict[str, Any]) -> str:
    """Activity 로그 행 포맷"""
    activity_id = activity.get("activity_id", "N/A")
    title = activity.get("title", "N/A")
    activity_type = activity.get("type", "N/A")
    owner = activity.get("owner", "N/A")
    status = activity.get("status", "N/A")
    date = activity.get("date", "N/A")

    return f"| {date} | {activity_id} | {title} | {activity_type} | {owner} | {status} |"


# ============================================================
# Mock Confluence Client
# ============================================================


class MockConfluenceClient:
    """Confluence API Mock 클라이언트"""

    def __init__(self):
        self.base_url = os.getenv("CONFLUENCE_BASE_URL", "https://confluence.example.com")
        self.space_key = os.getenv("CONFLUENCE_SPACE_KEY", "AX")
        self.is_configured = bool(os.getenv("CONFLUENCE_API_TOKEN"))

    async def create_page(
        self,
        title: str,
        body_md: str,
        parent_id: str | None = None,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """페이지 생성"""
        if not self.is_configured:
            raise ValueError("Confluence not configured (CONFLUENCE_API_TOKEN missing)")

        page_id = f"mock-{hash(title) % 100000}"
        return {
            "page_id": page_id,
            "url": f"{self.base_url}/wiki/spaces/{self.space_key}/pages/{page_id}",
        }

    async def update_page(
        self,
        page_id: str,
        title: str,
        body_md: str,
    ) -> dict[str, Any]:
        """페이지 수정"""
        if not self.is_configured:
            raise ValueError("Confluence not configured (CONFLUENCE_API_TOKEN missing)")

        return {
            "page_id": page_id,
            "url": f"{self.base_url}/wiki/spaces/{self.space_key}/pages/{page_id}",
        }

    async def append_to_page(
        self,
        page_id: str,
        content: str,
    ) -> dict[str, Any]:
        """페이지에 내용 추가"""
        if not self.is_configured:
            raise ValueError("Confluence not configured (CONFLUENCE_API_TOKEN missing)")

        return {
            "page_id": page_id,
            "url": f"{self.base_url}/wiki/spaces/{self.space_key}/pages/{page_id}",
        }


# ============================================================
# Pipeline Classes
# ============================================================


class ConfluenceSyncPipeline:
    """Confluence 동기화 파이프라인 (기본)"""

    STEPS = [
        {"id": "VALIDATE_TARGETS", "label": "대상 검증"},
        {"id": "PREPARE_CONTENT", "label": "콘텐츠 준비"},
        {"id": "SYNC_PAGES", "label": "페이지 동기화"},
        {"id": "UPDATE_TABLES", "label": "테이블 업데이트"},
        {"id": "FINALIZE", "label": "최종 확인"},
    ]

    def __init__(self):
        self.confluence = MockConfluenceClient()
        self.live_doc_page_id = os.getenv("CONFLUENCE_LIVE_DOC_PAGE_ID")
        self.play_db_page_id = os.getenv("CONFLUENCE_PLAY_DB_PAGE_ID")

    async def run(self, sync_input: SyncInput) -> SyncOutput:
        """파이프라인 실행"""
        logger.info(
            "Starting Confluence Sync pipeline",
            targets_count=len(sync_input.targets),
            dry_run=sync_input.dry_run,
        )

        results = []
        summary = {"total": len(sync_input.targets), "success": 0, "failed": 0, "skipped": 0}

        for target in sync_input.targets:
            if sync_input.dry_run:
                result = SyncResult(
                    target_type=target.target_type,
                    target_id=target.target_id,
                    action=target.action,
                    status="skipped",
                    error="dry_run mode",
                )
                summary["skipped"] += 1
            else:
                result = await self._sync_target(target)
                if result.status == "success":
                    summary["success"] += 1
                elif result.status == "failed":
                    summary["failed"] += 1
                else:
                    summary["skipped"] += 1

            results.append(result)

        logger.info("Confluence Sync pipeline completed", summary=summary)

        return SyncOutput(results=results, summary=summary)

    async def _sync_target(self, target: SyncTarget) -> SyncResult:
        """단일 대상 동기화"""
        try:
            if target.action == SyncAction.CREATE_PAGE:
                return await self._create_page(target)
            elif target.action == SyncAction.UPDATE_PAGE:
                return await self._update_page(target)
            elif target.action == SyncAction.APPEND_LOG:
                return await self._append_log(target)
            elif target.action == SyncAction.UPDATE_TABLE:
                return await self._update_table(target)
            else:
                return SyncResult(
                    target_type=target.target_type,
                    target_id=target.target_id,
                    action=target.action,
                    status="failed",
                    error=f"Unknown action: {target.action}",
                )
        except ValueError as e:
            return SyncResult(
                target_type=target.target_type,
                target_id=target.target_id,
                action=target.action,
                status="failed",
                error=str(e),
            )

    async def _create_page(self, target: SyncTarget) -> SyncResult:
        """페이지 생성"""
        if target.target_type == SyncTargetType.SIGNAL:
            content = format_signal_page(target.data)
            labels = ["signal", target.data.get("play_id", "")]
            parent_id = self.play_db_page_id
        elif target.target_type == SyncTargetType.SCORECARD:
            content = format_scorecard_page(target.data)
            labels = ["scorecard"]
            parent_id = self.play_db_page_id
        elif target.target_type == SyncTargetType.BRIEF:
            content = format_brief_page(target.data)
            labels = ["brief", target.data.get("signal_id", "")]
            parent_id = self.play_db_page_id
        else:
            return SyncResult(
                target_type=target.target_type,
                target_id=target.target_id,
                action=target.action,
                status="failed",
                error=f"Cannot create page for type: {target.target_type}",
            )

        title = target.data.get("title", f"{target.target_type.value}-{target.target_id}")
        result = await self.confluence.create_page(
            title=title,
            body_md=content,
            parent_id=parent_id if parent_id else None,
            labels=[label for label in labels if label],
        )

        return SyncResult(
            target_type=target.target_type,
            target_id=target.target_id,
            action=target.action,
            status="success",
            page_id=result.get("page_id"),
            page_url=result.get("url"),
        )

    async def _update_page(self, target: SyncTarget) -> SyncResult:
        """페이지 수정"""
        if not target.page_id:
            return SyncResult(
                target_type=target.target_type,
                target_id=target.target_id,
                action=target.action,
                status="failed",
                error="page_id is required for update",
            )

        if target.target_type == SyncTargetType.SIGNAL:
            content = format_signal_page(target.data)
        elif target.target_type == SyncTargetType.SCORECARD:
            content = format_scorecard_page(target.data)
        elif target.target_type == SyncTargetType.BRIEF:
            content = format_brief_page(target.data)
        else:
            return SyncResult(
                target_type=target.target_type,
                target_id=target.target_id,
                action=target.action,
                status="failed",
                error=f"Cannot update page for type: {target.target_type}",
            )

        title = target.data.get("title", f"{target.target_type.value}-{target.target_id}")
        result = await self.confluence.update_page(
            page_id=target.page_id,
            title=title,
            body_md=content,
        )

        return SyncResult(
            target_type=target.target_type,
            target_id=target.target_id,
            action=target.action,
            status="success",
            page_id=result.get("page_id"),
            page_url=result.get("url"),
        )

    async def _append_log(self, target: SyncTarget) -> SyncResult:
        """로그 추가"""
        if not self.live_doc_page_id:
            return SyncResult(
                target_type=target.target_type,
                target_id=target.target_id,
                action=target.action,
                status="skipped",
                error="CONFLUENCE_LIVE_DOC_PAGE_ID not configured",
            )

        if target.target_type == SyncTargetType.ACTIVITY:
            content = format_activity_log(target.data)
        else:
            return SyncResult(
                target_type=target.target_type,
                target_id=target.target_id,
                action=target.action,
                status="failed",
                error=f"Cannot append log for type: {target.target_type}",
            )

        result = await self.confluence.append_to_page(
            page_id=self.live_doc_page_id,
            content=content,
        )

        return SyncResult(
            target_type=target.target_type,
            target_id=target.target_id,
            action=target.action,
            status="success",
            page_id=result.get("page_id"),
            page_url=result.get("url"),
        )

    async def _update_table(self, target: SyncTarget) -> SyncResult:
        """테이블 업데이트"""
        return SyncResult(
            target_type=target.target_type,
            target_id=target.target_id,
            action=target.action,
            status="skipped",
            error="UPDATE_TABLE not implemented yet",
        )

    async def sync_signal(self, signal: dict[str, Any], action: SyncAction) -> SyncResult:
        """Signal 동기화"""
        target = SyncTarget(
            target_type=SyncTargetType.SIGNAL,
            target_id=signal.get("signal_id", "unknown"),
            data=signal,
            action=action,
        )
        return await self._sync_target(target)

    async def sync_scorecard(self, scorecard: dict[str, Any], action: SyncAction) -> SyncResult:
        """Scorecard 동기화"""
        target = SyncTarget(
            target_type=SyncTargetType.SCORECARD,
            target_id=scorecard.get("scorecard_id", "unknown"),
            data=scorecard,
            action=action,
        )
        return await self._sync_target(target)

    async def sync_brief(self, brief: dict[str, Any], action: SyncAction) -> SyncResult:
        """Brief 동기화"""
        target = SyncTarget(
            target_type=SyncTargetType.BRIEF,
            target_id=brief.get("brief_id", "unknown"),
            data=brief,
            action=action,
        )
        return await self._sync_target(target)

    async def log_activity(self, activity: dict[str, Any]) -> SyncResult:
        """Activity 로그 추가"""
        target = SyncTarget(
            target_type=SyncTargetType.ACTIVITY,
            target_id=activity.get("activity_id", "unknown"),
            data=activity,
            action=SyncAction.APPEND_LOG,
        )
        return await self._sync_target(target)

    async def update_play_stats(self, play_id: str, stats: dict[str, Any]) -> SyncResult:
        """Play 통계 업데이트"""
        target = SyncTarget(
            target_type=SyncTargetType.PLAY,
            target_id=play_id,
            data=stats,
            action=SyncAction.UPDATE_TABLE,
            play_id=play_id,
        )
        return await self._sync_target(target)


class ConfluenceSyncPipelineWithEvents(ConfluenceSyncPipeline):
    """Confluence 동기화 파이프라인 (이벤트 발행)"""

    def __init__(self, emitter: Any):
        super().__init__()
        self.emitter = emitter

    async def run(self, sync_input: SyncInput) -> SyncOutput:
        """파이프라인 실행 (이벤트 발행)"""
        self.emitter.emit_run_started("WF-06", self.STEPS)

        try:
            self.emitter.emit_step_started("VALIDATE_TARGETS")
            self.emitter.emit_step_finished("VALIDATE_TARGETS")

            self.emitter.emit_step_started("PREPARE_CONTENT")
            self.emitter.emit_step_finished("PREPARE_CONTENT")

            self.emitter.emit_step_started("SYNC_PAGES")
            result = await super().run(sync_input)
            self.emitter.emit_step_finished("SYNC_PAGES")

            self.emitter.emit_step_started("UPDATE_TABLES")
            self.emitter.emit_step_finished("UPDATE_TABLES")

            self.emitter.emit_step_started("FINALIZE")
            self.emitter.emit_step_finished("FINALIZE")

            self.emitter.emit_run_finished(result.summary)
            return result

        except Exception as e:
            self.emitter.emit_run_error(str(e))
            raise


async def run(input_data: dict[str, Any]) -> dict[str, Any]:
    """워크플로 실행 (dict 인터페이스)"""
    targets = []
    for t in input_data.get("targets", []):
        targets.append(SyncTarget(
            target_type=SyncTargetType(t.get("target_type", "signal")),
            target_id=t.get("target_id", ""),
            data=t.get("data", {}),
            action=SyncAction(t.get("action", "create_page")),
            play_id=t.get("play_id"),
            page_id=t.get("page_id"),
        ))

    sync_input = SyncInput(
        targets=targets,
        sync_type=input_data.get("sync_type", "realtime"),
        play_id=input_data.get("play_id"),
        dry_run=input_data.get("dry_run", False),
    )

    pipeline = ConfluenceSyncPipeline()
    result = await pipeline.run(sync_input)

    return {
        "results": [
            {
                "target_type": r.target_type.value,
                "target_id": r.target_id,
                "action": r.action.value,
                "status": r.status,
                "page_id": r.page_id,
                "page_url": r.page_url,
                "error": r.error,
            }
            for r in result.results
        ],
        "summary": result.summary,
    }
