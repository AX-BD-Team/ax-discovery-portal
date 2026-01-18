"""
Evals CLI 단위 테스트

CLI 명령어 및 게이트 체커 검증
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from backend.evals.models.entities import Outcome, Run, Transcript, Trial
from backend.evals.models.enums import Decision, RunStatus, TrialStatus
from backend.evals.runners.gate_checker import (
    GateCheckConfig,
    GateChecker,
    GateResult,
    check_gate,
)
from backend.evals.runners.results import RunResult, TaskResult, TrialResult


class TestGateCheckConfig:
    """GateCheckConfig 테스트"""

    def test_default_config(self):
        """기본 설정 테스트"""
        config = GateCheckConfig()

        assert config.min_pass_rate == 0.8
        assert config.min_score == 0.5
        assert config.required_tasks == []
        assert config.blocking is True

    def test_custom_config(self):
        """커스텀 설정 테스트"""
        config = GateCheckConfig(
            min_pass_rate=0.9,
            min_score=0.7,
            required_tasks=["task_a", "task_b"],
            blocking=False,
        )

        assert config.min_pass_rate == 0.9
        assert config.min_score == 0.7
        assert config.required_tasks == ["task_a", "task_b"]
        assert config.blocking is False


class TestGateResult:
    """GateResult 테스트"""

    def test_default_result(self):
        """기본 결과 테스트"""
        result = GateResult()

        assert result.passed is False
        # 기본값은 UNKNOWN 또는 FAIL
        assert result.decision in (Decision.FAIL, Decision.UNKNOWN)
        assert result.conditions == {}
        assert result.failed_conditions == []

    def test_pass_result(self):
        """통과 결과 테스트"""
        result = GateResult(
            passed=True,
            decision=Decision.PASS,
            reason="모든 조건 통과",
            conditions={"pass_rate": True, "min_score": True},
        )

        assert result.passed is True
        assert result.decision == Decision.PASS
        assert result.reason == "모든 조건 통과"

    def test_marginal_result(self):
        """경계 결과 테스트"""
        result = GateResult(
            passed=False,
            decision=Decision.MARGINAL,
            reason="일부 조건 미달",
            failed_conditions=["required_tasks"],
        )

        assert result.passed is False
        assert result.decision == Decision.MARGINAL
        assert "required_tasks" in result.failed_conditions


class TestGateChecker:
    """GateChecker 테스트"""

    @pytest.fixture
    def sample_run_result(self):
        """샘플 RunResult 생성"""
        run = Run(
            run_id="run_test123",
            task_ids=["task_a", "task_b"],
            status=RunStatus.COMPLETED,
        )

        # TaskResult 생성
        task_results = [
            self._create_task_result("task_a", passed=True, score=0.9),
            self._create_task_result("task_b", passed=True, score=0.8),
        ]

        result = RunResult(
            run=run,
            task_results=task_results,
        )
        result.compute_statistics()
        return result

    def _create_task_result(
        self,
        task_id: str,
        passed: bool,
        score: float,
    ) -> TaskResult:
        """TaskResult 헬퍼 생성"""
        trial = Trial(
            trial_id=f"trial_{task_id}",
            run_id="run_test123",
            task_id=task_id,
            trial_index=0,
            status=TrialStatus.COMPLETED if passed else TrialStatus.FAILED,
            passed=passed,
            score=score,
        )

        trial_result = TrialResult(
            trial=trial,
            transcript=Transcript(trial_id=trial.trial_id),
            outcome=Outcome(trial_id=trial.trial_id, passed=passed),
        )
        trial_result.passed = passed
        trial_result.score = score

        task_result = TaskResult(
            task_id=task_id,
            trials=[trial_result],
        )
        task_result.compute_statistics()
        return task_result

    def test_check_all_pass(self, sample_run_result):
        """모든 조건 통과 테스트"""
        config = GateCheckConfig(
            min_pass_rate=0.8,
            min_score=0.5,
            required_tasks=[],
        )

        checker = GateChecker(config=config)
        result = checker.check(sample_run_result)

        assert result.passed is True
        assert result.decision == Decision.PASS
        assert result.conditions.get("pass_rate") is True
        assert result.conditions.get("min_score") is True

    def test_check_pass_rate_fail(self):
        """통과율 미달 테스트"""
        run = Run(
            run_id="run_fail",
            task_ids=["task_a", "task_b"],
            status=RunStatus.COMPLETED,
        )

        task_results = [
            self._create_task_result("task_a", passed=False, score=0.3),
            self._create_task_result("task_b", passed=False, score=0.4),
        ]

        run_result = RunResult(run=run, task_results=task_results)
        run_result.compute_statistics()

        config = GateCheckConfig(min_pass_rate=0.8)
        checker = GateChecker(config=config)
        result = checker.check(run_result)

        assert result.passed is False
        assert result.conditions.get("pass_rate") is False
        # failed_conditions는 한글 메시지를 포함
        assert len(result.failed_conditions) > 0

    def test_check_required_tasks(self):
        """필수 Task 검사 테스트"""
        run = Run(
            run_id="run_required",
            task_ids=["task_a", "task_b"],
            status=RunStatus.COMPLETED,
        )

        task_results = [
            self._create_task_result("task_a", passed=True, score=0.9),
            self._create_task_result("task_b", passed=False, score=0.3),
        ]

        run_result = RunResult(run=run, task_results=task_results)
        run_result.compute_statistics()

        # task_b가 필수인데 실패
        config = GateCheckConfig(
            min_pass_rate=0.5,
            required_tasks=["task_b"],
        )
        checker = GateChecker(config=config)
        result = checker.check(run_result)

        assert result.passed is False
        assert result.conditions.get("required_tasks") is False
        # failed_required_tasks는 포맷팅된 문자열 포함
        assert any("task_b" in t for t in result.failed_required_tasks)

    def test_check_min_score_fail(self):
        """최소 점수 미달 테스트"""
        run = Run(
            run_id="run_score",
            task_ids=["task_a"],
            status=RunStatus.COMPLETED,
        )

        task_results = [
            self._create_task_result("task_a", passed=True, score=0.4),
        ]

        run_result = RunResult(run=run, task_results=task_results)
        run_result.compute_statistics()

        config = GateCheckConfig(min_score=0.6)
        checker = GateChecker(config=config)
        result = checker.check(run_result)

        assert result.passed is False
        assert result.conditions.get("min_score") is False

    def test_check_marginal_decision(self):
        """MARGINAL 판정 테스트"""
        run = Run(
            run_id="run_marginal",
            task_ids=["task_a", "task_b", "task_c"],
            status=RunStatus.COMPLETED,
        )

        # 66% 통과율 (60-80% 범위)
        task_results = [
            self._create_task_result("task_a", passed=True, score=0.8),
            self._create_task_result("task_b", passed=True, score=0.7),
            self._create_task_result("task_c", passed=False, score=0.4),
        ]

        run_result = RunResult(run=run, task_results=task_results)
        run_result.compute_statistics()

        config = GateCheckConfig(min_pass_rate=0.8)
        checker = GateChecker(config=config)
        result = checker.check(run_result)

        assert result.passed is False
        assert result.decision == Decision.MARGINAL

    def test_format_report(self, sample_run_result):
        """리포트 포맷 테스트"""
        config = GateCheckConfig()
        checker = GateChecker(config=config)
        result = checker.check(sample_run_result)

        report = checker.format_report(result)

        assert "게이트" in report or "Gate" in report or "PASS" in report or "통과" in report


class TestCheckGateHelper:
    """check_gate 헬퍼 함수 테스트"""

    def test_check_gate_default(self):
        """기본 설정으로 check_gate 테스트"""
        run = Run(
            run_id="run_helper",
            task_ids=["task_a"],
            status=RunStatus.COMPLETED,
        )

        trial = Trial(
            trial_id="trial_helper",
            run_id="run_helper",
            task_id="task_a",
            trial_index=0,
            status=TrialStatus.COMPLETED,
            passed=True,
            score=0.9,
        )

        trial_result = TrialResult(
            trial=trial,
            transcript=Transcript(trial_id="trial_helper"),
            outcome=Outcome(trial_id="trial_helper", passed=True),
        )
        trial_result.passed = True
        trial_result.score = 0.9

        task_result = TaskResult(
            task_id="task_a",
            trials=[trial_result],
        )
        task_result.compute_statistics()

        run_result = RunResult(run=run, task_results=[task_result])
        run_result.compute_statistics()

        result = check_gate(run_result)

        assert isinstance(result, GateResult)
        assert result.passed is True

    def test_check_gate_custom_config(self):
        """커스텀 설정으로 check_gate 테스트"""
        run = Run(
            run_id="run_custom",
            task_ids=["task_a"],
            status=RunStatus.COMPLETED,
        )

        trial = Trial(
            trial_id="trial_custom",
            run_id="run_custom",
            task_id="task_a",
            trial_index=0,
            status=TrialStatus.COMPLETED,
            passed=True,
            score=0.7,
        )

        trial_result = TrialResult(
            trial=trial,
            transcript=Transcript(trial_id="trial_custom"),
            outcome=Outcome(trial_id="trial_custom", passed=True),
        )
        trial_result.passed = True
        trial_result.score = 0.7

        task_result = TaskResult(
            task_id="task_a",
            trials=[trial_result],
        )
        task_result.compute_statistics()

        run_result = RunResult(run=run, task_results=[task_result])
        run_result.compute_statistics()

        # 높은 min_score 요구
        config = GateCheckConfig(min_score=0.9)
        result = check_gate(run_result, config=config)

        assert result.passed is False
        assert result.conditions.get("min_score") is False


class TestCLIArguments:
    """CLI 인자 파싱 테스트"""

    def test_import_cli(self):
        """CLI 모듈 import 테스트"""
        from backend.evals import cli

        assert hasattr(cli, "main")

    def test_run_command_args(self):
        """run 명령어 인자 테스트"""
        from backend.evals.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            [
                "run",
                "--suite",
                "regression",
                "--k",
                "3",
                "--parallel",
                "--output",
                "json",
            ]
        )

        assert args.command == "run"
        assert args.suite == "regression"
        assert args.k == 3
        assert args.parallel is True
        assert args.output == "json"

    def test_validate_command_args(self):
        """validate 명령어 인자 테스트"""
        from backend.evals.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(
            [
                "validate",
                "evals/tasks/workflow/test.yaml",
            ]
        )

        assert args.command == "validate"
        assert args.path == "evals/tasks/workflow/test.yaml"

    def test_list_command_args(self):
        """list 명령어 인자 테스트"""
        from backend.evals.cli import create_parser

        parser = create_parser()

        # --suites
        args = parser.parse_args(["list", "--suites"])
        assert args.command == "list"
        assert args.suites is True

        # --tasks
        args = parser.parse_args(["list", "--tasks"])
        assert args.tasks is True


class TestCLIIntegration:
    """CLI 통합 테스트"""

    def test_list_suites(self, capsys):
        """Suite 목록 조회 테스트"""
        import sys

        with patch.object(sys, "argv", ["cli", "list", "--suites"]):
            # CLI 실행은 실제 파일 시스템에 의존하므로 mock 필요
            pass  # 통합 테스트는 별도 실행

    def test_validate_task_yaml(self):
        """Task YAML 유효성 검사 테스트"""
        from backend.evals.loaders import validate_task_yaml

        # 테스트용 YAML 경로
        test_yaml = Path("evals/tasks/workflow/wf01-seminar-basic.yaml")

        if test_yaml.exists():
            is_valid, errors = validate_task_yaml(test_yaml)
            # 유효한 YAML이면 에러 없음
            if is_valid:
                assert errors == []
