"""
Activities Router

Activity 조회 및 관리 API
외부 세미나 수집 결과 조회
수집기 헬스체크
채팅 기반 세미나 추가
파일 업로드 일괄 등록
"""

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db

logger = structlog.get_logger()

router = APIRouter()


# ============================================================
# Response Models
# ============================================================


class ActivityResponse(BaseModel):
    """Activity 응답"""

    entity_id: str
    entity_type: str
    name: str
    description: str | None = None

    # Properties에서 추출
    url: str | None = None
    date: str | None = None
    organizer: str | None = None
    play_id: str | None = None
    source: str | None = None
    channel: str | None = None
    source_type: str | None = None
    categories: list[str] | None = None
    status: str | None = None

    # 타임스탬프
    created_at: str | None = None
    updated_at: str | None = None

    @classmethod
    def from_entity(cls, entity) -> "ActivityResponse":
        """Entity에서 변환"""
        props = entity.properties or {}
        return cls(
            entity_id=entity.entity_id,
            entity_type=entity.entity_type.value,
            name=entity.name,
            description=entity.description,
            url=props.get("url"),
            date=props.get("date"),
            organizer=props.get("organizer"),
            play_id=props.get("play_id"),
            source=props.get("source"),
            channel=props.get("channel"),
            source_type=props.get("source_type"),
            categories=props.get("categories", []),
            status=props.get("status"),
            created_at=entity.created_at.isoformat() if entity.created_at else None,
            updated_at=entity.updated_at.isoformat() if entity.updated_at else None,
        )


class ActivityListResponse(BaseModel):
    """Activity 목록 응답"""

    items: list[ActivityResponse]
    total: int
    page: int
    page_size: int


class ActivityStatsResponse(BaseModel):
    """Activity 통계 응답"""

    total: int
    by_source_type: dict[str, int]
    today_count: int


# ============================================================
# Activity 조회 API
# ============================================================


