"""
Task Converter 서비스

Play의 next_action을 Task 목록으로 변환
"""

import re
from dataclasses import dataclass
from datetime import date
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.play_record import PlayRecord
from backend.database.models.task import TaskPriority
from backend.database.repositories.task import task_repo


@dataclass
class TaskTemplate:
    """Task 생성용 템플릿"""

    title: str
    description: str | None = None
    priority: str = TaskPriority.P1.value
    order_index: int = 0
    source_text: str | None = None


class TaskConverter:
    """Play → Task 변환 서비스"""

    # next_action 분리자 패턴: → / / , 등
    SEPARATOR_PATTERN = re.compile(r"\s*[→/,]\s*")

    # 숫자 추출 패턴 (예: "10개", "키워드20", "후보10")
    NUMBER_PATTERN = re.compile(r"(\d+)")

    def parse_next_action(self, next_action: str) -> list[str]:
        """
        next_action 문자열을 개별 액션으로 분리

        예: "10+키워드20 세팅 → 이번주 후보10 수집"
        → ["10+키워드20 세팅", "이번주 후보10 수집"]

        Args:
            next_action: Play의 next_action 문자열

        Returns:
            list[str]: 분리된 액션 목록
        """
        if not next_action:
            return []

        # → 기준 분리 (주 분리자)
        parts = self.SEPARATOR_PATTERN.split(next_action)

        # 빈 문자열 제거 및 정리
        actions = [part.strip() for part in parts if part.strip()]

        return actions

    def extract_priority(self, play: PlayRecord) -> str:
        """
        Play의 priority 또는 RAG 상태에서 Task 우선순위 결정

        Args:
            play: PlayRecord 객체

        Returns:
            str: Task 우선순위 (P0/P1/P2)
        """
        # Play의 priority 필드가 있으면 그대로 사용
        if play.priority:
            return play.priority

        # RAG 상태 기반
        if play.status == "R":
            return TaskPriority.P0.value
        elif play.status == "Y":
            return TaskPriority.P1.value
        else:
            return TaskPriority.P2.value

    def convert_play_to_task_templates(self, play: PlayRecord) -> list[TaskTemplate]:
        """
        Play의 next_action을 TaskTemplate 목록으로 변환

        Args:
            play: PlayRecord 객체

        Returns:
            list[TaskTemplate]: 생성할 Task 템플릿 목록
        """
        templates = []

        # 1. next_action 파싱
        actions = self.parse_next_action(play.next_action or "")

        priority = self.extract_priority(play)

        for idx, action in enumerate(actions):
            template = TaskTemplate(
                title=action,
                description=f"Play: {play.play_name}",
                priority=priority,
                order_index=idx,
                source_text=play.next_action,
            )
            templates.append(template)

        return templates

    def generate_goal_task_templates(self, play: PlayRecord) -> list[TaskTemplate]:
        """
        미충족 목표를 Task로 변환

        예: signal_qtd < signal_goal → "Signal 24건 달성 (현재 0건)"

        Args:
            play: PlayRecord 객체

        Returns:
            list[TaskTemplate]: 목표 달성용 Task 템플릿
        """
        templates = []
        priority = self.extract_priority(play)

        # Signal 목표 미달성
        if hasattr(play, "signal_goal") and play.signal_goal > 0:
            if play.signal_qtd < play.signal_goal:
                remaining = play.signal_goal - play.signal_qtd
                templates.append(
                    TaskTemplate(
                        title=f"Signal {remaining}건 추가 수집",
                        description=f"목표: {play.signal_goal}건, 현재: {play.signal_qtd}건",
                        priority=priority,
                        order_index=100,
                    )
                )

        # Brief 목표 미달성
        if hasattr(play, "brief_goal") and play.brief_goal > 0:
            if play.brief_qtd < play.brief_goal:
                remaining = play.brief_goal - play.brief_qtd
                templates.append(
                    TaskTemplate(
                        title=f"Brief {remaining}건 생성",
                        description=f"목표: {play.brief_goal}건, 현재: {play.brief_qtd}건",
                        priority=priority,
                        order_index=101,
                    )
                )

        # S2 목표 미달성
        if hasattr(play, "s2_goal") and play.s2_goal > 0:
            if play.s2_qtd < play.s2_goal:
                remaining = play.s2_goal - play.s2_qtd
                templates.append(
                    TaskTemplate(
                        title=f"S2 {remaining}건 진입",
                        description=f"목표: {play.s2_goal}건, 현재: {play.s2_qtd}건",
                        priority=priority,
                        order_index=102,
                    )
                )

        return templates

    async def create_tasks_for_play(
        self,
        db: AsyncSession,
        play: PlayRecord,
        include_goal_tasks: bool = False,
        due_date: date | None = None,
    ) -> list:
        """
        Play에서 Task 자동 생성

        Args:
            db: 데이터베이스 세션
            play: PlayRecord 객체
            include_goal_tasks: 목표 달성 Task 포함 여부
            due_date: 기한 (없으면 Play의 due_date 사용)

        Returns:
            list[Task]: 생성된 Task 목록
        """
        # 기존 Task 삭제 (재생성 시)
        await task_repo.delete_by_play_id(db, play.play_id)

        tasks = []

        # 1. next_action → Task
        templates = self.convert_play_to_task_templates(play)

        # 2. 목표 달성 Task (선택)
        if include_goal_tasks:
            templates.extend(self.generate_goal_task_templates(play))

        # 3. Task 생성
        # SQLAlchemy Date → Python date 변환 (mypy 타입 호환성)
        play_due_raw = play.due_date if hasattr(play, "due_date") else None
        play_due = cast(date | None, play_due_raw)  # SQLAlchemy Date는 런타임에 Python date
        task_due: date | None = due_date or play_due
        assignee = play.owner.split("(")[0].replace("Owner:", "").strip() if play.owner else None

        for template in templates:
            task_id = await task_repo.get_next_task_id(db)
            task = await task_repo.create_task(
                db=db,
                task_id=task_id,
                play_id=play.play_id,
                title=template.title,
                description=template.description,
                priority=template.priority,
                assignee=assignee,
                due_date=task_due,
                order_index=template.order_index,
                source_text=template.source_text,
            )
            tasks.append(task)

        return tasks


# 싱글톤 인스턴스
task_converter = TaskConverter()
