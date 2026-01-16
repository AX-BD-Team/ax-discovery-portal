"""
WF-03 VoC Mining 단위 테스트
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.agent_runtime.workflows.wf_voc_mining import (
    VoCInput,
    VoCMiningPipeline,
    VoCMiningPipelineWithDB,
    VoCMiningPipelineWithEvents,
    VoCOutput,
    run,
    run_with_db,
    run_with_events,
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
        # 테마 키워드에 매칭되는 충분한 데이터 제공
        voc_texts = "\n".join(
            [
                "응답이 너무 느립니다",
                "대기 시간이 너무 깁니다",
                "시스템이 느려요",
                "처리 시간이 오래 걸려요",
                "기다리는 시간이 길어요",
            ]
        )
        input_data = VoCInput(
            text_content=voc_texts,
            source_type="text",
            min_frequency=2,
            max_themes=5,
        )

        result = await self.pipeline.run(input_data)

        assert isinstance(result, VoCOutput)
        # 테마가 있으면 시그널도 생성됨
        if len(result.themes) > 0:
            assert len(result.signals) > 0

    @pytest.mark.asyncio
    async def test_analyze_themes_with_matching_data(self):
        """매칭되는 데이터로 테마 분석"""
        voc_texts = "\n".join(
            [
                "응답이 너무 느립니다",
                "대기 시간이 너무 깁니다",
                "시스템이 느려요",
                "처리 시간이 오래 걸려요",
                "기다리는 시간이 길어요",
            ]
        )
        input_data = VoCInput(
            text_content=voc_texts,
            source_type="text",
            min_frequency=2,
            max_themes=5,
        )

        themes = await self.pipeline._analyze_themes(input_data)

        assert len(themes) >= 1
        theme_names = [t["name"] for t in themes]
        assert "응답 시간 지연" in theme_names

    @pytest.mark.asyncio
    async def test_analyze_themes_empty_data(self):
        """빈 데이터로 테마 분석"""
        input_data = VoCInput(text_content="", source_type="text")

        themes = await self.pipeline._analyze_themes(input_data)

        assert len(themes) == 0

    def test_extract_themes_from_records(self):
        """_extract_themes_from_records 메소드 테스트"""
        from backend.agent_runtime.workflows.voc_data_handlers import VoCRecord

        records = [
            VoCRecord(text="응답이 너무 느립니다"),
            VoCRecord(text="대기 시간이 너무 깁니다"),
            VoCRecord(text="시스템이 느려요"),
        ]

        themes = self.pipeline._extract_themes_from_records(records, min_frequency=1, max_themes=5)

        assert len(themes) >= 1
        assert themes[0]["name"] == "응답 시간 지연"
        assert themes[0]["frequency"] >= 1

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
        voc_texts = "\n".join(
            [
                "응답이 너무 느립니다",
                "대기 시간이 너무 깁니다",
                "시스템이 느려요",
                "처리 시간이 오래 걸려요",
                "기다리는 시간이 길어요",
            ]
        )
        result = await run(
            {
                "source_type": "text",
                "text_content": voc_texts,
                "play_id": "CUSTOM_PLAY_ID",
                "min_frequency": 2,
            }
        )

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

    @pytest.mark.asyncio
    async def test_run_with_extended_fields(self):
        """확장된 필드로 실행"""
        result = await run(
            {
                "source_type": "text",
                "text_content": "응답이 너무 느립니다\n절차가 복잡합니다",
                "play_id": "KT_Desk_V01_VoC",
                "max_themes": 3,
            }
        )

        assert "themes" in result
        assert "signals" in result


class TestVoCDataHandlers:
    """VoC 데이터 핸들러 테스트"""

    def test_get_handler_text(self):
        """텍스트 핸들러 가져오기"""
        from backend.agent_runtime.workflows.voc_data_handlers import get_handler

        handler = get_handler("text")
        assert handler is not None

    def test_get_handler_csv(self):
        """CSV 핸들러 가져오기"""
        from backend.agent_runtime.workflows.voc_data_handlers import get_handler

        handler = get_handler("csv")
        assert handler is not None

    def test_get_handler_api(self):
        """API 핸들러 가져오기"""
        from backend.agent_runtime.workflows.voc_data_handlers import get_handler

        handler = get_handler("api")
        assert handler is not None

    def test_get_handler_invalid(self):
        """잘못된 소스 타입"""
        from backend.agent_runtime.workflows.voc_data_handlers import get_handler

        with pytest.raises(ValueError):
            get_handler("invalid_type")

    def test_text_handler_parse(self):
        """텍스트 핸들러 파싱"""
        from backend.agent_runtime.workflows.voc_data_handlers import TextVoCHandler

        handler = TextVoCHandler()
        records = handler.parse("응답이 느립니다\n절차가 복잡합니다\n화면이 이상합니다")

        assert len(records) == 3
        assert records[0].text == "응답이 느립니다"
        assert records[1].text == "절차가 복잡합니다"
        assert records[2].text == "화면이 이상합니다"

    def test_text_handler_empty_lines(self):
        """텍스트 핸들러 - 빈 줄 처리"""
        from backend.agent_runtime.workflows.voc_data_handlers import TextVoCHandler

        handler = TextVoCHandler()
        records = handler.parse("첫번째 VoC입니다\n\n두번째 VoC입니다\n   \n세번째 VoC입니다")

        assert len(records) == 3

    def test_csv_handler_parse(self):
        """CSV 핸들러 파싱"""
        from backend.agent_runtime.workflows.voc_data_handlers import CSVVoCHandler

        handler = CSVVoCHandler()
        csv_data = """text,category,severity