@router.get("", response_model=ActivityListResponse)
async def list_activities(
    play_id: str | None = Query(None, description="Play ID 필터"),
    source_type: str | None = Query(None, description="소스 타입 필터 (rss, festa, eventbrite)"),
    status: str | None = Query(None, description="상태 필터"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지 크기"),
    db: AsyncSession = Depends(get_db),
):
    """
    Activity 목록 조회

    수집된 외부 세미나/이벤트 Activity 목록

    Args:
        play_id: Play ID 필터
        source_type: 소스 타입 필터 (rss, festa, eventbrite)
        status: 상태 필터
        page: 페이지 번호
        page_size: 페이지 크기

    Returns:
        ActivityListResponse: Activity 목록 + 페이지네이션 정보
    """
    from sqlalchemy import func, select

    from backend.database.models.entity import Entity, EntityType

    # 기본 쿼리 조건
    base_conditions = [Entity.entity_type == EntityType.ACTIVITY]

    # JSON 필터 조건 추가 (PostgreSQL JSONB 연산자 사용)
    # SQLite 호환성을 위해 DB 종류에 따라 분기
    if play_id:
        # PostgreSQL: properties->>'play_id', SQLite: json_extract(properties, '$.play_id')
        base_conditions.append(Entity.properties["play_id"].astext == play_id)
    if source_type:
        base_conditions.append(Entity.properties["source_type"].astext == source_type)
    if status:
        base_conditions.append(Entity.properties["status"].astext == status)

    # 총 개수 조회 (별도 쿼리로 분리하여 최적화)
    count_query = select(func.count()).select_from(Entity).where(*base_conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 페이지네이션 적용된 데이터 조회
    skip = (page - 1) * page_size
    query = (
        select(Entity)
        .where(*base_conditions)
        .order_by(Entity.created_at.desc())
        .offset(skip)
        .limit(page_size)
    )
    result = await db.execute(query)
    items = list(result.scalars().all())

    return ActivityListResponse(
        items=[ActivityResponse.from_entity(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/stats", response_model=ActivityStatsResponse)
async def get_activity_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    Activity 통계 조회

    Returns:
        ActivityStatsResponse: 전체 개수, 소스별 개수, 오늘 수집 개수
    """
    from datetime import UTC, datetime

    from sqlalchemy import func, select

    from backend.database.models.entity import Entity, EntityType

    # 모든 통계를 단일 쿼리로 조회 (성능 최적화)
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)

    # 소스 타입별 개수를 DB에서 직접 집계 (PostgreSQL JSONB)
    source_types = [
        "rss",
        "festa",
        "eventbrite",
        "manual",
        "onoffmix",
        "eventus",
        "devevent",
        "chat",
        "upload",
    ]

    # 총 개수 + 오늘 수집 개수를 단일 쿼리로
    stats_query = select(
        func.count().label("total"),
        func.count().filter(Entity.created_at >= today_start).label("today_count"),
    ).where(Entity.entity_type == EntityType.ACTIVITY)

    stats_result = await db.execute(stats_query)
    stats_row = stats_result.one()
    total = stats_row.total or 0
    today_count = stats_row.today_count or 0

    # 소스 타입별 개수 집계 (DB 레벨)
    source_count_query = (
        select(
            Entity.properties["source_type"].astext.label("source_type"),
            func.count().label("count"),
        )
        .where(Entity.entity_type == EntityType.ACTIVITY)
        .group_by(Entity.properties["source_type"].astext)
    )
    source_result = await db.execute(source_count_query)
    source_rows = source_result.all()

    # 결과를 딕셔너리로 변환
    by_source_type = dict.fromkeys(source_types, 0)
    for row in source_rows:
        source_type = row.source_type or "manual"
        if source_type in by_source_type:
            by_source_type[source_type] = row.count
        else:
            # 알 수 없는 소스 타입은 manual로 집계
            by_source_type["manual"] = by_source_type.get("manual", 0) + row.count

    return ActivityStatsResponse(
        total=total,
        by_source_type=by_source_type,
        today_count=today_count,
    )


# ============================================================
# 수집기 헬스체크 API (/{activity_id} 보다 먼저 정의해야 함)
# ============================================================


class CollectorHealthResponse(BaseModel):
    """수집기 헬스체크 응답"""

    collector_name: str
    status: str  # healthy, degraded, unhealthy
    checked_at: str
    sample_count: int
    error_message: str | None = None
    response_time_ms: float | None = None


class HealthCheckResponse(BaseModel):
    """헬스체크 전체 응답"""

    checked_at: str
    results: list[CollectorHealthResponse]
    summary: dict


@router.get("/health-check", response_model=HealthCheckResponse)
async def get_collector_health():
    """
    수집기 헬스체크 결과 반환

    OnOffMix, EventUs 등 웹 스크래핑 기반 수집기의 상태를 확인합니다.
    HTML 구조 변경 시 조기 감지를 위한 진단 엔드포인트입니다.

    Returns:
        HealthCheckResponse: 수집기별 헬스체크 결과
    """
    from backend.integrations.external_sources import run_health_check

    result = await run_health_check()
    return result


@router.get("/{activity_id}", response_model=ActivityResponse)
async def get_activity(
    activity_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Activity 상세 조회

    Args:
        activity_id: Activity ID

    Returns:
        ActivityResponse: Activity 상세 정보
    """
    from sqlalchemy import and_, select

    from backend.database.models.entity import Entity, EntityType

    result = await db.execute(
        select(Entity).where(
            and_(
                Entity.entity_id == activity_id,
                Entity.entity_type == EntityType.ACTIVITY,
            )
        )
    )
    entity = result.scalar_one_or_none()

    if not entity:
        raise HTTPException(status_code=404, detail="Activity not found")

    return ActivityResponse.from_entity(entity)


@router.get("/by-url/{url:path}")
async def get_activity_by_url(
    url: str,
    db: AsyncSession = Depends(get_db),
):
    """
    URL로 Activity 조회

    중복 체크에 유용

    Args:
        url: 세미나/이벤트 URL

    Returns:
        Activity 정보 (없으면 404)
    """
    from sqlalchemy import select

    from backend.database.models.entity import Entity, EntityType

    # DB 레벨에서 URL로 직접 필터링 (JSONB 인덱스 활용)
    result = await db.execute(
        select(Entity)
        .where(
            Entity.entity_type == EntityType.ACTIVITY,
            Entity.properties["url"].astext == url,
        )
        .limit(1)
    )
    entity = result.scalar_one_or_none()

    if not entity:
        raise HTTPException(status_code=404, detail="Activity not found for this URL")

    return ActivityResponse.from_entity(entity)


@router.post("/check-duplicate")
async def check_duplicate(
    url: str | None = None,
    title: str | None = None,
    date: str | None = None,
    external_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """
    중복 Activity 체크

    Args:
        url: 이벤트 URL
        title: 이벤트 제목
        date: 이벤트 날짜
        external_id: 외부 시스템 ID

    Returns:
        중복 여부 및 기존 Activity 정보
    """
    from sqlalchemy import select

    from backend.database.models.entity import Entity, EntityType

    if not any([url, title, external_id]):
        raise HTTPException(
            status_code=400,
            detail="url, title, 또는 external_id 중 하나는 필수입니다",
        )

    existing = None

    # 1. external_id로 체크 (가장 우선순위 높음)
    if external_id and not existing:
        result = await db.execute(
            select(Entity)
            .where(
                Entity.entity_type == EntityType.ACTIVITY,
                Entity.external_ref_id == external_id,
            )
            .limit(1)
        )
        existing = result.scalar_one_or_none()

    # 2. URL로 체크 (DB 레벨 JSONB 쿼리)
    if url and not existing:
        result = await db.execute(
            select(Entity)
            .where(
                Entity.entity_type == EntityType.ACTIVITY,
                Entity.properties["url"].astext == url,
            )
            .limit(1)
        )
        existing = result.scalar_one_or_none()

    # 3. 제목 + 날짜로 체크 (DB 레벨 쿼리)
    if title and date and not existing:
        result = await db.execute(
            select(Entity)
            .where(
                Entity.entity_type == EntityType.ACTIVITY,
                Entity.name == title,
                Entity.properties["date"].astext == date,
            )
            .limit(1)
        )
        existing = result.scalar_one_or_none()

    if existing:
        return {
            "is_duplicate": True,
            "existing_activity": ActivityResponse.from_entity(existing),
        }
    else:
        return {
            "is_duplicate": False,
            "existing_activity": None,
        }


# ============================================================
# 채팅 기반 세미나 추가 API
# ============================================================


class ChatMessage(BaseModel):
    """채팅 메시지"""

    role: str  # user, assistant
    content: str
    timestamp: str | None = None


class SeminarExtractResult(BaseModel):
    """세미나 정보 추출 결과"""

    title: str
    description: str | None = None
    date: str | None = None
    organizer: str | None = None
    url: str | None = None
    categories: list[str] = []
    confidence: float = 0.0


class ChatResponse(BaseModel):
    """채팅 응답"""

    message: str
    extracted_seminars: list[SeminarExtractResult] = []
    requires_confirmation: bool = False


@router.post("/chat")
async def chat_add_seminar(
    message: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """
    채팅으로 세미나 추가 (SSE 스트리밍)

    텍스트 메시지 또는 파일에서 세미나 정보를 추출하고
    사용자 확인 후 Activity로 등록합니다.

    Args:
        message: 사용자 메시지 (URL, 세미나 정보 등)
        files: 첨부 파일 (이미지, PDF, 텍스트 등)

    Returns:
        SSE 스트리밍 응답
    """
    import asyncio
    import json
    from datetime import UTC, datetime

    async def generate_response():
        """SSE 이벤트 생성"""
        try:
            # 1. 시작 이벤트
            yield f"data: {json.dumps({'type': 'start', 'message': '메시지 분석 중...'})}\n\n"
            await asyncio.sleep(0.1)

            # 2. 파일 처리 (있는 경우)
            extracted_from_files: list[dict] = []
            if files:
                from backend.integrations.file_processor import FileProcessor

                processor = FileProcessor()
                for file in files:
                    yield f"data: {json.dumps({'type': 'progress', 'message': f'파일 처리 중: {file.filename}'})}\n\n"

                    content = await file.read()
                    filename = file.filename or "unknown"
                    content_type = file.content_type or ""

                    try:
                        seminars = await processor.process_file(content, filename, content_type)
                        for s in seminars:
                            extracted_from_files.append(s.to_dict())
                    except Exception as e:
                        logger.warning(f"파일 처리 실패: {filename}", error=str(e))

            # 3. 텍스트 메시지 처리
            yield f"data: {json.dumps({'type': 'progress', 'message': '메시지 분석 중...'})}\n\n"

            from backend.integrations.file_processor import FileProcessor

            processor = FileProcessor()
            extracted_from_text = await processor.process_text(message)
            extracted_text_dicts = [s.to_dict() for s in extracted_from_text]

            # 4. 결과 병합
            all_extracted = extracted_from_files + extracted_text_dicts

            if not all_extracted:
                # URL이 감지되었지만 추출 실패 시
                import re

                urls = re.findall(r"https?://[^\s]+", message)
                if urls:
                    yield f"data: {json.dumps({'type': 'info', 'message': f'{len(urls)}개의 URL을 감지했지만 세미나 정보를 추출하지 못했습니다. URL을 직접 확인해주세요.'})}\n\n"
                else:
                    yield f"data: {json.dumps({'type': 'info', 'message': '세미나 정보를 찾지 못했습니다. 세미나 제목, 날짜, 주최자 정보를 포함해주세요.'})}\n\n"

            # 5. 추출 결과 반환
            yield f"data: {json.dumps({'type': 'extracted', 'seminars': all_extracted, 'count': len(all_extracted)})}\n\n"

            # 6. 완료
            yield f"data: {json.dumps({'type': 'complete', 'message': f'{len(all_extracted)}개의 세미나 정보를 추출했습니다.', 'timestamp': datetime.now(UTC).isoformat()})}\n\n"

        except Exception as e:
            logger.error("채팅 처리 오류", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'message': f'처리 중 오류가 발생했습니다: {str(e)}'})}\n\n"

    return StreamingResponse(
        generate_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


class ConfirmSeminarRequest(BaseModel):
    """세미나 확인 요청"""

    seminars: list[dict]
    play_id: str = "EXT_Desk_D01_Seminar"


@router.post("/chat/confirm")
async def confirm_seminar(
    request: ConfirmSeminarRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    추출된 세미나 정보 확인 후 Activity로 등록

    Args:
        request: 등록할 세미나 정보 목록과 Play ID

    Returns:
        등록된 Activity 목록
    """
    seminars = request.seminars
    play_id = request.play_id
    from datetime import UTC, datetime
    from uuid import uuid4

    from backend.database.models.entity import Entity, EntityType

    registered = []

    for seminar_data in seminars:
        try:
            # Entity 생성
            entity = Entity(
                entity_id=f"ACT-{uuid4().hex[:12]}",
                entity_type=EntityType.ACTIVITY,
                name=seminar_data.get("title", "제목 없음"),
                description=seminar_data.get("description"),
                properties={
                    "url": seminar_data.get("url"),
                    "date": seminar_data.get("date"),
                    "organizer": seminar_data.get("organizer"),
                    "play_id": play_id,
                    "source": "chat",
                    "channel": "manual",
                    "source_type": "chat",
                    "categories": seminar_data.get("categories", []),
                    "status": "pending",
                },
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )

            db.add(entity)
            await db.flush()

            registered.append(ActivityResponse.from_entity(entity))

        except Exception as e:
            logger.error("세미나 등록 실패", seminar=seminar_data, error=str(e))

    await db.commit()

    return {
        "registered": registered,
        "count": len(registered),
        "play_id": play_id,
    }


# ============================================================
# 파일 업로드 일괄 등록 API
# ============================================================


class UploadResult(BaseModel):
    """업로드 결과"""

    filename: str
    extracted_count: int
    seminars: list[SeminarExtractResult]
    error: str | None = None


class UploadResponse(BaseModel):
    """업로드 응답"""

    total_files: int
    total_extracted: int
    results: list[UploadResult]


@router.post("/upload", response_model=UploadResponse)
async def upload_seminars(
    files: list[UploadFile] = File(...),
    play_id: str = Form(default="EXT_Desk_D01_Seminar"),
    auto_register: bool = Form(default=False),
    db: AsyncSession = Depends(get_db),
):
    """
    파일에서 세미나 일괄 추출 및 등록

    지원 파일 형식:
    - 이미지: jpg, png, webp (OCR)
    - PDF: pdf
    - 문서: docx, xlsx
    - 텍스트: txt, csv, json, md

    Args:
        files: 업로드할 파일 목록
        play_id: 연결할 Play ID
        auto_register: True이면 자동 등록, False이면 추출만

    Returns:
        UploadResponse: 파일별 추출 결과
    """
    from backend.integrations.file_processor import FileProcessor

    processor = FileProcessor()
    results: list[UploadResult] = []
    total_extracted = 0

    for file in files:
        try:
            content = await file.read()
            filename = file.filename or "unknown"
            content_type = file.content_type or ""

            # 세미나 정보 추출
            seminars = await processor.process_file(content, filename, content_type)
            extracted_count = len(seminars)
            total_extracted += extracted_count

            results.append(
                UploadResult(
                    filename=filename,
                    extracted_count=extracted_count,
                    seminars=[
                        SeminarExtractResult(
                            title=s.title,
                            description=s.description,
                            date=s.date,
                            organizer=s.organizer,
                            url=s.url,
                            categories=s.categories or [],
                            confidence=s.confidence if hasattr(s, "confidence") else 0.8,
                        )
                        for s in seminars
                    ],
                )
            )

            # 자동 등록 옵션이 켜진 경우
            if auto_register and seminars:
                from datetime import UTC, datetime
                from uuid import uuid4

                from backend.database.models.entity import Entity, EntityType

                for seminar in seminars:
                    entity = Entity(
                        entity_id=f"ACT-{uuid4().hex[:12]}",
                        entity_type=EntityType.ACTIVITY,
                        name=seminar.title,
                        description=seminar.description,
                        properties={
                            "url": seminar.url,
                            "date": seminar.date,
                            "organizer": seminar.organizer,
                            "play_id": play_id,
                            "source": "upload",
                            "channel": "manual",
                            "source_type": "upload",
                            "categories": seminar.categories or [],
                            "status": "pending",
                        },
                        created_at=datetime.now(UTC),
                        updated_at=datetime.now(UTC),
                    )
                    db.add(entity)

                await db.commit()

        except Exception as e:
            logger.error("파일 처리 실패", filename=file.filename, error=str(e))
            results.append(
                UploadResult(
                    filename=file.filename or "unknown",
                    extracted_count=0,
                    seminars=[],
                    error=str(e),
                )
            )

    return UploadResponse(
        total_files=len(files),
        total_extracted=total_extracted,
        results=results,
    )
