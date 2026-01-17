"""
ToDo 동기화 서비스

project-todo.md (원장) ↔ Confluence 동기화
"""

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from backend.services.todo_parser import TodoItem, TodoList, TodoParser, todo_parser

logger = structlog.get_logger()


@dataclass
class SyncDiff:
    """동기화 차이점"""

    only_in_system: list[TodoItem] = field(default_factory=list)
    only_in_confluence: list[TodoItem] = field(default_factory=list)
    status_diff: list[tuple[TodoItem, TodoItem]] = field(default_factory=list)  # (system, confluence)
    content_diff: list[tuple[TodoItem, TodoItem]] = field(default_factory=list)  # (system, confluence)

    @property
    def has_diff(self) -> bool:
        """차이점이 있는지 확인"""
        return bool(
            self.only_in_system
            or self.only_in_confluence
            or self.status_diff
            or self.content_diff
        )

    @property
    def summary(self) -> dict[str, int]:
        """차이점 요약"""
        return {
            "only_in_system": len(self.only_in_system),
            "only_in_confluence": len(self.only_in_confluence),
            "status_diff": len(self.status_diff),
            "content_diff": len(self.content_diff),
            "total_diff": (
                len(self.only_in_system)
                + len(self.only_in_confluence)
                + len(self.status_diff)
                + len(self.content_diff)
            ),
        }


@dataclass
class ProgressReport:
    """진행현황 리포트"""

    total_items: int = 0
    completed: int = 0
    in_progress: int = 0
    pending: int = 0
    completion_rate: float = 0.0
    phase_stats: dict[str, dict[str, Any]] = field(default_factory=dict)
    stale_items: list[TodoItem] = field(default_factory=list)  # 장기 미완료 항목
    recommendations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "total_items": self.total_items,
            "completed": self.completed,
            "in_progress": self.in_progress,
            "pending": self.pending,
            "completion_rate": round(self.completion_rate, 2),
            "phase_stats": self.phase_stats,
            "stale_items": [
                {"id": item.id, "content": item.content, "phase": item.phase}
                for item in self.stale_items
            ],
            "recommendations": self.recommendations,
        }

    def to_markdown(self) -> str:
        """Markdown 형식으로 변환"""
        lines = [
            "# 📊 ToDo 진행현황 리포트",
            "",
            f"**생성일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## 📈 전체 현황",
            "",
            "| 항목 | 건수 | 비율 |",
            "|------|------|------|",
            f"| ✅ 완료 | {self.completed} | {self._rate(self.completed)}% |",
            f"| 🚧 진행중 | {self.in_progress} | {self._rate(self.in_progress)}% |",
            f"| 📋 대기 | {self.pending} | {self._rate(self.pending)}% |",
            f"| **합계** | **{self.total_items}** | **100%** |",
            "",
            f"**완료율**: {round(self.completion_rate, 1)}%",
            "",
            "---",
            "",
            "## 📁 Phase별 현황",
            "",
            "| Phase | 완료 | 진행중 | 대기 | 완료율 |",
            "|-------|------|--------|------|--------|",
        ]

        for phase, stats in self.phase_stats.items():
            rate = stats.get("completion_rate", 0)
            lines.append(
                f"| {phase} | {stats.get('completed', 0)} | "
                f"{stats.get('in_progress', 0)} | {stats.get('pending', 0)} | "
                f"{round(rate, 1)}% |"
            )

        lines.extend(["", "---", ""])

        if self.stale_items:
            lines.extend([
                "## ⚠️ 장기 미완료 항목",
                "",
            ])
            for item in self.stale_items[:10]:  # 최대 10개
                lines.append(f"- [{item.phase}] {item.content}")
            lines.extend(["", "---", ""])

        if self.recommendations:
            lines.extend([
                "## 💡 권장 사항",
                "",
            ])
            for rec in self.recommendations:
                lines.append(f"- {rec}")

        return "\n".join(lines)

    def _rate(self, count: int) -> float:
        """비율 계산"""
        if self.total_items == 0:
            return 0.0
        return round(count / self.total_items * 100, 1)


