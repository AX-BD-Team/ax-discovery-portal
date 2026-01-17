"""
ToDo List 파서

project-todo.md 및 Confluence HTML 파싱
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

import structlog

logger = structlog.get_logger()


@dataclass
class TodoItem:
    """ToDo 항목"""

    id: str  # "Phase3-5" 형식
    content: str  # 작업 내용
    status: Literal["completed", "in_progress", "pending"]
    phase: str  # "Phase 1" ~ "Phase 4"
    version: str | None = None  # "v0.5.0"
    sub_items: list["TodoItem"] = field(default_factory=list)
    line_number: int = 0


@dataclass
class TodoList:
    """ToDo 리스트"""

    items: list[TodoItem] = field(default_factory=list)
    version: str = ""
    last_updated: str = ""
    phases: dict[str, list[TodoItem]] = field(default_factory=dict)


class TodoParser:
    """
    ToDo 파서

    Markdown 및 Confluence HTML 파싱 지원
    """

    # 체크박스 패턴
    CHECKBOX_COMPLETED = re.compile(r"^\s*-\s*\[x\]\s*(.+)$", re.IGNORECASE)
    CHECKBOX_PENDING = re.compile(r"^\s*-\s*\[\s*\]\s*(.+)$")

    # Phase 헤더 패턴
    PHASE_HEADER = re.compile(
        r"^##\s*(?:✅|🚧|📋|🎯)?\s*(Phase\s*\d+(?:\.\d+)?)[:\s]*(.*)$", re.IGNORECASE
    )

    # 버전 패턴
    VERSION_PATTERN = re.compile(r"v(\d+\.\d+\.\d+)")

    # 메타데이터 패턴
    VERSION_META = re.compile(r"\*\*현재 버전\*\*:\s*(\d+\.\d+\.\d+)")
    UPDATED_META = re.compile(r"\*\*마지막 업데이트\*\*:\s*(\d{4}-\d{2}-\d{2})")

    # 진행 중 키워드
    IN_PROGRESS_KEYWORDS = ["진행 중", "진행중", "🚧", "작업 중"]

    def __init__(self):
        self.logger = logger.bind(service="todo_parser")

    def parse_markdown(self, content: str) -> TodoList:
        """
        Markdown 형식의 ToDo 파일 파싱

        Args:
            content: Markdown 텍스트

        Returns:
            파싱된 TodoList
        """
        lines = content.split("\n")
        todo_list = TodoList()
        current_phase = ""
        current_phase_items: list[TodoItem] = []
        item_counter = 0

        # 메타데이터 추출
        for line in lines[:20]:  # 상단 20줄 내에서 메타데이터 검색
            version_match = self.VERSION_META.search(line)
            if version_match:
                todo_list.version = version_match.group(1)

            updated_match = self.UPDATED_META.search(line)
            if updated_match:
                todo_list.last_updated = updated_match.group(1)

        for line_num, line in enumerate(lines, 1):
            # Phase 헤더 감지
            phase_match = self.PHASE_HEADER.match(line)
            if phase_match:
                # 이전 Phase 저장
                if current_phase and current_phase_items:
                    todo_list.phases[current_phase] = current_phase_items.copy()
                    todo_list.items.extend(current_phase_items)

                current_phase = phase_match.group(1).strip()
                current_phase_items = []
                item_counter = 0
                continue

            # 완료된 항목
            completed_match = self.CHECKBOX_COMPLETED.match(line)
            if completed_match and current_phase:
                item_counter += 1
                item = self._create_item(
                    content=completed_match.group(1).strip(),
                    status="completed",
                    phase=current_phase,
                    item_counter=item_counter,
                    line_number=line_num,
                )
                current_phase_items.append(item)
                continue

            # 미완료 항목
            pending_match = self.CHECKBOX_PENDING.match(line)
            if pending_match and current_phase:
                item_counter += 1
                content_text = pending_match.group(1).strip()

                # 진행 중 키워드 체크
                status: Literal["completed", "in_progress", "pending"] = "pending"
                for keyword in self.IN_PROGRESS_KEYWORDS:
                    if keyword in content_text or keyword in current_phase:
                        status = "in_progress"
                        break

                # 현재 Phase가 "진행 중"인지 확인
                if "🚧" in line or any(
                    kw in lines[line_num - 5 : line_num] for kw in ["진행 중", "🚧"]
                ):
                    status = "in_progress"

                item = self._create_item(
                    content=content_text,
                    status=status,
                    phase=current_phase,
                    item_counter=item_counter,
                    line_number=line_num,
                )
                current_phase_items.append(item)

        # 마지막 Phase 저장
        if current_phase and current_phase_items:
            todo_list.phases[current_phase] = current_phase_items.copy()
            todo_list.items.extend(current_phase_items)

        self.logger.info(
            "Markdown 파싱 완료",
            total_items=len(todo_list.items),
            phases=len(todo_list.phases),
            version=todo_list.version,
        )

        return todo_list

    def _create_item(
        self,
        content: str,
        status: Literal["completed", "in_progress", "pending"],
        phase: str,
        item_counter: int,
        line_number: int,
    ) -> TodoItem:
        """ToDo 항목 생성"""
        # Phase 번호 추출
        phase_num_match = re.search(r"Phase\s*(\d+(?:\.\d+)?)", phase, re.IGNORECASE)
        phase_num = phase_num_match.group(1) if phase_num_match else "0"

        # ID 생성
        item_id = f"Phase{phase_num}-{item_counter}"

        # 버전 추출
        version_match = self.VERSION_PATTERN.search(content)
        version = f"v{version_match.group(1)}" if version_match else None

        # 내용 정리 (버전, 이모지, 체크 표시 제거)
        clean_content = content
        if version_match:
            clean_content = clean_content.replace(version_match.group(0), "").strip()
        clean_content = re.sub(r"✅|🚧|📋|🎯", "", clean_content).strip()

        return TodoItem(
            id=item_id,
            content=clean_content,
            status=status,
            phase=phase,
            version=version,
            line_number=line_number,
        )

    def parse_confluence_html(self, html: str) -> TodoList:
        """
        Confluence HTML 형식의 ToDo 파싱

        Args:
            html: Confluence Storage Format HTML

        Returns:
            파싱된 TodoList
        """
        todo_list = TodoList()
        current_phase = ""
        item_counter = 0

        # 간단한 HTML 파싱 (정규식 기반)
        # 실제 환경에서는 BeautifulSoup 등 사용 권장

        # Phase 헤더 추출 (h2 태그)
        phase_pattern = re.compile(
            r"<h2[^>]*>(?:✅|🚧|📋|🎯)?\s*(Phase\s*\d+(?:\.\d+)?)[:\s]*([^<]*)</h2>",
            re.IGNORECASE,
        )

        # 체크박스 추출
        # Confluence 체크박스: <ac:task-status ac:status="complete"/>
        task_complete_pattern = re.compile(
            r'<ac:task[^>]*>.*?<ac:task-status[^>]*status="complete"[^>]*/>.*?<ac:task-body>(.*?)</ac:task-body>.*?</ac:task>',
            re.DOTALL,
        )
        task_incomplete_pattern = re.compile(
            r'<ac:task[^>]*>.*?<ac:task-status[^>]*status="incomplete"[^>]*/>.*?<ac:task-body>(.*?)</ac:task-body>.*?</ac:task>',
            re.DOTALL,
        )

        # 간단한 리스트 항목 패턴 (li 태그)
        list_item_pattern = re.compile(r"<li[^>]*>(.*?)</li>", re.DOTALL)

        # Phase 섹션 분리
        sections = re.split(r"(<h2[^>]*>.*?</h2>)", html)

        for i, section in enumerate(sections):
            # Phase 헤더 확인
            phase_match = phase_pattern.search(section)
            if phase_match:
                current_phase = phase_match.group(1).strip()
                item_counter = 0
                continue

            if not current_phase:
                continue

            # 완료된 작업
            for match in task_complete_pattern.finditer(section):
                item_counter += 1
                content = self._strip_html(match.group(1))
                item = self._create_item(
                    content=content,
                    status="completed",
                    phase=current_phase,
                    item_counter=item_counter,
                    line_number=0,
                )
                todo_list.items.append(item)
                if current_phase not in todo_list.phases:
                    todo_list.phases[current_phase] = []
                todo_list.phases[current_phase].append(item)

            # 미완료 작업
            for match in task_incomplete_pattern.finditer(section):
                item_counter += 1
                content = self._strip_html(match.group(1))
                item = self._create_item(
                    content=content,
                    status="pending",
                    phase=current_phase,
                    item_counter=item_counter,
                    line_number=0,
                )
                todo_list.items.append(item)
                if current_phase not in todo_list.phases:
                    todo_list.phases[current_phase] = []
                todo_list.phases[current_phase].append(item)

        self.logger.info(
            "Confluence HTML 파싱 완료",
            total_items=len(todo_list.items),
            phases=len(todo_list.phases),
        )

        return todo_list

    def _strip_html(self, html: str) -> str:
        """HTML 태그 제거"""
        text = re.sub(r"<[^>]+>", "", html)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def to_markdown(self, todo: TodoList) -> str:
        """
        TodoList를 Markdown으로 변환

        Args:
            todo: TodoList 객체

        Returns:
            Markdown 텍스트
        """
        lines = [
            "# AX Discovery Portal - Project TODO",
            "",
            "> 프로젝트 진행 상황 및 다음 단계",
            "",
            f"**현재 버전**: {todo.version}",
            f"**마지막 업데이트**: {todo.last_updated or datetime.now().strftime('%Y-%m-%d')}",
            "",
            "---",
            "",
        ]

        # Phase별로 항목 출력
        for phase, items in todo.phases.items():
            # Phase 상태 결정
            completed_count = sum(1 for item in items if item.status == "completed")
            total_count = len(items)

            if completed_count == total_count:
                status_emoji = "✅"
                status_text = "완료"
            elif completed_count > 0:
                status_emoji = "🚧"
                status_text = "진행 중"
            else:
                status_emoji = "📋"
                status_text = "예정"

            lines.append(f"## {status_emoji} {phase}: {status_text}")
            lines.append("")

            for item in items:
                checkbox = "[x]" if item.status == "completed" else "[ ]"
                version_str = f" {item.version}" if item.version else ""
                status_str = " ✅" if item.status == "completed" else ""
                lines.append(f"- {checkbox} {item.content}{version_str}{status_str}")

            lines.append("")
            lines.append("---")
            lines.append("")

        return "\n".join(lines)

    def to_confluence_html(self, todo: TodoList) -> str:
        """
        TodoList를 Confluence Storage Format HTML로 변환

        Args:
            todo: TodoList 객체

        Returns:
            Confluence Storage Format HTML
        """
        html_parts = [
            '<ac:structured-macro ac:name="info">',
            "<ac:rich-text-body>",
            f"<p><strong>현재 버전</strong>: {todo.version}</p>",
            f"<p><strong>마지막 업데이트</strong>: {todo.last_updated or datetime.now().strftime('%Y-%m-%d')}</p>",
            "</ac:rich-text-body>",
            "</ac:structured-macro>",
            "",
        ]

        for phase, items in todo.phases.items():
            # Phase 상태 결정
            completed_count = sum(1 for item in items if item.status == "completed")
            total_count = len(items)

            if completed_count == total_count:
                status_emoji = "✅"
            elif completed_count > 0:
                status_emoji = "🚧"
            else:
                status_emoji = "📋"

            html_parts.append(f"<h2>{status_emoji} {phase}</h2>")
            html_parts.append("<ac:task-list>")

            for item in items:
                status = "complete" if item.status == "completed" else "incomplete"
                version_str = f" <em>{item.version}</em>" if item.version else ""

                html_parts.append("<ac:task>")
                html_parts.append(f'<ac:task-status ac:status="{status}"/>')
                html_parts.append(f"<ac:task-body>{item.content}{version_str}</ac:task-body>")
                html_parts.append("</ac:task>")

            html_parts.append("</ac:task-list>")
            html_parts.append("")

        return "\n".join(html_parts)


# 싱글톤 인스턴스
todo_parser = TodoParser()
