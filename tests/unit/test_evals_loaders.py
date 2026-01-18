"""
Evals YAML 로더 단위 테스트

backend/evals/loaders/yaml_loader.py 테스트
"""

from pathlib import Path

import pytest

from backend.evals.loaders.yaml_loader import (
    discover_suites,
    discover_tasks,
    load_suite,
    load_task,
    load_tasks_from_suite,
    validate_suite_yaml,
    validate_task_yaml,
)
from backend.evals.models.enums import GraderType, ScoringMode, SuitePurpose, TaskType
from backend.evals.models.suite import SuiteDefinition
from backend.evals.models.task import TaskDefinition

# ============================================================================
# Fixture
# ============================================================================


@pytest.fixture
def sample_task_yaml(tmp_path: Path) -> Path:
    """샘플 Task YAML 파일 생성"""
    task_dir = tmp_path / "tasks"
    task_dir.mkdir()

    task_content = """
task:
  id: test-task-001
  type: workflow
  desc: "테스트용 Task"
  suite: test-suite
  version: "1.0.0"

  metadata:
    domain: functionality
    difficulty: easy
    risk: low
    purpose: regression
    expected_pass_rate: 0.9
    owner: test-team

  inputs:
    prompt: "테스트 프롬프트입니다."
    context:
      workflow_id: "WF-TEST"

  trials:
    k: 3
    parallel: true

  environment:
    sandbox: process
    reset: clean
    network: internal

  agent:
    adapter: ax_agent_sdk
    agent_id: orchestrator
    model: claude-sonnet-4-20250514
    max_turns: 10

  graders:
    - type: deterministic_tests
      id: unit_tests
      weight: 0.5
      config:
        framework: pytest
        test_files:
          - "tests/test_example.py"

    - type: state_check
      id: db_state
      weight: 0.5
      required: true
      config:
        checks:
          - type: db_row_exists
            target: "entities"

  scoring:
    mode: weighted
    pass_threshold: 0.8

  timeout:
    total_seconds: 120
    per_turn_seconds: 30

  cost_budget:
    max_tokens: 30000
    max_usd: 0.3

  tags:
    - test
    - workflow
"""
    task_file = task_dir / "test-task.yaml"
    task_file.write_text(task_content, encoding="utf-8")

    return task_file


@pytest.fixture
def sample_suite_yaml(tmp_path: Path, sample_task_yaml: Path) -> Path:
    """샘플 Suite YAML 파일 생성"""
    suite_dir = tmp_path / "suites"
    suite_dir.mkdir()

    # Task 파일 상대 경로 계산
    task_rel_path = sample_task_yaml.relative_to(tmp_path)

    suite_content = f"""
suite:
  id: test-suite-001
  name: "테스트 스위트"
  description: "단위 테스트용 스위트"
  version: "1.0.0"
  purpose: regression
  domain: workflow
  owner_team: test-team

  tasks:
    - path: "{task_rel_path.as_posix()}"
      enabled: true

  defaults:
    trials:
      k: 3
      parallel: true
    timeout:
      total_seconds: 180

  schedule:
    enabled: true
    on_pr: true
    branches:
      - main

  gates:
    enabled: true
    blocking: true
    pass_criteria:
      min_pass_rate: 0.9
      max_regression_count: 0

  tags:
    - test
    - regression
"""
    suite_file = suite_dir / "test-suite.yaml"
    suite_file.write_text(suite_content, encoding="utf-8")

    return suite_file


@pytest.fixture
def invalid_task_yaml(tmp_path: Path) -> Path:
    """유효하지 않은 Task YAML 파일 생성"""
    task_dir = tmp_path / "invalid"
    task_dir.mkdir()

    # 필수 필드 누락
    invalid_content = """
task:
  id: invalid-task
  type: invalid_type
  desc: "유효하지 않은 Task"
"""
    task_file = task_dir / "invalid-task.yaml"
    task_file.write_text(invalid_content, encoding="utf-8")

    return task_file


