"""
Play 동기화 서비스

Play DB ↔ Confluence 자동 동기화
"""

import os
import re
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.brief import OpportunityBrief
from backend.database.models.play_record import PlayRecord
from backend.database.models.signal import Signal
from backend.database.repositories.play_record import play_record_repo
from backend.integrations.mcp_confluence.server import ConfluenceMCP

logger = structlog.get_logger()


class PlaySyncService:
    """
    Play DB ↔ Confluence 동기화 서비스

    주요 기능:
    - Play 통계 자동 집계 (Signal/Brief/S2 건수)
    - RAG 상태 자동 계산
    - Confluence Play DB 테이블 업데이트
    """

    def __init__(self):
        self.confluence = ConfluenceMCP()
        self.logger = logger.bind(service="play_sync")

        # Confluence Play DB 페이지 ID (환경변수에서 설정)
        self.play_db_page_id = os.getenv("CONFLUENCE_PLAY_DB_PAGE_ID", "")

    async def update_play_stats_from_db(self, db: AsyncSession, play_id: str) -> PlayRecord | None:
        """
        DB 집계 → PlayRecord 업데이트

        Signal/Brief 건수를 집계하여 PlayRecord 실적 필드 업데이트

        Args:
            db: 데이터베이스 세션
            play_id: Play ID

        Returns:
            PlayRecord | None: 업데이트된 PlayRecord
        """
        play = await play_record_repo.get_by_id(db, play_id)
        if not play:
            self.logger.warning("Play not found", play_id=play_id)
            return None

        # Signal 건수 집계
        signal_count_result = await db.execute(
            select(func.count()).select_from(Signal).where(Signal.play_id == play_id)
        )
        signal_count = signal_count_result.scalar() or 0

        # Brief 건수 집계
        brief_count_result = await db.execute(
            select(func.count())
            .select_from(OpportunityBrief)
            .where(
                OpportunityBrief.signal_id.in_(
                    select(Signal.signal_id).where(Signal.play_id == play_id)
                )
            )
        )
        brief_count = brief_count_result.scalar() or 0

        # S2 건수 집계 (status = 's2_validated' 기준)
        s2_count_result = await db.execute(
            select(func.count())
            .select_from(OpportunityBrief)
            .where(
                OpportunityBrief.signal_id.in_(
                    select(Signal.signal_id).where(Signal.play_id == play_id)
                ),
                OpportunityBrief.status == "s2_validated",
            )
        )
        s2_count = s2_count_result.scalar() or 0

        # PlayRecord 업데이트
        play.signal_qtd = signal_count
        play.brief_qtd = brief_count
        play.s2_qtd = s2_count

        # RAG 상태 자동 계산
        new_rag = play.calculate_rag_status()
        play.status = new_rag  # type: ignore[assignment]

        play.last_updated = datetime.now(UTC)

        await db.flush()
        await db.refresh(play)

        self.logger.info(
            "Play stats updated",
            play_id=play_id,
            signal_qtd=signal_count,
            brief_qtd=brief_count,
            s2_qtd=s2_count,
            rag=new_rag,
        )

        return play

    async def sync_play_to_confluence(self, db: AsyncSession, play_id: str) -> dict[str, Any]:
        """
        단일 Play Confluence 동기화

        Args:
            db: 데이터베이스 세션
            play_id: Play ID

        Returns:
            dict: 동기화 결과
        """
        if not self.play_db_page_id:
            return {"status": "skipped", "reason": "CONFLUENCE_PLAY_DB_PAGE_ID not configured"}

        play = await play_record_repo.get_by_id(db, play_id)
        if not play:
            return {"status": "error", "reason": "Play not found"}

        try:
            # 1. Confluence 페이지 조회
            page = await self.confluence.get_page(self.play_db_page_id)
            body = page["body"]

            # 2. 테이블 행 찾아서 업데이트
            updated_body = self._update_play_row_in_table(body, play)

            # 3. 페이지 업데이트
            if updated_body != body:
                await self.confluence.update_page(
                    page_id=self.play_db_page_id,
                    body_md=updated_body,
                )
                self.logger.info("Confluence sync completed", play_id=play_id)
                return {"status": "synced", "play_id": play_id}
            else:
                return {"status": "no_change", "play_id": play_id}

        except Exception as e:
            self.logger.error("Confluence sync failed", play_id=play_id, error=str(e))
            return {"status": "error", "play_id": play_id, "error": str(e)}

    async def sync_all_plays_to_confluence(self, db: AsyncSession) -> dict[str, Any]:
        """
        전체 Play Confluence 동기화

        Args:
            db: 데이터베이스 세션

        Returns:
            dict: 동기화 결과
        """
        if not self.play_db_page_id:
            return {"status": "skipped", "reason": "CONFLUENCE_PLAY_DB_PAGE_ID not configured"}

        plays = await play_record_repo.get_all(db)

        results: dict[str, Any] = {"total": len(plays), "synced": 0, "errors": []}

        try:
            # 1. Confluence 페이지 조회
            page = await self.confluence.get_page(self.play_db_page_id)
            body = page["body"]

            # 2. 모든 Play 정보로 테이블 업데이트
            updated_body = body
            for play in plays:
                updated_body = self._update_play_row_in_table(updated_body, play)
                results["synced"] += 1

            # 3. 페이지 업데이트
            if updated_body != body:
                await self.confluence.update_page(
                    page_id=self.play_db_page_id,
                    body_md=updated_body,
                )

            self.logger.info("Full Confluence sync completed", total=results["total"])
            return results

        except Exception as e:
            self.logger.error("Full Confluence sync failed", error=str(e))
            results["errors"].append(str(e))
            return results

    def _update_play_row_in_table(self, body: str, play: PlayRecord) -> str:
        """
        HTML 테이블에서 Play 행 업데이트

        Args:
            body: 페이지 HTML 내용
            play: PlayRecord 객체

        Returns:
            str: 업데이트된 HTML
        """
        # RAG 이모지 매핑
        rag_emoji = {
            "G": "🟢",
            "Y": "🟡",
            "R": "🔴",
        }

        # Play ID 패턴 찾기 (테이블 행)
        # 예: | EXT_Desk_D01_세미나파이프라인 | ... |
        pattern = rf"(\|\s*{re.escape(play.play_id)}\s*\|)"

        def update_row(match):
            # 기존 행을 새 데이터로 교체
            row = f"""| {play.play_id} | {play.activity_qtd}/{play.activity_goal if hasattr(play, "activity_goal") else 0} | {play.signal_qtd}/{play.signal_goal if hasattr(play, "signal_goal") else 0} | {play.brief_qtd}/{play.brief_goal if hasattr(play, "brief_goal") else 0} | {rag_emoji.get(play.status if isinstance(play.status, str) else play.status.value, "⚪")} | {play.next_action or ""} |"""
            return row

        # 패턴이 있으면 교체, 없으면 원본 반환
        if re.search(pattern, body):
            # 전체 행 교체 (간단한 패턴 매칭)
            lines = body.split("\n")
            updated_lines = []
            for line in lines:
                if play.play_id in line and "|" in line:
                    # 테이블 행으로 추정
                    rag = rag_emoji.get(
                        play.status
                        if isinstance(play.status, str)
                        else play.status.value
                        if hasattr(play.status, "value")
                        else "G",
                        "⚪",
                    )
                    activity_goal = getattr(play, "activity_goal", 0) or 0
                    signal_goal = getattr(play, "signal_goal", 0) or 0
                    brief_goal = getattr(play, "brief_goal", 0) or 0

                    updated_line = f"| {play.play_id} | {play.activity_qtd}/{activity_goal} | {play.signal_qtd}/{signal_goal} | {play.brief_qtd}/{brief_goal} | {rag} | {play.next_action or ''} |"
                    updated_lines.append(updated_line)
                else:
                    updated_lines.append(line)
            return "\n".join(updated_lines)

        return body

    def generate_play_table_html(self, plays: list[PlayRecord]) -> str:
        """
        Play 목록으로 HTML 테이블 생성

        Args:
            plays: PlayRecord 목록

        Returns:
            str: HTML 테이블
        """
        rag_emoji = {"G": "🟢", "Y": "🟡", "R": "🔴"}

        rows = []
        for play in plays:
            rag = rag_emoji.get(
                play.status
                if isinstance(play.status, str)
                else play.status.value
                if hasattr(play.status, "value")
                else "G",
                "⚪",
            )
            activity_goal = getattr(play, "activity_goal", 0) or 0
            signal_goal = getattr(play, "signal_goal", 0) or 0
            brief_goal = getattr(play, "brief_goal", 0) or 0

            row = f"""<tr>
                <td>{play.play_id}</td>
                <td>{play.play_name}</td>
                <td>{play.activity_qtd}/{activity_goal}</td>
                <td>{play.signal_qtd}/{signal_goal}</td>
                <td>{play.brief_qtd}/{brief_goal}</td>
                <td>{rag}</td>
                <td>{play.next_action or ""}</td>
            </tr>"""
            rows.append(row)

        table = f"""<table>
            <thead>
                <tr>
                    <th>Play ID</th>
                    <th>Play Name</th>
                    <th>Act/Goal</th>
                    <th>Sig/Goal</th>
                    <th>Brf/Goal</th>
                    <th>RAG</th>
                    <th>Next Action</th>
                </tr>
            </thead>
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>"""

        return table


# 싱글톤 인스턴스
play_sync_service = PlaySyncService()
