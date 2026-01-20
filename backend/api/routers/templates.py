"""
Template 다운로드 API 라우터

Boilerplate 템플릿을 Zip 파일로 다운로드하는 기능 제공
"""

import io
import re
import zipfile
from pathlib import Path

import structlog
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = structlog.get_logger()

router = APIRouter()

# Boilerplate 디렉토리 경로
BOILERPLATE_DIR = Path(__file__).parent.parent.parent.parent / "boilerplate"

# Zip에서 제외할 파일/디렉토리 패턴
EXCLUDE_PATTERNS = [
    "__pycache__",
    ".git",
    ".venv",
    "venv",
    "node_modules",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "*.pyc",
    "*.pyo",
    ".DS_Store",
    "Thumbs.db",
]


class TemplateConfig(BaseModel):
    """템플릿 구성 옵션"""

    project_name: str = Field(
        default="my-agent-project",
        description="프로젝트 이름 (PascalCase 또는 kebab-case)",
        examples=["my-agent-project", "AwesomeAgent"],
    )
    project_description: str = Field(
        default="Claude Agent SDK 기반 멀티에이전트 프로젝트",
        description="프로젝트 설명",
    )
    author_name: str = Field(
        default="Your Team",
        description="저자/팀 이름",
    )
    org: str = Field(
        default="your-org",
        description="GitHub 조직명",
    )
    cli_name: str | None = Field(
        default=None,
        description="CLI 명령어 이름 (기본값: project_name의 kebab-case)",
    )


class TemplateInfo(BaseModel):
    """템플릿 정보"""

    name: str
    description: str
    version: str
    files_count: int
    placeholders: list[str]


def should_exclude(path: Path) -> bool:
    """파일/디렉토리 제외 여부 판단"""
    name = path.name

    for pattern in EXCLUDE_PATTERNS:
        if pattern.startswith("*"):
            # 확장자 패턴
            if name.endswith(pattern[1:]):
                return True
        elif name == pattern:
            return True

    return False


def to_kebab_case(name: str) -> str:
    """문자열을 kebab-case로 변환"""
    # PascalCase/camelCase → kebab-case
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1-\2", name)
    s2 = re.sub("([a-z0-9])([A-Z])", r"\1-\2", s1)
    # 공백, 언더스코어 → 하이픈
    s3 = re.sub(r"[\s_]+", "-", s2)
    return s3.lower()


def replace_placeholders(content: str, config: TemplateConfig) -> str:
    """플레이스홀더를 실제 값으로 치환"""
    cli_name = config.cli_name or to_kebab_case(config.project_name)
    project_kebab = to_kebab_case(config.project_name)

    # 대문자 및 소문자 케밥 형식 모두 지원
    replacements = {
        # 대문자 형식
        "{{PROJECT_NAME}}": config.project_name,
        "{{PROJECT_DESCRIPTION}}": config.project_description,
        # 소문자 케밥 형식
        "{{project-name}}": project_kebab,
        "{{project-description}}": config.project_description,
        "{{project-cli}}": cli_name,
        "{{author-name}}": config.author_name,
        "{{org}}": config.org,
    }

    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)

    return content


def create_zip_buffer(config: TemplateConfig | None = None) -> io.BytesIO:
    """Boilerplate 디렉토리를 Zip 파일로 압축"""
    buffer = io.BytesIO()

    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in BOILERPLATE_DIR.rglob("*"):
            # 제외 대상 체크
            if any(should_exclude(p) for p in file_path.parents) or should_exclude(file_path):
                continue

            # 디렉토리는 건너뜀 (파일만 추가)
            if file_path.is_dir():
                continue

            # 상대 경로 계산
            relative_path = file_path.relative_to(BOILERPLATE_DIR)

            # 파일 내용 읽기
            try:
                content = file_path.read_text(encoding="utf-8")

                # 플레이스홀더 치환 (config가 있는 경우)
                if config:
                    content = replace_placeholders(content, config)

                # Zip에 추가
                zf.writestr(str(relative_path), content)
            except UnicodeDecodeError:
                # 바이너리 파일은 그대로 추가
                zf.writestr(str(relative_path), file_path.read_bytes())

    buffer.seek(0)
    return buffer