@pytest.fixture
def minimal_task_yaml(tmp_path: Path) -> Path:
    """최소 필수 필드만 포함한 Task YAML"""
    task_dir = tmp_path / "minimal"
    task_dir.mkdir()

    minimal_content = """
task:
  id: minimal-task
  type: coding
  desc: "최소 Task"
  suite: minimal-suite

  graders:
    - type: deterministic_tests
      weight: 1.0
      config:
        framework: pytest
        test_files:
          - "test.py"

  scoring:
    mode: binary
    pass_threshold: 0.5
"""
    task_file = task_dir / "minimal-task.yaml"
    task_file.write_text(minimal_content, encoding="utf-8")

    return task_file


@pytest.fixture
def evals_directory(tmp_path: Path) -> tuple[Path, Path, Path]:
    """evals 디렉토리 구조 생성, (evals_dir, task1_path, task2_path) 반환"""
    evals_dir = tmp_path / "evals"
    tasks_dir = evals_dir / "tasks" / "workflow"
    suites_dir = evals_dir / "suites" / "regression"

    tasks_dir.mkdir(parents=True)
    suites_dir.mkdir(parents=True)

    # Task 1
    task1_content = """
task:
  id: task-001
  type: workflow
  desc: "Task 1"
  suite: suite-001

  graders:
    - type: state_check
      weight: 1.0
      config: {}

  scoring:
    mode: binary
"""
    task1_path = tasks_dir / "task-001.yaml"
    task1_path.write_text(task1_content, encoding="utf-8")

    # Task 2
    task2_content = """
task:
  id: task-002
  type: coding
  desc: "Task 2"
  suite: suite-001

  graders:
    - type: deterministic_tests
      weight: 1.0
      config:
        framework: pytest
        test_files: ["test.py"]

  scoring:
    mode: weighted
"""
    task2_path = tasks_dir / "task-002.yaml"
    task2_path.write_text(task2_content, encoding="utf-8")

    # Suite - 절대 경로 사용
    suite_content = f"""
suite:
  id: suite-001
  name: "테스트 스위트"
  purpose: regression

  tasks:
    - path: "{task1_path.as_posix()}"
    - path: "{task2_path.as_posix()}"
      enabled: false
"""
    (suites_dir / "suite-001.yaml").write_text(suite_content, encoding="utf-8")

    return evals_dir


# ============================================================================
# load_task 테스트
# ============================================================================


class TestLoadTask:
    """load_task 함수 테스트"""

    def test_load_valid_task(self, sample_task_yaml: Path):
        """유효한 Task YAML 로드 테스트"""
        task = load_task(sample_task_yaml)

        assert isinstance(task, TaskDefinition)
        assert task.get_task_id() == "test-task-001"
        assert task.task.type == TaskType.WORKFLOW
        assert task.task.desc == "테스트용 Task"
        assert task.task.version == "1.0.0"

    def test_load_task_metadata(self, sample_task_yaml: Path):
        """Task 메타데이터 로드 테스트"""
        task = load_task(sample_task_yaml)

        assert task.task.metadata is not None
        assert task.task.metadata.difficulty.value == "easy"
        assert task.task.metadata.risk.value == "low"
        assert task.task.metadata.expected_pass_rate == 0.9

    def test_load_task_inputs(self, sample_task_yaml: Path):
        """Task 입력 로드 테스트"""
        task = load_task(sample_task_yaml)

        assert task.task.inputs is not None
        assert "테스트 프롬프트" in task.task.inputs.prompt
        assert task.task.inputs.context["workflow_id"] == "WF-TEST"

    def test_load_task_graders(self, sample_task_yaml: Path):
        """Task 채점기 로드 테스트"""
        task = load_task(sample_task_yaml)

        assert len(task.task.graders) == 2
        assert task.task.graders[0].type == GraderType.DETERMINISTIC_TESTS
        assert task.task.graders[0].id == "unit_tests"
        assert task.task.graders[0].weight == 0.5

        assert task.task.graders[1].type == GraderType.STATE_CHECK
        assert task.task.graders[1].required is True

    def test_load_task_scoring(self, sample_task_yaml: Path):
        """Task 채점 설정 로드 테스트"""
        task = load_task(sample_task_yaml)

        assert task.task.scoring.mode == ScoringMode.WEIGHTED
        assert task.task.scoring.pass_threshold == 0.8

    def test_load_task_not_found(self, tmp_path: Path):
        """존재하지 않는 Task 파일 로드 테스트"""
        with pytest.raises(FileNotFoundError):
            load_task(tmp_path / "nonexistent.yaml")

    def test_load_minimal_task(self, minimal_task_yaml: Path):
        """최소 Task YAML 로드 테스트"""
        task = load_task(minimal_task_yaml)

        assert task.get_task_id() == "minimal-task"
        assert task.task.type == TaskType.CODING
        assert len(task.task.graders) == 1

    def test_load_task_with_base_dir(self, tmp_path: Path, sample_task_yaml: Path):
        """base_dir 기준 상대 경로 로드 테스트"""
        task = load_task(sample_task_yaml.name, base_dir=sample_task_yaml.parent)

        assert task.get_task_id() == "test-task-001"


# ============================================================================
# load_suite 테스트
# ============================================================================


class TestLoadSuite:
    """load_suite 함수 테스트"""

    def test_load_valid_suite(self, sample_suite_yaml: Path):
        """유효한 Suite YAML 로드 테스트"""
        suite = load_suite(sample_suite_yaml)

        assert isinstance(suite, SuiteDefinition)
        assert suite.get_suite_id() == "test-suite-001"
        assert suite.suite.name == "테스트 스위트"
        assert suite.suite.purpose == SuitePurpose.REGRESSION

    def test_load_suite_tasks(self, sample_suite_yaml: Path):
        """Suite Task 목록 로드 테스트"""
        suite = load_suite(sample_suite_yaml)

        assert len(suite.suite.tasks) == 1
        # TaskReference 객체
        task_ref = suite.suite.tasks[0]
        assert task_ref.enabled is True

    def test_load_suite_gates(self, sample_suite_yaml: Path):
        """Suite 게이트 설정 로드 테스트"""
        suite = load_suite(sample_suite_yaml)

        assert suite.is_gate_enabled() is True
        assert suite.get_min_pass_rate() == 0.9

    def test_load_suite_schedule(self, sample_suite_yaml: Path):
        """Suite 스케줄 설정 로드 테스트"""
        suite = load_suite(sample_suite_yaml)

        assert suite.suite.schedule is not None
        assert suite.suite.schedule.enabled is True
        assert suite.suite.schedule.on_pr is True
        assert "main" in suite.suite.schedule.branches

    def test_load_suite_not_found(self, tmp_path: Path):
        """존재하지 않는 Suite 파일 로드 테스트"""
        with pytest.raises(FileNotFoundError):
            load_suite(tmp_path / "nonexistent.yaml")


# ============================================================================
# validate 테스트
# ============================================================================


class TestValidation:
    """YAML 검증 테스트"""

    def test_validate_valid_task(self, sample_task_yaml: Path):
        """유효한 Task 검증 테스트"""
        is_valid, errors = validate_task_yaml(sample_task_yaml)

        assert is_valid is True
        assert errors == []

    def test_validate_invalid_task(self, invalid_task_yaml: Path):
        """유효하지 않은 Task 검증 테스트"""
        is_valid, errors = validate_task_yaml(invalid_task_yaml)

        assert is_valid is False
        assert len(errors) > 0

    def test_validate_nonexistent_task(self, tmp_path: Path):
        """존재하지 않는 Task 검증 테스트"""
        is_valid, errors = validate_task_yaml(tmp_path / "nonexistent.yaml")

        assert is_valid is False
        assert len(errors) == 1
        assert "찾을 수 없습니다" in errors[0]

    def test_validate_valid_suite(self, sample_suite_yaml: Path):
        """유효한 Suite 검증 테스트"""
        is_valid, errors = validate_suite_yaml(sample_suite_yaml)

        assert is_valid is True
        assert errors == []


# ============================================================================
# discover 테스트
# ============================================================================


