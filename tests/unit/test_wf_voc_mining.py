"""
WF-03 VoC Mining 단위 테스트
"""

import pytest

from backend.agent_runtime.workflows.wf_voc_mining import (
    VoCInput,
    VoCMiningPipeline,
    VoCOutput,
    run,
)


class TestVoCInput:
    """VoCInput 데이터클래스 테스트"""

    def test_default_values(self):
        """기본값 확인"""
        input_data = VoCInput(data_source="test_source")

        assert input_data.data_source == "test_source"
        assert input_data.play_id == "KT_Desk_V01_VoC"
        assert input_data.min_frequency == 5

    def test_custom_values(self):
        """커스텀 값 설정"""
        input_data = VoCInput(
            data_source="custom_source",
            play_id="CUSTOM_PLAY",
            min_frequency=10,
        )

        assert input_data.data_source == "custom_source"
        assert input_data.play_id == "CUSTOM_PLAY"
        assert input_data.min_frequency == 10


class TestVoCOutput:
    """VoCOutput 데이터클래스 테스트"""

    def test_output_structure(self):
        """출력 구조 확인"""
        output = VoCOutput(
            themes=[{"theme_id": "T1"}],
            signals=[{"signal_id": "S1"}],
            brief_candidates=[{"id": "B1"}],
        )

        assert len(output.themes) == 1
        assert len(output.signals) == 1
        assert len(output.brief_candidates) == 1


class TestVoCMiningPipeline:
    """VoCMiningPipeline 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.pipeline = VoCMiningPipeline()

    @pytest.mark.asyncio
    async def test_run_success(self):
        """파이프라인 실행 성공"""
        input_data = VoCInput(data_source="test_voc_data")

        result = await self.pipeline.run(input_data)

        assert isinstance(result, VoCOutput)
        assert len(result.themes) > 0
        assert len(result.signals) > 0

    @pytest.mark.asyncio
    async def test_analyze_themes(self):
        """테마 분석"""
        input_data = VoCInput(data_source="test_data")

        themes = await self.pipeline._analyze_themes(input_data)

        assert len(themes) == 2
        assert themes[0]["theme_id"] == "THEME-001"
        assert themes[0]["name"] == "응답 시간 지연"
        assert themes[0]["severity"] == "HIGH"
        assert themes[1]["theme_id"] == "THEME-002"
        assert themes[1]["severity"] == "MEDIUM"

    @pytest.mark.asyncio
    async def test_create_signals(self):
        """Signal 생성"""
        themes = [
            {
                "theme_id": "THEME-001",
                "name": "테스트 테마",
                "frequency": 50,
                "severity": "HIGH",
                "keywords": ["키워드1", "키워드2"],
            }
        ]

        signals = await self.pipeline._create_signals(themes, "TEST_PLAY")

        assert len(signals) == 1
        signal = signals[0]
        assert signal["title"] == "[VoC] 테스트 테마"
        assert signal["play_id"] == "TEST_PLAY"
        assert signal["source"] == "KT"
        assert signal["channel"] == "데스크리서치"
        assert signal["status"] == "NEW"
        assert signal["confidence"] == 1.0  # 50/50 = 1.0
        assert "키워드1" in signal["tags"]

    @pytest.mark.asyncio
    async def test_create_signals_low_frequency(self):
        """낮은 빈도의 Signal 생성"""
        themes = [
            {
                "theme_id": "THEME-001",
                "name": "낮은 빈도 테마",
                "frequency": 10,
                "severity": "LOW",
                "keywords": [],
            }
        ]

        signals = await self.pipeline._create_signals(themes, "TEST_PLAY")

        assert len(signals) == 1
        assert signals[0]["confidence"] == 0.2  # 10/50 = 0.2

    @pytest.mark.asyncio
    async def test_select_brief_candidates_high_confidence(self):
        """Brief 후보 선정 - 높은 신뢰도"""
        signals = [
            {"signal_id": "S1", "confidence": 0.9},
            {"signal_id": "S2", "confidence": 0.8},
            {"signal_id": "S3", "confidence": 0.7},
        ]

        candidates = await self.pipeline._select_brief_candidates(signals)

        assert len(candidates) == 2  # 상위 2개만
        assert candidates[0]["signal_id"] == "S1"
        assert candidates[1]["signal_id"] == "S2"

    @pytest.mark.asyncio
    async def test_select_brief_candidates_low_confidence(self):
        """Brief 후보 선정 - 낮은 신뢰도"""
        signals = [
            {"signal_id": "S1", "confidence": 0.5},
            {"signal_id": "S2", "confidence": 0.3},
        ]

        candidates = await self.pipeline._select_brief_candidates(signals)

        assert len(candidates) == 0  # 0.7 미만은 제외

    @pytest.mark.asyncio
    async def test_select_brief_candidates_mixed(self):
        """Brief 후보 선정 - 혼합"""
        signals = [
            {"signal_id": "S1", "confidence": 0.9},
            {"signal_id": "S2", "confidence": 0.5},
            {"signal_id": "S3", "confidence": 0.75},
        ]

        candidates = await self.pipeline._select_brief_candidates(signals)

        assert len(candidates) == 2
        # 0.9와 0.75만 포함
        candidate_ids = [c["signal_id"] for c in candidates]
        assert "S1" in candidate_ids
        assert "S3" in candidate_ids
        assert "S2" not in candidate_ids

    @pytest.mark.asyncio
    async def test_select_brief_candidates_empty(self):
        """Brief 후보 선정 - 빈 입력"""
        candidates = await self.pipeline._select_brief_candidates([])

        assert len(candidates) == 0


class TestRunFunction:
    """run 함수 테스트"""

    @pytest.mark.asyncio
    async def test_run_with_minimal_input(self):
        """최소 입력으로 실행"""
        result = await run({"data_source": "test_source"})

        assert "themes" in result
        assert "signals" in result
        assert "brief_candidates" in result

    @pytest.mark.asyncio
    async def test_run_with_full_input(self):
        """전체 입력으로 실행"""
        result = await run({
            "data_source": "full_test_source",
            "play_id": "CUSTOM_PLAY_ID",
            "min_frequency": 10,
        })

        assert "themes" in result
        assert len(result["signals"]) > 0
        # play_id가 적용되었는지 확인
        for signal in result["signals"]:
            assert signal["play_id"] == "CUSTOM_PLAY_ID"

    @pytest.mark.asyncio
    async def test_run_returns_dict(self):
        """dict 반환 확인"""
        result = await run({"data_source": "test"})

        assert isinstance(result, dict)
        assert isinstance(result["themes"], list)
        assert isinstance(result["signals"], list)
        assert isinstance(result["brief_candidates"], list)
