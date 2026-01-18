#!/usr/bin/env python
"""
Evals CLI

Eval Suite/Task 실행 및 게이트 검사를 위한 CLI
`python -m backend.evals run --suite regression` 형태로 실행

사용법:
    # Suite 실행
    python -m backend.evals run --suite regression
    python -m backend.evals run --suite workflow_regression --k 3

    # Task 필터링 실행
    python -m backend.evals run --suite regression --task wf01-seminar-basic

    # 옵션
    python -m backend.evals run --suite regression --parallel --k 5 --output json

    # 유효성 검사
    python -m backend.evals validate --suite evals/suites/regression/workflow-regression.yaml

    # Suite 목록 조회
    python -m backend.evals list --suites
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import structlog

# Windows UTF-8 출력 설정
if sys.platform == "win32":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 프로젝트 루트를 PYTHONPATH에 추가
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.evals.loaders import (
    discover_suites,
    discover_tasks,
    load_suite,
    load_tasks_from_suite,
    validate_suite_yaml,
    validate_task_yaml,
)
from backend.evals.models.suite import SuiteDefinition
from backend.evals.runners import RunnerConfig, RunnerContext, run_suite
from backend.evals.runners.gate_checker import GateChecker
from backend.evals.runners.results import RunResult

# 로거 설정
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)


# ============================================================================
# 결과 포맷터
# ============================================================================


def format_result_json(result: RunResult) -> str:
    """JSON 포맷으로 결과 출력"""
    return json.dumps(result.to_dict(), indent=2, ensure_ascii=False, default=str)


def format_result_yaml(result: RunResult) -> str:
    """YAML 포맷으로 결과 출력 (PyYAML 필요)"""
    try:
        import yaml

        return yaml.dump(result.to_dict(), allow_unicode=True, default_flow_style=False)
    except ImportError:
        logger.warning("PyYAML이 설치되지 않아 JSON으로 대체합니다")
        return format_result_json(result)


def format_result_summary(result: RunResult) -> str:
    """사람이 읽기 쉬운 요약 포맷"""
    lines = [
        "",
        "=" * 60,
        "📊 Eval 실행 결과 요약",
        "=" * 60,
        f"Run ID:    {result.run.run_id}",
        f"Suite:     {result.run.suite_id or 'N/A'}",
        f"상태:      {result.status.value}",
        "",
        "─" * 60,
        "📈 통계",
        "─" * 60,
        f"Task:      {result.passed_tasks}/{result.total_tasks} 통과",
        f"통과율:    {result.overall_pass_rate:.1%}",
        f"평균 점수: {result.overall_avg_score:.2f}",
        f"총 비용:   ${result.total_cost_usd:.4f}",
        f"소요 시간: {result.total_duration_seconds:.1f}초",
        "",
    ]

    # Task별 결과
    if result.task_results:
        lines.extend(
            [
                "─" * 60,
                "📋 Task별 결과",
                "─" * 60,
            ]
        )
        for task_result in result.task_results:
            status_icon = "✅" if task_result.passed else "❌"
            lines.append(
                f"  {status_icon} {task_result.task_id}: "
                f"pass@k={task_result.pass_at_k:.0%}, "
                f"avg={task_result.avg_score:.2f}"
            )
        lines.append("")

    # 게이트 결과
    lines.extend(
        [
            "─" * 60,
            "🚦 게이트 판정",
            "─" * 60,
            f"게이트 통과: {'✅ 통과' if result.gate_passed else '❌ 실패'}",
            f"판정:        {result.decision.value}",
            f"사유:        {result.gate_result.reason}",
        ]
    )

    # 실패 조건
    if result.gate_result.failed_conditions:
        lines.append("")
        lines.append("실패 조건:")
        for condition in result.gate_result.failed_conditions:
            lines.append(f"  - {condition}")

    lines.extend(
        [
            "",
            "=" * 60,
        ]
    )

    return "\n".join(lines)


# ============================================================================
# 명령어 핸들러
# ============================================================================


async def cmd_run(args: argparse.Namespace) -> int:
    """
    Suite/Task 실행 명령어

    Returns:
        종료 코드 (0: 성공, 1: 게이트 실패, 2: 실행 오류)
    """
    logger.info("Eval 실행 시작", suite=args.suite, task=args.task)

    try:
        # Suite 로드
        suite_def = _load_suite_by_name_or_path(args.suite)
        if suite_def is None:
            logger.error(f"Suite를 찾을 수 없습니다: {args.suite}")
            return 2

        logger.info(f"Suite 로드 완료: {suite_def.suite.name}")

        # Task 로드
        task_data = load_tasks_from_suite(args.suite_path)
        if not task_data:
            logger.error("Suite에 Task가 없습니다")
            return 2

        # Task 엔터티로 변환
        tasks = [td.to_task_entity() for td, _ in task_data]
        logger.info(f"Task {len(tasks)}개 로드 완료")

        # Task 필터 적용
        task_filter = args.task.split(",") if args.task else None

        # 채점기 맵 생성 (간단한 버전 - 실제로는 GraderFactory 사용)
        graders_map: dict[str, list[Any]] = {}
        # TODO: TaskDefinition의 graders를 GraderFactory로 변환

        # Runner 설정
        config = RunnerConfig(
            max_workers=args.parallel_workers if args.parallel else 1,
            total_timeout=suite_def.suite.defaults.timeout.get("total_seconds", 300)
            if suite_def.suite.defaults and suite_def.suite.defaults.timeout
            else 300,
        )

        # 실행 컨텍스트 (run_id는 SuiteRunner가 자동 생성하므로 임시값 사용)
        import uuid

        context = RunnerContext(
            run_id=f"cli_{uuid.uuid4().hex[:12]}",
            triggered_by="cli",
            git_sha=os.environ.get("GITHUB_SHA"),
            git_branch=os.environ.get("GITHUB_REF_NAME"),
        )

        # Suite 실행
        result = await run_suite(
            suite=suite_def.to_suite_entity(),
            tasks=tasks,
            graders_map=graders_map,
            task_filter=task_filter,
            k=args.k,
            parallel=args.parallel,
            config=config,
            context=context,
        )

        # 결과 출력
        if args.output == "json":
            print(format_result_json(result))
        elif args.output == "yaml":
            print(format_result_yaml(result))
        else:
            print(format_result_summary(result))

        # 게이트 체크
        if args.gate:
            checker = GateChecker(suite_def)
            gate_result = checker.check(result)

            if args.output == "summary":
                print("\n" + checker.format_report(gate_result))

            if not gate_result.passed:
                logger.warning("게이트 실패", reason=gate_result.reason)
                return 1

        logger.info("Eval 실행 완료", gate_passed=result.gate_passed)
        return 0 if result.gate_passed else 1

    except FileNotFoundError as e:
        logger.error(f"파일을 찾을 수 없습니다: {e}")
        return 2
    except Exception as e:
        logger.exception(f"실행 중 오류 발생: {e}")
        return 2


def _load_suite_by_name_or_path(suite_arg: str) -> SuiteDefinition | None:
    """이름 또는 경로로 Suite 로드"""
    # 파일 경로로 시도
    path = Path(suite_arg)
    if path.exists() and path.suffix in (".yaml", ".yml"):
        return load_suite(path)

    # 이름으로 검색
    name_mappings = {
        "regression": "evals/suites/regression/workflow-regression.yaml",
        "workflow_regression": "evals/suites/regression/workflow-regression.yaml",
        "capability": "evals/suites/capability/brief-capability.yaml",
        "brief_capability": "evals/suites/capability/brief-capability.yaml",
    }

    if suite_arg in name_mappings:
        mapped_path = Path(name_mappings[suite_arg])
        if mapped_path.exists():
            return load_suite(mapped_path)

    # 검색으로 찾기
    for suite_path in discover_suites():
        try:
            suite = load_suite(suite_path)
            if suite.suite.id == suite_arg:
                return suite
        except Exception:
            continue

    return None


async def cmd_validate(args: argparse.Namespace) -> int:
    """
    YAML 파일 유효성 검사 명령어

    Returns:
        종료 코드 (0: 유효, 1: 오류 있음)
    """
    path = Path(args.path)

    if not path.exists():
        logger.error(f"파일을 찾을 수 없습니다: {path}")
        return 1

    # Suite 또는 Task 파일 유형 결정
    if args.type == "suite" or "suite" in str(path):
        valid, errors = validate_suite_yaml(path)
        file_type = "Suite"
    else:
        valid, errors = validate_task_yaml(path)
        file_type = "Task"

    if valid:
        print(f"✅ {file_type} YAML 유효성 검사 통과: {path}")
        return 0
    else:
        print(f"❌ {file_type} YAML 유효성 검사 실패: {path}")
        for error in errors:
            print(f"  - {error}")
        return 1


async def cmd_list(args: argparse.Namespace) -> int:
    """
    Suite/Task 목록 조회 명령어
    """
    if args.suites:
        print("\n📦 사용 가능한 Suite 목록:")
        print("─" * 50)
        for suite_path in discover_suites():
            try:
                suite = load_suite(suite_path)
                task_count = len(suite.suite.tasks)
                print(f"  • {suite.suite.id}")
                print(f"    이름: {suite.suite.name}")
                print(f"    목적: {suite.suite.purpose.value}")
                print(f"    Task: {task_count}개")
                print(f"    경로: {suite_path}")
                print()
            except Exception as e:
                print(f"  ⚠️ {suite_path}: 로드 실패 ({e})")
        return 0

    if args.tasks:
        print("\n📋 사용 가능한 Task 목록:")
        print("─" * 50)
        for task_path in discover_tasks():
            try:
                from backend.evals.loaders import load_task

                task = load_task(task_path)
                print(f"  • {task.task.id}")
                print(f"    유형: {task.task.type.value}")
                print(f"    Suite: {task.task.suite}")
                print(f"    경로: {task_path}")
                print()
            except Exception as e:
                print(f"  ⚠️ {task_path}: 로드 실패 ({e})")
        return 0

    print("--suites 또는 --tasks 옵션을 지정하세요")
    return 1


# ============================================================================
# CLI 파서
# ============================================================================


def create_parser() -> argparse.ArgumentParser:
    """CLI 파서 생성"""
    parser = argparse.ArgumentParser(
        prog="python -m backend.evals",
        description="AX Discovery Portal Evals CLI - 에이전트 평가 및 회귀 테스트 실행",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  # regression suite 실행
  python -m backend.evals run --suite regression

  # 특정 Task만 실행
  python -m backend.evals run --suite regression --task wf01-seminar-basic

  # 병렬 실행 및 JSON 출력
  python -m backend.evals run --suite regression --parallel --output json

  # YAML 유효성 검사
  python -m backend.evals validate evals/suites/regression/workflow-regression.yaml
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="명령어")

    # run 명령어
    run_parser = subparsers.add_parser("run", help="Suite/Task 실행")
    run_parser.add_argument(
        "--suite",
        "-s",
        required=True,
        help="실행할 Suite (이름 또는 경로). 예: regression, workflow_regression",
    )
    run_parser.add_argument(
        "--task",
        "-t",
        help="실행할 Task ID (쉼표로 구분). 미지정 시 Suite 전체 실행",
    )
    run_parser.add_argument(
        "--k",
        type=int,
        default=3,
        help="Trial 횟수 (기본값: 3)",
    )
    run_parser.add_argument(
        "--parallel",
        action="store_true",
        help="Task 병렬 실행 (기본값: 순차)",
    )
    run_parser.add_argument(
        "--parallel-workers",
        type=int,
        default=4,
        help="병렬 실행 시 워커 수 (기본값: 4)",
    )
    run_parser.add_argument(
        "--output",
        "-o",
        choices=["summary", "json", "yaml"],
        default="summary",
        help="출력 형식 (기본값: summary)",
    )
    run_parser.add_argument(
        "--gate",
        action="store_true",
        default=True,
        help="게이트 체크 실행 (기본값: True)",
    )
    run_parser.add_argument(
        "--no-gate",
        dest="gate",
        action="store_false",
        help="게이트 체크 비활성화",
    )

    # validate 명령어
    validate_parser = subparsers.add_parser("validate", help="YAML 유효성 검사")
    validate_parser.add_argument(
        "path",
        help="검사할 YAML 파일 경로",
    )
    validate_parser.add_argument(
        "--type",
        choices=["suite", "task", "auto"],
        default="auto",
        help="파일 유형 (기본값: auto)",
    )

    # list 명령어
    list_parser = subparsers.add_parser("list", help="Suite/Task 목록 조회")
    list_parser.add_argument(
        "--suites",
        action="store_true",
        help="Suite 목록 조회",
    )
    list_parser.add_argument(
        "--tasks",
        action="store_true",
        help="Task 목록 조회",
    )

    return parser


def main() -> int:
    """CLI 엔트리포인트"""
    parser = create_parser()
    args = parser.parse_args()

    # 명령어 없으면 도움말 출력
    if not args.command:
        parser.print_help()
        return 0

    # run 명령어: suite 경로 저장
    if args.command == "run":
        args.suite_path = _resolve_suite_path(args.suite)
        if args.suite_path is None:
            logger.error(f"Suite를 찾을 수 없습니다: {args.suite}")
            return 2

    # 명령어 실행
    if args.command == "run":
        return asyncio.run(cmd_run(args))
    elif args.command == "validate":
        return asyncio.run(cmd_validate(args))
    elif args.command == "list":
        return asyncio.run(cmd_list(args))
    else:
        parser.print_help()
        return 0


def _resolve_suite_path(suite_arg: str) -> Path | None:
    """Suite 이름/경로를 실제 파일 경로로 해석"""
    # 파일 경로로 시도
    path = Path(suite_arg)
    if path.exists():
        return path

    # 이름 매핑
    name_mappings = {
        "regression": "evals/suites/regression/workflow-regression.yaml",
        "workflow_regression": "evals/suites/regression/workflow-regression.yaml",
        "capability": "evals/suites/capability/brief-capability.yaml",
        "brief_capability": "evals/suites/capability/brief-capability.yaml",
    }

    if suite_arg in name_mappings:
        mapped_path = Path(name_mappings[suite_arg])
        if mapped_path.exists():
            return mapped_path

    # discover로 검색
    for suite_path in discover_suites():
        try:
            suite = load_suite(suite_path)
            if suite.suite.id == suite_arg:
                return suite_path
        except Exception:
            continue

    return None


if __name__ == "__main__":
    sys.exit(main())
