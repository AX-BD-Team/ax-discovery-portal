"""
YAML 로더

Task/Suite YAML 파일 로딩 및 검증
"""

from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from backend.evals.models.suite import SuiteDefinition
from backend.evals.models.task import TaskDefinition

# ============================================================================
# 기본 경로 설정
# ============================================================================

# 프로젝트 루트 기준 evals 디렉토리
DEFAULT_EVALS_DIR = Path(__file__).parent.parent.parent.parent / "evals"
TASKS_DIR = DEFAULT_EVALS_DIR / "tasks"
SUITES_DIR = DEFAULT_EVALS_DIR / "suites"


# ============================================================================
# YAML 로딩
# ============================================================================


def _load_yaml(path: str | Path) -> dict[str, Any]:
    """YAML 파일 로드"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"YAML 파일을 찾을 수 없습니다: {path}")

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict):
        raise ValueError(f"YAML 파일이 딕셔너리 형식이 아닙니다: {path}")

    return data


def _resolve_path(path: str | Path, base_dir: Path | None = None) -> Path:
    """경로 해석 (상대 경로 → 절대 경로)"""
    path = Path(path)

    if path.is_absolute():
        return path

    # 기본 디렉토리 기준으로 해석
    if base_dir:
        resolved = base_dir / path
        if resolved.exists():
            return resolved

    # evals 디렉토리 기준으로 해석
    resolved = DEFAULT_EVALS_DIR / path
    if resolved.exists():
        return resolved

    # 프로젝트 루트 기준으로 해석
    project_root = DEFAULT_EVALS_DIR.parent
    resolved = project_root / path
    if resolved.exists():
        return resolved

    # 그래도 없으면 원본 반환 (에러는 호출자가 처리)
    return path


# ============================================================================
# Task 로딩
# ============================================================================


def load_task(path: str | Path, base_dir: Path | None = None) -> TaskDefinition:
    """
    Task YAML 파일 로드 및 검증

    Args:
        path: Task YAML 파일 경로
        base_dir: 상대 경로 해석 기준 디렉토리

    Returns:
        TaskDefinition: 검증된 Task 정의

    Raises:
        FileNotFoundError: 파일이 없는 경우
        ValidationError: 스키마 검증 실패
    """
    resolved_path = _resolve_path(path, base_dir)
    data = _load_yaml(resolved_path)

    try:
        return TaskDefinition.model_validate(data)
    except ValidationError as e:
        # 원본 에러에 파일 경로 컨텍스트 추가하여 re-raise
        raise ValueError(f"Task YAML 검증 실패 ({resolved_path}): {e}") from e


def validate_task_yaml(path: str | Path) -> tuple[bool, list[str]]:
    """
    Task YAML 파일 검증

    Returns:
        (성공 여부, 에러 메시지 목록)
    """
    try:
        load_task(path)
        return True, []
    except FileNotFoundError as e:
        return False, [str(e)]
    except ValidationError as e:
        errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        return False, errors
    except Exception as e:
        return False, [str(e)]


# ============================================================================
# Suite 로딩
# ============================================================================


def load_suite(path: str | Path, base_dir: Path | None = None) -> SuiteDefinition:
    """
    Suite YAML 파일 로드 및 검증

    Args:
        path: Suite YAML 파일 경로
        base_dir: 상대 경로 해석 기준 디렉토리

    Returns:
        SuiteDefinition: 검증된 Suite 정의

    Raises:
        FileNotFoundError: 파일이 없는 경우
        ValidationError: 스키마 검증 실패
    """
    resolved_path = _resolve_path(path, base_dir)
    data = _load_yaml(resolved_path)

    try:
        return SuiteDefinition.model_validate(data)
    except ValidationError as e:
        # 원본 에러에 파일 경로 컨텍스트 추가하여 re-raise
        raise ValueError(f"Suite YAML 검증 실패 ({resolved_path}): {e}") from e


def validate_suite_yaml(path: str | Path) -> tuple[bool, list[str]]:
    """
    Suite YAML 파일 검증

    Returns:
        (성공 여부, 에러 메시지 목록)
    """
    try:
        load_suite(path)
        return True, []
    except FileNotFoundError as e:
        return False, [str(e)]
    except ValidationError as e:
        errors = [f"{err['loc']}: {err['msg']}" for err in e.errors()]
        return False, errors
    except Exception as e:
        return False, [str(e)]


# ============================================================================
# Suite → Task 로딩
# ============================================================================


def load_tasks_from_suite(
    suite_path: str | Path,
    only_enabled: bool = True,
) -> list[tuple[TaskDefinition, dict | None]]:
    """
    Suite에 포함된 모든 Task 로드

    Args:
        suite_path: Suite YAML 파일 경로
        only_enabled: 활성화된 Task만 로드할지 여부

    Returns:
        [(TaskDefinition, override_config), ...] 목록

    Raises:
        FileNotFoundError: Suite 또는 Task 파일이 없는 경우
        ValidationError: 스키마 검증 실패
    """
    suite_path = _resolve_path(suite_path)
    suite = load_suite(suite_path)
    suite_dir = suite_path.parent

    tasks = []
    for task_ref in suite.suite.tasks:
        if isinstance(task_ref, str):
            # 단순 경로 참조
            task_path = task_ref
            enabled = True
            override = None
        else:
            # TaskReference 객체
            task_path = task_ref.path
            enabled = task_ref.enabled
            override = task_ref.override

        if only_enabled and not enabled:
            continue

        task = load_task(task_path, base_dir=suite_dir)
        tasks.append((task, override))

    return tasks


# ============================================================================
# 디스커버리
# ============================================================================


def discover_tasks(
    directory: str | Path | None = None,
    recursive: bool = True,
) -> list[Path]:
    """
    디렉토리에서 Task YAML 파일 검색

    Args:
        directory: 검색 디렉토리 (기본: evals/tasks)
        recursive: 하위 디렉토리 포함 여부

    Returns:
        Task YAML 파일 경로 목록
    """
    directory = Path(directory) if directory else TASKS_DIR

    if not directory.exists():
        return []

    pattern = "**/*.yaml" if recursive else "*.yaml"
    yaml_files = list(directory.glob(pattern))

    # task: 키가 있는 파일만 필터링
    task_files = []
    for f in yaml_files:
        try:
            data = _load_yaml(f)
            if "task" in data:
                task_files.append(f)
        except Exception:
            continue

    return sorted(task_files)


def discover_suites(
    directory: str | Path | None = None,
    recursive: bool = True,
) -> list[Path]:
    """
    디렉토리에서 Suite YAML 파일 검색

    Args:
        directory: 검색 디렉토리 (기본: evals/suites)
        recursive: 하위 디렉토리 포함 여부

    Returns:
        Suite YAML 파일 경로 목록
    """
    directory = Path(directory) if directory else SUITES_DIR

    if not directory.exists():
        return []

    pattern = "**/*.yaml" if recursive else "*.yaml"
    yaml_files = list(directory.glob(pattern))

    # suite: 키가 있는 파일만 필터링
    suite_files = []
    for f in yaml_files:
        try:
            data = _load_yaml(f)
            if "suite" in data:
                suite_files.append(f)
        except Exception:
            continue

    return sorted(suite_files)


# ============================================================================
# 유틸리티
# ============================================================================


def get_task_by_id(
    task_id: str,
    search_dir: str | Path | None = None,
) -> TaskDefinition | None:
    """
    Task ID로 Task 검색

    Args:
        task_id: Task ID
        search_dir: 검색 디렉토리

    Returns:
        TaskDefinition 또는 None
    """
    for task_path in discover_tasks(search_dir):
        try:
            task = load_task(task_path)
            if task.get_task_id() == task_id:
                return task
        except Exception:
            continue
    return None


def get_suite_by_id(
    suite_id: str,
    search_dir: str | Path | None = None,
) -> SuiteDefinition | None:
    """
    Suite ID로 Suite 검색

    Args:
        suite_id: Suite ID
        search_dir: 검색 디렉토리

    Returns:
        SuiteDefinition 또는 None
    """
    for suite_path in discover_suites(search_dir):
        try:
            suite = load_suite(suite_path)
            if suite.get_suite_id() == suite_id:
                return suite
        except Exception:
            continue
    return None


def validate_all_tasks(directory: str | Path | None = None) -> dict[str, list[str]]:
    """
    디렉토리의 모든 Task YAML 검증

    Returns:
        {파일 경로: [에러 메시지 목록]} (에러가 있는 파일만)
    """
    errors = {}
    for task_path in discover_tasks(directory):
        valid, error_msgs = validate_task_yaml(task_path)
        if not valid:
            errors[str(task_path)] = error_msgs
    return errors


def validate_all_suites(directory: str | Path | None = None) -> dict[str, list[str]]:
    """
    디렉토리의 모든 Suite YAML 검증

    Returns:
        {파일 경로: [에러 메시지 목록]} (에러가 있는 파일만)
    """
    errors = {}
    for suite_path in discover_suites(directory):
        valid, error_msgs = validate_suite_yaml(suite_path)
        if not valid:
            errors[str(suite_path)] = error_msgs
    return errors
