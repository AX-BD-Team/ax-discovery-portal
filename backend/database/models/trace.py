"""
Trace 모델 (P0)

실패 분류 체계를 Trace에 자동으로 남기기
요청/응답마다 trace_id를 만들고 아래를 자동으로 분류/태깅:
- RELATION_EXTRACTION_ERROR
- ENTITY_TYPE_AMBIGUITY
- RECENCY_STALE_SOURCE
- MISSING_SOURCE_COVERAGE
- PATH_TOO_LONG_OR_NO_PATH
- DUPLICATE_SIGNAL_SUSPECTED

이게 쌓이면, "튜닝"이 아니라 설계 변경 포인트가 데이터로 보임
"""

import enum
from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Enum, Float, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class TraceErrorType(enum.Enum):
    """실패 분류 체계"""

    # 관계 추출 오류
    RELATION_EXTRACTION_ERROR = "RELATION_EXTRACTION_ERROR"

    # 엔티티 타입 혼동
    ENTITY_TYPE_AMBIGUITY = "ENTITY_TYPE_AMBIGUITY"

    # 최신성 문제
    RECENCY_STALE_SOURCE = "RECENCY_STALE_SOURCE"

    # 커버리지 부족
    MISSING_SOURCE_COVERAGE = "MISSING_SOURCE_COVERAGE"

    # 경로 탐색 실패
    PATH_TOO_LONG_OR_NO_PATH = "PATH_TOO_LONG_OR_NO_PATH"

    # 중복 의심
    DUPLICATE_SIGNAL_SUSPECTED = "DUPLICATE_SIGNAL_SUSPECTED"

    # 검증 실패
    VALIDATION_FAILED = "VALIDATION_FAILED"

    # 신뢰도 낮음
    LOW_CONFIDENCE_RESULT = "LOW_CONFIDENCE_RESULT"

    # LLM 추출 실패
    LLM_EXTRACTION_FAILED = "LLM_EXTRACTION_FAILED"

    # 타임아웃
    TIMEOUT = "TIMEOUT"

    # 기타
    OTHER = "OTHER"


class TraceStatus(enum.Enum):
    """Trace 상태"""

    RUNNING = "running"
    SUCCESS = "success"
    PARTIAL = "partial"  # 일부 성공
    FAILED = "failed"


class Trace(Base):
    """
    Trace 테이블

    요청/응답 추적 및 실패 분류
    XAI와 연동하여 문제 원인 분석
    """

    __tablename__ = "traces"

    # Primary Key
    trace_id: Mapped[str] = mapped_column(String(100), primary_key=True)

    # 세션/워크플로 연결
    session_id: Mapped[str | None] = mapped_column(String(100))
    workflow_id: Mapped[str | None] = mapped_column(String(50))
    run_id: Mapped[str | None] = mapped_column(String(100))

    # 작업 정보
    operation: Mapped[str] = mapped_column(String(100), nullable=False)
    # 예: "signal_extraction", "scorecard_evaluation", "path_finding", "entity_linking"

    # 입력/출력
    input_data: Mapped[dict | None] = mapped_column(JSON)
    output_data: Mapped[dict | None] = mapped_column(JSON)

    # 상태
    status: Mapped[TraceStatus] = mapped_column(
        Enum(TraceStatus), default=TraceStatus.RUNNING, nullable=False
    )

    # 실패 분류 (복수 가능)
    error_types: Mapped[list | None] = mapped_column(JSON, default=list)
    # 예: ["RECENCY_STALE_SOURCE", "LOW_CONFIDENCE_RESULT"]

    # 상세 오류 메시지
    error_message: Mapped[str | None] = mapped_column(Text)

    # 관련 엔티티 ID들
    entity_ids: Mapped[list | None] = mapped_column(JSON, default=list)
    triple_ids: Mapped[list | None] = mapped_column(JSON, default=list)

    # 성능 지표
    duration_ms: Mapped[int | None] = mapped_column()
    confidence: Mapped[float | None] = mapped_column(Float)

    # 모델/추출기 정보 (디버깅용)
    model_version: Mapped[str | None] = mapped_column(String(100))
    prompt_version: Mapped[str | None] = mapped_column(String(100))
    extractor_run_id: Mapped[str | None] = mapped_column(String(100))

    # 추가 메타데이터
    extra_metadata: Mapped[dict | None] = mapped_column(JSON, default=dict)

    # 타임스탬프
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 생성자
    created_by: Mapped[str | None] = mapped_column(String(100))

    # Indexes
    __table_args__ = (
        Index("idx_trace_session_id", "session_id"),
        Index("idx_trace_workflow_id", "workflow_id"),
        Index("idx_trace_operation", "operation"),
        Index("idx_trace_status", "status"),
        Index("idx_trace_started_at", "started_at"),
        # 에러 분석용 인덱스 (GIN for JSON array would be better in PostgreSQL)
    )

    def __repr__(self) -> str:
        return f"<Trace(trace_id='{self.trace_id}', operation='{self.operation}', status='{self.status.value}')>"

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "session_id": self.session_id,
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "operation": self.operation,
            "status": self.status.value,
            "error_types": self.error_types,
            "error_message": self.error_message,
            "entity_ids": self.entity_ids,
            "triple_ids": self.triple_ids,
            "duration_ms": self.duration_ms,
            "confidence": self.confidence,
            "model_version": self.model_version,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
        }

    def add_error(self, error_type: TraceErrorType, message: str | None = None):
        """에러 추가"""
        if self.error_types is None:
            self.error_types = []
        if error_type.value not in self.error_types:
            self.error_types.append(error_type.value)
        if message:
            if self.error_message:
                self.error_message += f"\n{message}"
            else:
                self.error_message = message

    def finish(self, status: TraceStatus, output_data: dict | None = None):
        """Trace 완료"""
        self.status = status
        self.finished_at = datetime.now(UTC)
        if self.started_at:
            delta = self.finished_at - self.started_at
            self.duration_ms = int(delta.total_seconds() * 1000)
        if output_data:
            self.output_data = output_data