def count_files() -> int:
    """템플릿 파일 수 계산"""
    count = 0
    for file_path in BOILERPLATE_DIR.rglob("*"):
        if file_path.is_file() and not any(
            should_exclude(p) for p in file_path.parents
        ) and not should_exclude(file_path):
            count += 1
    return count


@router.get("/info", response_model=TemplateInfo)
async def get_template_info() -> TemplateInfo:
    """
    템플릿 정보 조회

    Boilerplate 템플릿의 메타 정보와 사용 가능한 플레이스홀더 목록을 반환합니다.
    """
    return TemplateInfo(
        name="Claude Agent SDK Boilerplate",
        description="Claude Agent SDK 기반 멀티에이전트 프로젝트 템플릿",
        version="1.0.0",
        files_count=count_files(),
        placeholders=[
            "{{PROJECT_NAME}}",
            "{{PROJECT_DESCRIPTION}}",
            "{{project-name}}",
            "{{project-description}}",
            "{{project-cli}}",
            "{{author-name}}",
            "{{org}}",
        ],
    )


@router.get("/download")
async def download_template(
    project_name: str | None = Query(
        default=None,
        description="프로젝트 이름 (플레이스홀더 치환용)",
        examples=["my-agent-project"],
    ),
    project_description: str | None = Query(
        default=None,
        description="프로젝트 설명",
    ),
    author_name: str | None = Query(
        default=None,
        description="저자/팀 이름",
    ),
    org: str | None = Query(
        default=None,
        description="GitHub 조직명",
    ),
    cli_name: str | None = Query(
        default=None,
        description="CLI 명령어 이름",
    ),
) -> StreamingResponse:
    """
    Boilerplate 템플릿 Zip 다운로드

    프로젝트 정보를 제공하면 플레이스홀더가 치환된 템플릿을 다운로드합니다.
    파라미터 없이 호출하면 원본 템플릿을 다운로드합니다.

    ## 플레이스홀더

    | 플레이스홀더 | 설명 | 예시 |
    |-------------|------|------|
    | `{{PROJECT_NAME}}` | 프로젝트 이름 | `my-agent-project` |
    | `{{PROJECT_DESCRIPTION}}` | 프로젝트 설명 | 프로젝트 개요 |
    | `{{project-name}}` | 패키지명 (kebab-case) | `my-agent-project` |
    | `{{project-cli}}` | CLI 명령어 | `my-project` |
    | `{{author-name}}` | 저자/팀 이름 | `Your Team` |
    | `{{org}}` | GitHub 조직 | `your-org` |
    """
    config = None

    # 파라미터가 하나라도 있으면 config 생성
    if any([project_name, project_description, author_name, org, cli_name]):
        config = TemplateConfig(
            project_name=project_name or "my-agent-project",
            project_description=project_description or "Claude Agent SDK 기반 멀티에이전트 프로젝트",
            author_name=author_name or "Your Team",
            org=org or "your-org",
            cli_name=cli_name,
        )

    logger.info(
        "Downloading template",
        config=config.model_dump() if config else None,
    )

    # Zip 생성
    zip_buffer = create_zip_buffer(config)

    # 파일명 결정
    filename = f"{config.project_name}.zip" if config else "claude-agent-boilerplate.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


@router.post("/download")
async def download_template_post(config: TemplateConfig) -> StreamingResponse:
    """
    Boilerplate 템플릿 Zip 다운로드 (POST)

    POST 요청으로 상세한 템플릿 구성을 전달하여 커스터마이징된 템플릿을 다운로드합니다.
    """
    logger.info(
        "Downloading template (POST)",
        config=config.model_dump(),
    )

    # Zip 생성
    zip_buffer = create_zip_buffer(config)

    # 파일명 결정
    filename = f"{config.project_name}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )
