"""
Evals 패키지 진입점

`python -m backend.evals` 명령어로 CLI 실행을 가능하게 함

사용법:
    python -m backend.evals run --suite regression
    python -m backend.evals validate evals/suites/regression/workflow-regression.yaml
    python -m backend.evals list --suites
"""

from backend.evals.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