class CompetencyQuestion(Base):
    """
    Competency Questions 테이블 (P0)

    BD용 질문 20~50개를 고정하고 regression 테스트로 돌림
    온톨로지/파이프라인 변경 시 품질 하락을 즉시 감지

    예시:
    - "최근 30일 내, 특정 산업에서 나온 Signal 중 Scorecard 상위 10개와 근거는?"
    - "A 고객 관련 Signal에서 경쟁사가 언급된 Evidence 경로는?"
    - "Topic X가 포함된 Brief 중 Pilot로 간 것들의 공통 Technology/Play 패턴은?"
    """

    __tablename__ = "competency_questions"

    # Primary Key
    question_id: Mapped[str] = mapped_column(String(50), primary_key=True)

    # 질문 내용
    question: Mapped[str] = mapped_column(Text, nullable=False)

    # 질문 카테고리
    category: Mapped[str] = mapped_column(String(100))
    # 예: "recency", "evidence_chain", "pattern_discovery", "duplicate_detection"

    # 예상 쿼리 유형
    expected_query_type: Mapped[str] = mapped_column(String(50))
    # 예: "rdb", "graph", "vector", "hybrid"

    # 테스트 파라미터
    parameters: Mapped[dict | None] = mapped_column(JSON, default=dict)
    # 예: {"industry": "금융", "days": 30, "top_k": 10}

    # 정답 기준 (golden set)
    expected_result_pattern: Mapped[dict | None] = mapped_column(JSON)
    # 예: {"min_results": 5, "required_fields": ["signal_id", "evidence"]}

    # 최소 품질 기준
    min_precision: Mapped[float | None] = mapped_column(Float, default=0.8)
    min_recall: Mapped[float | None] = mapped_column(Float, default=0.7)

    # 활성화 여부
    is_active: Mapped[bool] = mapped_column(default=True)

    # 마지막 테스트 결과
    last_test_result: Mapped[dict | None] = mapped_column(JSON)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    # Indexes
    __table_args__ = (
        Index("idx_cq_category", "category"),
        Index("idx_cq_is_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<CompetencyQuestion(question_id='{self.question_id}', category='{self.category}')>"


# 기본 Competency Questions (BD 도메인용)
DEFAULT_COMPETENCY_QUESTIONS = [
    {
        "question_id": "cq-001",
        "question": "최근 30일 내, 금융 산업에서 나온 Signal 중 Scorecard 상위 10개와 근거는?",
        "category": "recency",
        "expected_query_type": "hybrid",
        "parameters": {"industry": "금융", "days": 30, "top_k": 10},
    },
    {
        "question_id": "cq-002",
        "question": "A 고객 관련 Signal에서 경쟁사(역할 기준)가 언급된 Evidence 경로는?",
        "category": "evidence_chain",
        "expected_query_type": "graph",
        "parameters": {"customer_name": "A"},
    },
    {
        "question_id": "cq-003",
        "question": "Topic 'AI 자동화'가 포함된 Brief 중 Pilot로 간 것들의 공통 Technology/Play 패턴은?",
        "category": "pattern_discovery",
        "expected_query_type": "graph",
        "parameters": {"topic": "AI 자동화", "status": "PILOT_READY"},
    },
    {
        "question_id": "cq-004",
        "question": "새로 입력된 Signal과 가장 유사한 기존 Signal 5개는?",
        "category": "duplicate_detection",
        "expected_query_type": "vector",
        "parameters": {"top_k": 5},
    },
    {
        "question_id": "cq-005",
        "question": "Source 동기화가 7일 이상 안 된 stale 데이터 목록은?",
        "category": "data_quality",
        "expected_query_type": "rdb",
        "parameters": {"stale_days": 7},
    },
    {
        "question_id": "cq-006",
        "question": "Signal에서 Brief까지의 평균 리드타임은? (Play별 분석)",
        "category": "kpi",
        "expected_query_type": "rdb",
        "parameters": {"group_by": "play_id"},
    },
    {
        "question_id": "cq-007",
        "question": "proposed 상태로 검증 대기 중인 Triple 중 confidence 0.5 이하는?",
        "category": "data_quality",
        "expected_query_type": "rdb",
        "parameters": {"status": "proposed", "max_confidence": 0.5},
    },
    {
        "question_id": "cq-008",
        "question": "특정 Organization이 customer와 competitor 역할을 모두 가진 경우는?",
        "category": "entity_ambiguity",
        "expected_query_type": "graph",
        "parameters": {},
    },
    {
        "question_id": "cq-009",
        "question": "Evidence 없이 생성된 inferred Triple 목록은?",
        "category": "data_quality",
        "expected_query_type": "rdb",
        "parameters": {"assertion_type": "inferred", "has_evidence": False},
    },
    {
        "question_id": "cq-010",
        "question": "가장 많이 참조되는 Source 상위 5개는?",
        "category": "coverage",
        "expected_query_type": "rdb",
        "parameters": {"top_k": 5},
    },
]