응답이 느립니다,불만,HIGH
절차가 복잡합니다,제안,MEDIUM"""

        records = handler.parse(csv_data)

        assert len(records) == 2
        assert records[0].text == "응답이 느립니다"
        assert records[0].category == "불만"
        assert records[0].severity == "HIGH"

    def test_api_handler_parse(self):
        """API 핸들러 파싱"""
        from backend.agent_runtime.workflows.voc_data_handlers import APIVoCHandler

        handler = APIVoCHandler()
        api_data = [
            {"text": "응답이 느립니다", "category": "불만"},
            {"content": "절차가 복잡합니다", "type": "제안"},
            {"message": "화면이 이상합니다"},
        ]

        records = handler.parse(api_data)

        assert len(records) == 3
        assert records[0].text == "응답이 느립니다"
        assert records[1].text == "절차가 복잡합니다"
        assert records[2].text == "화면이 이상합니다"


class TestPipelineSteps:
    """파이프라인 단계 테스트"""

    def test_steps_defined(self):
        """STEPS 정의 확인"""
        pipeline = VoCMiningPipeline()

        assert hasattr(pipeline, "STEPS")
        assert len(pipeline.STEPS) == 5

        step_ids = [s["id"] for s in pipeline.STEPS]
        assert "DATA_LOADING" in step_ids
        assert "DATA_PREPROCESSING" in step_ids
        assert "THEME_EXTRACTION" in step_ids
        assert "SIGNAL_GENERATION" in step_ids
        assert "BRIEF_SELECTION" in step_ids


class TestVoCMiningPipelineWithEvents:
    """VoCMiningPipelineWithEvents 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.mock_emitter = MagicMock()
        # 모든 async emitter 메서드를 AsyncMock으로 설정
        self.mock_emitter.emit_run_started = AsyncMock()
        self.mock_emitter.emit_run_finished = AsyncMock()
        self.mock_emitter.emit_run_error = AsyncMock()
        self.mock_emitter.emit_step_started = AsyncMock()
        self.mock_emitter.emit_step_finished = AsyncMock()
        self.mock_emitter.emit_surface = AsyncMock()
        self.mock_emitter.emit_workflow_complete = AsyncMock()
        self.pipeline = VoCMiningPipelineWithEvents(self.mock_emitter)

    @pytest.mark.asyncio
    async def test_run_emits_events(self):
        """이벤트 발행 확인"""
        voc_texts = "\n".join(
            [
                "응답이 너무 느립니다",
                "대기 시간이 너무 깁니다",
                "시스템이 느려요",
            ]
        )
        input_data = VoCInput(
            text_content=voc_texts,
            source_type="text",
            min_frequency=1,
        )

        result = await self.pipeline.run(input_data)

        assert isinstance(result, VoCOutput)
        # 이벤트 발행 확인
        assert self.mock_emitter.emit_step_started.call_count >= 1
        assert self.mock_emitter.emit_step_finished.call_count >= 1
        self.mock_emitter.emit_run_finished.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_events_function(self):
        """run_with_events 함수 테스트"""
        with patch(
            "backend.agent_runtime.workflows.wf_voc_mining.VoCMiningPipelineWithEvents"
        ) as MockPipeline:
            mock_instance = MagicMock()
            mock_instance.run = AsyncMock(
                return_value=VoCOutput(themes=[], signals=[], brief_candidates=[])
            )
            MockPipeline.return_value = mock_instance

            mock_emitter = MagicMock()
            result = await run_with_events({"source_type": "text"}, mock_emitter)

            assert "themes" in result
            assert "signals" in result
            MockPipeline.assert_called_once_with(mock_emitter)


class TestVoCMiningPipelineWithDB:
    """VoCMiningPipelineWithDB 테스트"""

    def setup_method(self):
        """테스트 설정"""
        self.mock_emitter = MagicMock()
        # 모든 async emitter 메서드를 AsyncMock으로 설정
        self.mock_emitter.emit_run_started = AsyncMock()
        self.mock_emitter.emit_run_finished = AsyncMock()
        self.mock_emitter.emit_run_error = AsyncMock()
        self.mock_emitter.emit_step_started = AsyncMock()
        self.mock_emitter.emit_step_finished = AsyncMock()
        self.mock_emitter.emit_surface = AsyncMock()
        self.mock_emitter.emit_workflow_complete = AsyncMock()
        self.mock_db = AsyncMock()
        self.pipeline = VoCMiningPipelineWithDB(self.mock_emitter, self.mock_db)

    @pytest.mark.asyncio
    async def test_run_with_db(self):
        """DB 연동 파이프라인 실행"""
        voc_texts = "\n".join(
            [
                "응답이 너무 느립니다",
                "대기 시간이 너무 깁니다",
                "시스템이 느려요",
            ]
        )
        input_data = VoCInput(
            text_content=voc_texts,
            source_type="text",
            min_frequency=1,
        )

        result = await self.pipeline.run(input_data)

        assert isinstance(result, VoCOutput)
        # 이벤트 발행 확인 (DB 버전은 부모 클래스의 이벤트를 발행)
        assert self.mock_emitter.emit_step_started.call_count >= 1
        self.mock_emitter.emit_run_finished.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_with_db_function(self):
        """run_with_db 함수 테스트"""
        with patch(
            "backend.agent_runtime.workflows.wf_voc_mining.VoCMiningPipelineWithDB"
        ) as MockPipeline:
            mock_instance = MagicMock()
            mock_instance.run = AsyncMock(
                return_value=VoCOutput(themes=[], signals=[], brief_candidates=[])
            )
            MockPipeline.return_value = mock_instance

            mock_emitter = MagicMock()
            mock_db = AsyncMock()
            result = await run_with_db({"source_type": "text"}, mock_emitter, mock_db)

            assert "themes" in result
            assert "signals" in result
            MockPipeline.assert_called_once_with(mock_emitter, mock_db)