class TodoSyncService:
    """
    ToDo 동기화 서비스

    project-todo.md (원장) ↔ Confluence 동기화
    """

    def __init__(self, parser: TodoParser | None = None):
        self.parser = parser or todo_parser
        self.logger = logger.bind(service="todo_sync")

        # Confluence 연동 (lazy import)
        self._confluence = None

        # 환경 변수
        self.todo_page_id = os.getenv("CONFLUENCE_TODO_PAGE_ID", "")
        self.default_todo_path = "project-todo.md"

    @property
    def confluence(self):
        """Confluence 클라이언트 (lazy loading)"""
        if self._confluence is None:
            try:
                from backend.integrations.mcp_confluence.server import ConfluenceMCP
                self._confluence = ConfluenceMCP()
            except ImportError:
                self.logger.warning("ConfluenceMCP를 가져올 수 없습니다")
                self._confluence = None
        return self._confluence

    async def load_system_todo(self, path: str | None = None) -> TodoList:
        """
        시스템 ToDo 파일 로드

        Args:
            path: project-todo.md 경로 (기본: project-todo.md)

        Returns:
            파싱된 TodoList
        """
        file_path = Path(path or self.default_todo_path)

        if not file_path.exists():
            self.logger.warning("ToDo 파일을 찾을 수 없습니다", path=str(file_path))
            return TodoList()

        content = file_path.read_text(encoding="utf-8")
        todo_list = self.parser.parse_markdown(content)

        self.logger.info(
            "시스템 ToDo 로드 완료",
            path=str(file_path),
            items=len(todo_list.items),
            version=todo_list.version,
        )

        return todo_list

    async def load_confluence_todo(self, page_id: str | None = None) -> TodoList:
        """
        Confluence ToDo 페이지 로드

        Args:
            page_id: Confluence 페이지 ID

        Returns:
            파싱된 TodoList
        """
        target_page_id = page_id or self.todo_page_id

        if not target_page_id:
            self.logger.warning("CONFLUENCE_TODO_PAGE_ID가 설정되지 않았습니다")
            return TodoList()

        if not self.confluence:
            self.logger.warning("Confluence 클라이언트를 초기화할 수 없습니다")
            return TodoList()

        try:
            page = await self.confluence.get_page(target_page_id)
            html_content = page.get("body", "")
            todo_list = self.parser.parse_confluence_html(html_content)

            self.logger.info(
                "Confluence ToDo 로드 완료",
                page_id=target_page_id,
                items=len(todo_list.items),
            )

            return todo_list

        except Exception as e:
            self.logger.error("Confluence ToDo 로드 실패", error=str(e))
            return TodoList()

    async def compare(self, system: TodoList, confluence: TodoList) -> SyncDiff:
        """
        시스템과 Confluence ToDo 비교

        Args:
            system: 시스템 TodoList (원장)
            confluence: Confluence TodoList

        Returns:
            SyncDiff 차이점
        """
        diff = SyncDiff()

        # ID 기반 매핑
        system_map = {item.id: item for item in system.items}
        confluence_map = {item.id: item for item in confluence.items}

        # 시스템에만 있는 항목
        for item_id, item in system_map.items():
            if item_id not in confluence_map:
                diff.only_in_system.append(item)

        # Confluence에만 있는 항목
        for item_id, item in confluence_map.items():
            if item_id not in system_map:
                diff.only_in_confluence.append(item)

        # 양쪽에 있는 항목 비교
        for item_id in system_map.keys() & confluence_map.keys():
            sys_item = system_map[item_id]
            conf_item = confluence_map[item_id]

            # 상태 차이
            if sys_item.status != conf_item.status:
                diff.status_diff.append((sys_item, conf_item))

            # 내용 차이 (정규화 후 비교)
            sys_content = self._normalize_content(sys_item.content)
            conf_content = self._normalize_content(conf_item.content)
            if sys_content != conf_content:
                diff.content_diff.append((sys_item, conf_item))

        self.logger.info("ToDo 비교 완료", diff_summary=diff.summary)

        return diff

    def _normalize_content(self, content: str) -> str:
        """내용 정규화 (비교용)"""
        import re
        # 버전, 이모지, 공백 정규화
        normalized = re.sub(r"v\d+\.\d+\.\d+", "", content)
        normalized = re.sub(r"✅|🚧|📋|🎯", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip().lower()

    async def generate_progress_report(self, todo: TodoList) -> ProgressReport:
        """
        진행현황 리포트 생성

        Args:
            todo: TodoList

        Returns:
            ProgressReport
        """
        report = ProgressReport()

        # 전체 통계
        report.total_items = len(todo.items)
        report.completed = sum(1 for item in todo.items if item.status == "completed")
        report.in_progress = sum(1 for item in todo.items if item.status == "in_progress")
        report.pending = sum(1 for item in todo.items if item.status == "pending")

        if report.total_items > 0:
            report.completion_rate = (report.completed / report.total_items) * 100

        # Phase별 통계
        for phase, items in todo.phases.items():
            phase_completed = sum(1 for item in items if item.status == "completed")
            phase_in_progress = sum(1 for item in items if item.status == "in_progress")
            phase_pending = sum(1 for item in items if item.status == "pending")
            phase_total = len(items)

            report.phase_stats[phase] = {
                "total": phase_total,
                "completed": phase_completed,
                "in_progress": phase_in_progress,
                "pending": phase_pending,
                "completion_rate": (phase_completed / phase_total * 100) if phase_total > 0 else 0,
            }

        # 장기 미완료 항목 (pending 상태인 Phase 1~2 항목)
        for phase, items in todo.phases.items():
            if "Phase 1" in phase or "Phase 2" in phase:
                for item in items:
                    if item.status == "pending":
                        report.stale_items.append(item)

        # 권장 사항 생성
        report.recommendations = self._generate_recommendations(report, todo)

        self.logger.info("진행현황 리포트 생성 완료", completion_rate=report.completion_rate)

        return report

    def _generate_recommendations(self, report: ProgressReport, todo: TodoList) -> list[str]:
        """권장 사항 생성"""
        recommendations = []

        # 완료율 기반 권장
        if report.completion_rate < 50:
            recommendations.append(
                f"전체 완료율이 {round(report.completion_rate, 1)}%입니다. "
                "우선순위가 높은 Phase부터 집중적으로 처리하세요."
            )

        # 진행중 항목이 너무 많은 경우
        if report.in_progress > 5:
            recommendations.append(
                f"진행 중인 항목이 {report.in_progress}개입니다. "
                "WIP(Work In Progress) 제한을 고려하세요."
            )

        # 장기 미완료 항목
        if report.stale_items:
            recommendations.append(
                f"Phase 1~2에 미완료 항목이 {len(report.stale_items)}개 있습니다. "
                "우선 처리하거나 스코프 조정을 검토하세요."
            )

        # Phase별 불균형
        phase_rates = [
            stats["completion_rate"]
            for stats in report.phase_stats.values()
        ]
        if phase_rates and max(phase_rates) - min(phase_rates) > 50:
            recommendations.append(
                "Phase별 완료율 편차가 큽니다. 리소스 재분배를 고려하세요."
            )

        # 성공적인 경우
        if report.completion_rate >= 80:
            recommendations.append(
                "🎉 훌륭합니다! 완료율 80% 이상 달성했습니다."
            )

        return recommendations

    async def sync_to_confluence(
        self,
        todo: TodoList,
        dry_run: bool = False,
        page_id: str | None = None,
    ) -> dict[str, Any]:
        """
        시스템 ToDo를 Confluence에 동기화

        Args:
            todo: 시스템 TodoList (원장)
            dry_run: True면 실제 업데이트 없이 미리보기만
            page_id: Confluence 페이지 ID

        Returns:
            동기화 결과
        """
        target_page_id = page_id or self.todo_page_id

        if not target_page_id:
            return {
                "status": "skipped",
                "reason": "CONFLUENCE_TODO_PAGE_ID not configured",
            }

        # HTML 변환
        html_content = self.parser.to_confluence_html(todo)

        if dry_run:
            return {
                "status": "dry_run",
                "page_id": target_page_id,
                "preview": html_content[:500] + "..." if len(html_content) > 500 else html_content,
                "content_length": len(html_content),
            }

        if not self.confluence:
            return {
                "status": "error",
                "reason": "Confluence client not available",
            }

        try:
            # 페이지 업데이트
            await self.confluence.update_page(
                page_id=target_page_id,
                body_md=html_content,
            )

            self.logger.info(
                "Confluence 동기화 완료",
                page_id=target_page_id,
                items=len(todo.items),
            )

            return {
                "status": "success",
                "page_id": target_page_id,
                "synced_items": len(todo.items),
            }

        except Exception as e:
            self.logger.error("Confluence 동기화 실패", error=str(e))
            return {
                "status": "error",
                "reason": str(e),
            }

    async def suggest_updates(
        self,
        todo: TodoList,
        codebase_context: str | None = None,
    ) -> list[str]:
        """
        코드베이스 컨텍스트 기반 ToDo 업데이트 제안

        Args:
            todo: TodoList
            codebase_context: 코드베이스 변경 컨텍스트 (git diff 등)

        Returns:
            업데이트 제안 목록
        """
        suggestions = []

        # 기본 제안: 상태 업데이트 필요 항목
        for item in todo.items:
            if item.status == "pending" and item.phase in ["Phase 1", "Phase 2"]:
                suggestions.append(
                    f"[{item.id}] '{item.content[:30]}...' - "
                    "이전 Phase 항목이 아직 미완료입니다. 상태를 확인하세요."
                )

        # 코드베이스 컨텍스트 기반 제안
        if codebase_context:
            # 키워드 매칭으로 관련 ToDo 찾기
            for item in todo.items:
                if item.status == "pending":
                    # 항목 내용의 키워드가 코드 변경에 있으면 완료 제안
                    keywords = self._extract_keywords(item.content)
                    for keyword in keywords:
                        if keyword.lower() in codebase_context.lower():
                            suggestions.append(
                                f"[{item.id}] '{item.content[:30]}...' - "
                                f"관련 코드가 변경되었습니다. 완료 상태로 업데이트하세요."
                            )
                            break

        self.logger.info("업데이트 제안 생성 완료", count=len(suggestions))

        return suggestions

    def _extract_keywords(self, content: str) -> list[str]:
        """내용에서 키워드 추출"""
        import re
        # 영문 단어와 한글 단어 추출
        words = re.findall(r"[a-zA-Z]+|[가-힣]+", content)
        # 3글자 이상만
        return [w for w in words if len(w) >= 3]


# 싱글톤 인스턴스
todo_sync_service = TodoSyncService()
