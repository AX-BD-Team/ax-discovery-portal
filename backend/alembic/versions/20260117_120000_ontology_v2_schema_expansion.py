"""Ontology v2 schema expansion (22 EntityTypes, 28 PredicateTypes)

BD 특화 온톨로지 v2 스키마 확장:
- EntityType: 13종 → 22종 (+9)
  신규: Activity, Validation, Pilot, Person, Team,
        MarketSegment, Trend, Decision, Meeting, Task, Milestone
- PredicateType: 17종 → 28종 (+11)
  신규: GENERATES, EVALUATES_TO, SUMMARIZED_IN, VALIDATED_BY, PILOTS_AS,
        PROGRESSES_TO, ADDRESSES, EMPLOYS, PARTNERS_WITH, SUBSIDIARY_OF,
        OWNS, DECIDES, ATTENDED, REPORTS_TO, CONTRADICTS, SCHEDULED_FOR, ACHIEVES

Revision ID: 4c8e9f0a1b2d
Revises: 2a0199fcd881
Create Date: 2026-01-17 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4c8e9f0a1b2d"
down_revision: str = "2a0199fcd881"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # PostgreSQL ENUM 타입 확장
    # EntityType에 새 값 추가

    # Activity, Validation, Pilot (Pipeline)
    op.execute("ALTER TYPE entitytype ADD VALUE IF NOT EXISTS 'Activity'")
    op.execute("ALTER TYPE entitytype ADD VALUE IF NOT EXISTS 'Validation'")
    op.execute("ALTER TYPE entitytype ADD VALUE IF NOT EXISTS 'Pilot'")

    # Person, Team (Organization)
    op.execute("ALTER TYPE entitytype ADD VALUE IF NOT EXISTS 'Person'")
    op.execute("ALTER TYPE entitytype ADD VALUE IF NOT EXISTS 'Team'")

    # MarketSegment, Trend (Market Context)
    op.execute("ALTER TYPE entitytype ADD VALUE IF NOT EXISTS 'MarketSegment'")
    op.execute("ALTER TYPE entitytype ADD VALUE IF NOT EXISTS 'Trend'")

    # Decision (Evidence & Reasoning)
    op.execute("ALTER TYPE entitytype ADD VALUE IF NOT EXISTS 'Decision'")

    # Meeting, Task, Milestone (Operational)
    op.execute("ALTER TYPE entitytype ADD VALUE IF NOT EXISTS 'Meeting'")
    op.execute("ALTER TYPE entitytype ADD VALUE IF NOT EXISTS 'Task'")
    op.execute("ALTER TYPE entitytype ADD VALUE IF NOT EXISTS 'Milestone'")

    # PredicateType에 새 값 추가

    # Pipeline Flow Relations
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'generates'")
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'evaluates_to'")
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'summarized_in'")
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'validated_by'")
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'pilots_as'")
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'progresses_to'")

    # Topic Relations
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'addresses'")

    # Organization Relations
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'employs'")
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'partners_with'")
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'subsidiary_of'")

    # Person Relations
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'owns'")
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'decides'")
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'attended'")
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'reports_to'")

    # Evidence Relations
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'contradicts'")

    # Operational Relations
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'scheduled_for'")
    op.execute("ALTER TYPE predicatetype ADD VALUE IF NOT EXISTS 'achieves'")


def downgrade() -> None:
    # PostgreSQL에서는 ENUM 값을 쉽게 제거할 수 없음
    # 새 ENUM 타입 생성 후 컬럼 변환 필요
    # 실제 다운그레이드가 필요한 경우 별도 마이그레이션 작성 권장

    # 주의: 이 다운그레이드는 데이터 손실을 유발할 수 있음
    # 새 타입의 엔티티/트리플이 있으면 먼저 삭제 필요

    pass  # ENUM 값 제거는 복잡하므로 생략