class TestDiscovery:
    """Task/Suite 디스커버리 테스트"""

    def test_discover_tasks(self, evals_directory: Path):
        """Task 디스커버리 테스트"""
        tasks = discover_tasks(evals_directory)

        assert len(tasks) == 2
        task_names = [t.name for t in tasks]
        assert "task-001.yaml" in task_names
        assert "task-002.yaml" in task_names

    def test_discover_tasks_empty_dir(self, tmp_path: Path):
        """빈 디렉토리 Task 디스커버리 테스트"""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()

        tasks = discover_tasks(empty_dir)

        assert tasks == []

    def test_discover_tasks_nonexistent_dir(self, tmp_path: Path):
        """존재하지 않는 디렉토리 테스트"""
        tasks = discover_tasks(tmp_path / "nonexistent")

        assert tasks == []

    def test_discover_suites(self, evals_directory: Path):
        """Suite 디스커버리 테스트"""
        suites = discover_suites(evals_directory)

        assert len(suites) == 1
        assert suites[0].name == "suite-001.yaml"


# ============================================================================
# load_tasks_from_suite 테스트
# ============================================================================


class TestLoadTasksFromSuite:
    """Suite에서 Task 로드 테스트"""

    def test_load_enabled_tasks_only(self, evals_directory: Path):
        """활성화된 Task만 로드 테스트"""
        suite_path = evals_directory / "suites" / "regression" / "suite-001.yaml"

        tasks = load_tasks_from_suite(suite_path, only_enabled=True)

        # task-002는 enabled=false이므로 1개만 로드
        assert len(tasks) == 1
        task, override = tasks[0]
        assert task.get_task_id() == "task-001"
        assert override is None

    def test_load_all_tasks(self, evals_directory: Path):
        """모든 Task 로드 테스트"""
        suite_path = evals_directory / "suites" / "regression" / "suite-001.yaml"

        tasks = load_tasks_from_suite(suite_path, only_enabled=False)

        assert len(tasks) == 2


# ============================================================================
# TaskDefinition 메서드 테스트
# ============================================================================


class TestTaskDefinitionMethods:
    """TaskDefinition 메서드 테스트"""

    def test_get_task_id(self, sample_task_yaml: Path):
        """get_task_id 테스트"""
        task = load_task(sample_task_yaml)

        assert task.get_task_id() == "test-task-001"

    def test_get_suite_id(self, sample_task_yaml: Path):
        """get_suite_id 테스트"""
        task = load_task(sample_task_yaml)

        assert task.get_suite_id() == "test-suite"

    def test_get_trial_count(self, sample_task_yaml: Path):
        """get_trial_count 테스트"""
        task = load_task(sample_task_yaml)

        assert task.get_trial_count() == 3

    def test_get_timeout_seconds(self, sample_task_yaml: Path):
        """get_timeout_seconds 테스트"""
        task = load_task(sample_task_yaml)

        assert task.get_timeout_seconds() == 120

    def test_get_cost_budget_usd(self, sample_task_yaml: Path):
        """get_cost_budget_usd 테스트"""
        task = load_task(sample_task_yaml)

        assert task.get_cost_budget_usd() == 0.3


# ============================================================================
# SuiteDefinition 메서드 테스트
# ============================================================================


class TestSuiteDefinitionMethods:
    """SuiteDefinition 메서드 테스트"""

    def test_get_suite_id(self, sample_suite_yaml: Path):
        """get_suite_id 테스트"""
        suite = load_suite(sample_suite_yaml)

        assert suite.get_suite_id() == "test-suite-001"

    def test_get_task_count(self, sample_suite_yaml: Path):
        """get_task_count 테스트"""
        suite = load_suite(sample_suite_yaml)

        assert suite.get_task_count() == 1

    def test_is_regression(self, sample_suite_yaml: Path):
        """is_regression 테스트"""
        suite = load_suite(sample_suite_yaml)

        assert suite.is_regression() is True

    def test_is_gate_enabled(self, sample_suite_yaml: Path):
        """is_gate_enabled 테스트"""
        suite = load_suite(sample_suite_yaml)

        assert suite.is_gate_enabled() is True

    def test_get_min_pass_rate(self, sample_suite_yaml: Path):
        """get_min_pass_rate 테스트"""
        suite = load_suite(sample_suite_yaml)

        assert suite.get_min_pass_rate() == 0.9
