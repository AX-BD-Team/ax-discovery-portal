"""
Agent Runtime Runner

Claude Agent SDK를 사용한 에이전트 실행 환경
"""

import asyncio
import json
import os
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, cast

import structlog

# Claude Agent SDK
from claude_agent_sdk import (
    ClaudeAgentOptions,
    ClaudeSDKClient,
    create_sdk_mcp_server,
    tool,
)
from claude_agent_sdk.types import AgentDefinition

logger = structlog.get_logger()


@dataclass
class AgentConfig:
    """에이전트 설정"""

    agent_id: str
    model: str = "claude-sonnet-4-20250514"
    max_iterations: int = 100
    session_timeout: int = 3600
    skills_dir: str = ".claude/skills"
    tools: list[str] | None = None


@dataclass
class WorkflowConfig:
    """워크플로 설정"""

    workflow_id: str
    agents: list[str]
    timeout: int = 7200
    require_approval: bool = False


class AgentRuntime:
    """
    Claude Agent SDK 기반 에이전트 실행 환경

    Features:
    - 멀티에이전트 오케스트레이션
    - 세션 관리 (생성/재개)
    - MCP 도구 연동
    - 훅 (pre/post tool use)
    """

    def __init__(self):
        self.logger = logger.bind(component="agent_runtime")
        self.sessions: dict[str, Any] = {}
        self.agents: dict[str, Any] = {}

        # 환경 변수
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = os.getenv("AGENT_MODEL", "claude-sonnet-4-20250514")

    async def initialize(self):
        """런타임 초기화"""
        self.logger.info("Initializing agent runtime...")

        # 에이전트 로드
        await self._load_agents()

        self.logger.info("Agent runtime initialized")

    async def _connect_mcp_servers(self) -> dict:
        """MCP 서버 설정 반환 (SDK 도구로 변환)"""
        from backend.integrations.mcp_confluence.server import ConfluenceMCP
        from backend.integrations.mcp_slack.server import SlackMCP
        from backend.integrations.mcp_teams.server import TeamsMCP

        confluence_mcp = ConfluenceMCP()
        teams_mcp = TeamsMCP()
        slack_mcp = SlackMCP()

        # SDK 도구 생성 (각 MCP 메서드를 래핑)
        # SDK 0.1.19 API: @tool(name, description, input_schema)
        @tool(
            "confluence.search_pages",
            "Confluence 페이지 검색",
            {"query": str, "limit": int},
        )
        async def search_pages(args: dict):
            """Confluence 페이지 검색"""
            return await confluence_mcp.search_pages(args["query"], args.get("limit", 10))

        @tool(
            "confluence.get_page",
            "Confluence 페이지 조회",
            {"page_id": str},
        )
        async def get_page(args: dict):
            """Confluence 페이지 조회"""
            return await confluence_mcp.get_page(args["page_id"])

        @tool(
            "confluence.create_page",
            "Confluence 페이지 생성",
            {"title": str, "body_md": str, "parent_page_id": str},
        )
        async def create_page(args: dict):
            """Confluence 페이지 생성"""
            return await confluence_mcp.create_page(
                args["title"], args["body_md"], args.get("parent_page_id")
            )

        @tool(
            "confluence.update_page",
            "Confluence 페이지 업데이트",
            {"page_id": str, "body_md": str, "title": str},
        )
        async def update_page(args: dict):
            """Confluence 페이지 업데이트"""
            return await confluence_mcp.update_page(args["page_id"], args["body_md"], None)

        @tool(
            "confluence.append_to_page",
            "Confluence 페이지에 내용 추가",
            {"page_id": str, "append_md": str},
        )
        async def append_to_page(args: dict):
            """Confluence 페이지에 내용 추가"""
            return await confluence_mcp.append_to_page(args["page_id"], args["append_md"])

        @tool(
            "confluence.add_labels",
            "Confluence 페이지에 라벨 추가",
            {"page_id": str, "labels": list},
        )
        async def add_labels(args: dict):
            """Confluence 페이지에 라벨 추가"""
            return await confluence_mcp.add_labels(args["page_id"], args["labels"])

        @tool(
            "confluence.increment_play_activity_count",
            "Play DB 테이블에서 activity_qtd 증가",
            {"page_id": str, "play_id": str},
        )
        async def increment_play_activity_count(args: dict):
            """Play DB 테이블에서 activity_qtd 증가"""
            return await confluence_mcp.increment_play_activity_count(
                args["page_id"], args["play_id"]
            )

        # Teams MCP 도구
        @tool(
            "teams.send_message",
            "Teams 채널에 텍스트 메시지 전송",
            {"text": str, "title": str},
        )
        async def teams_send_message(args: dict):
            """Teams 채널에 텍스트 메시지 전송"""
            return await teams_mcp.send_message(args["text"], args.get("title"))

        @tool(
            "teams.send_notification",
            "Teams 채널에 알림 전송 (색상 강조 지원)",
            {"text": str, "title": str, "level": str, "facts": dict},
        )
        async def teams_send_notification(args: dict):
            """Teams 채널에 알림 전송 (색상 강조 지원)"""
            return await teams_mcp.send_notification(
                args["text"], args["title"], args.get("level", "info"), args.get("facts")
            )

        @tool(
            "teams.send_card",
            "Teams 채널에 Adaptive Card 전송",
            {"card": dict},
        )
        async def teams_send_card(args: dict):
            """Teams 채널에 Adaptive Card 전송"""
            return await teams_mcp.send_card(args["card"])

        @tool(
            "teams.request_approval",
            "Teams 채널에 승인 요청 카드 전송",
            {
                "title": str,
                "description": str,
                "requester": str,
                "item_id": str,
                "item_type": str,
                "details": dict,
            },
        )
        async def teams_request_approval(args: dict):
            """Teams 채널에 승인 요청 카드 전송"""
            return await teams_mcp.request_approval(
                args["title"],
                args["description"],
                args["requester"],
                args["item_id"],
                args.get("item_type", "Brief"),
                args.get("details"),
            )

        @tool(
            "teams.send_kpi_digest",
            "Teams 채널에 KPI Digest 카드 전송",
            {"period": str, "metrics": dict, "alerts": list, "top_plays": list},
        )
        async def teams_send_kpi_digest(args: dict):
            """Teams 채널에 KPI Digest 카드 전송"""
            return await teams_mcp.send_kpi_digest(
                args["period"], args["metrics"], args.get("alerts"), args.get("top_plays")
            )

        # Slack MCP 도구
        @tool(
            "slack.send_message",
            "Slack 채널에 텍스트 메시지 전송",
            {"text": str, "title": str},
        )
        async def slack_send_message(args: dict):
            """Slack 채널에 텍스트 메시지 전송"""
            return await slack_mcp.send_message(args["text"], args.get("title"))

        @tool(
            "slack.send_notification",
            "Slack 채널에 알림 전송 (색상 강조 지원)",
            {"text": str, "title": str, "level": str, "fields": dict},
        )
        async def slack_send_notification(args: dict):
            """Slack 채널에 알림 전송 (색상 강조 지원)"""
            return await slack_mcp.send_notification(
                args["text"], args["title"], args.get("level", "info"), args.get("fields")
            )

        @tool(
            "slack.send_blocks",
            "Slack 채널에 Block Kit 메시지 전송",
            {"blocks": list},
        )
        async def slack_send_blocks(args: dict):
            """Slack 채널에 Block Kit 메시지 전송"""
            return await slack_mcp.send_blocks(args["blocks"])

        @tool(
            "slack.request_approval",
            "Slack 채널에 승인 요청 메시지 전송",
            {
                "title": str,
                "description": str,
                "requester": str,
                "item_id": str,
                "item_type": str,
                "details": dict,
            },
        )
        async def slack_request_approval(args: dict):
            """Slack 채널에 승인 요청 메시지 전송"""
            return await slack_mcp.request_approval(
                args["title"],
                args["description"],
                args["requester"],
                args["item_id"],
                args.get("item_type", "Brief"),
                args.get("details"),
            )

        @tool(
            "slack.send_kpi_digest",
            "Slack 채널에 KPI Digest 메시지 전송",
            {"period": str, "metrics": dict, "alerts": list, "top_plays": list},
        )
        async def slack_send_kpi_digest(args: dict):
            """Slack 채널에 KPI Digest 메시지 전송"""
            return await slack_mcp.send_kpi_digest(
                args["period"], args["metrics"], args.get("alerts"), args.get("top_plays")
            )

        # SDK MCP 서버 생성
        try:
            confluence_server = create_sdk_mcp_server(
                name="confluence",
                version="1.0.0",
                tools=[
                    search_pages,
                    get_page,
                    create_page,
                    update_page,
                    append_to_page,
                    add_labels,
                    increment_play_activity_count,
                ],
            )

            teams_server = create_sdk_mcp_server(
                name="teams",
                version="1.0.0",
                tools=[
                    teams_send_message,
                    teams_send_notification,
                    teams_send_card,
                    teams_request_approval,
                    teams_send_kpi_digest,
                ],
            )

            slack_server = create_sdk_mcp_server(
                name="slack",
                version="1.0.0",
                tools=[
                    slack_send_message,
                    slack_send_notification,
                    slack_send_blocks,
                    slack_request_approval,
                    slack_send_kpi_digest,
                ],
            )

            self.logger.info(
                "MCP servers connected", servers=["confluence", "teams", "slack"], tools=17
            )

            return {"confluence": confluence_server, "teams": teams_server, "slack": slack_server}

        except Exception as e:
            self.logger.error("Failed to connect MCP servers", error=str(e), exc_info=True)
            # Fallback: 빈 딕셔너리 반환
            return {}

    async def _load_agents(self):
        """에이전트 정의 로드 (.claude/agents/*.md 파싱)"""
        agents_dir = Path(".claude/agents")
        agent_files = {
            "orchestrator": "orchestrator.md",
            "external_scout": "external_scout.md",
            "interview_miner": "interview_miner.md",
            "voc_analyst": "voc_analyst.md",
            "scorecard_evaluator": "scorecard_evaluator.md",
            "brief_writer": "brief_writer.md",
            "confluence_sync": "confluence_sync.md",
            "governance": "governance.md",
        }

        if not agents_dir.exists():
            self.logger.warning(f"Agents directory not found: {agents_dir}")
            return

        for agent_id, filename in agent_files.items():
            file_path = agents_dir / filename

            try:
                if not file_path.exists():
                    self.logger.warning(f"Agent file not found: {file_path}")
                    continue

                # Markdown 파싱
                agent_def = await self._parse_agent_definition(file_path)
                config = AgentConfig(agent_id=agent_id)

                self.agents[agent_id] = {
                    "config": config,
                    "definition": agent_def,
                }

                self.logger.info(
                    f"Loaded agent: {agent_id}", tools=agent_def.tools, model=agent_def.model
                )

            except Exception as e:
                self.logger.error(f"Failed to load agent: {agent_id}", error=str(e), exc_info=True)

    async def _parse_agent_definition(self, file_path: Path) -> AgentDefinition:
        """Markdown 파일에서 AgentDefinition 생성"""
        content = file_path.read_text(encoding="utf-8")

        # 제목 추출 (첫 번째 # 헤더)
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1).strip() if title_match else file_path.stem

        # "## 역할" 섹션 추출
        role_match = re.search(r"##\s+역할\s*\n+(.*?)(?=\n##|\Z)", content, re.DOTALL)
        description = role_match.group(1).strip() if role_match else f"{title} agent"

        # 도구 추출
        tools = self._extract_tools_from_markdown(content)

        # 모델 추출
        model_str = self._extract_model_from_markdown(content) or "inherit"
        # AgentDefinition.model은 Literal['sonnet', 'opus', 'haiku', 'inherit'] | None 타입
        model_literal = cast(
            Literal["sonnet", "opus", "haiku", "inherit"] | None,
            model_str if model_str in ("sonnet", "opus", "haiku", "inherit") else "inherit",
        )

        return AgentDefinition(
            description=description,
            prompt=content,  # 전체 Markdown을 시스템 프롬프트로 사용
            tools=tools,
            model=model_literal,
        )

    def _extract_tools_from_markdown(self, content: str) -> list[str] | None:
        """Markdown의 설정 섹션에서 도구 목록 추출"""
        # "## 설정" 섹션의 JSON 블록 찾기
        config_match = re.search(r"```json\s*\n(\{.*?\})\s*\n```", content, re.DOTALL)

        if config_match:
            try:
                config = json.loads(config_match.group(1))

                # "tools" 또는 "allowed_tools" 키 찾기
                tools = config.get("tools") or config.get("allowed_tools")
                return tools if tools else None

            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse config JSON: {e}")

        return None  # None = 모든 도구 허용

    def _extract_model_from_markdown(self, content: str) -> str | None:
        """Markdown의 설정 섹션에서 모델 설정 추출"""
        config_match = re.search(r"```json\s*\n(\{.*?\})\s*\n```", content, re.DOTALL)

        if config_match:
            try:
                config = json.loads(config_match.group(1))
                return config.get("model")
            except json.JSONDecodeError:
                pass

        return None

    def _get_agent_definitions(self) -> dict[str, AgentDefinition]:
        """에이전트 정의 딕셔너리 반환"""
        return {
            agent_id: data["definition"]
            for agent_id, data in self.agents.items()
            if "definition" in data
        }

    async def create_session(self, workflow_id: str, input_data: dict[str, Any]) -> str:
        """세션 생성 (ClaudeSDKClient 인스턴스 포함)"""
        session_id = f"sess_{workflow_id}_{uuid.uuid4().hex[:8]}"

        # MCP 서버 설정
        mcp_servers = await self._connect_mcp_servers()

        # SDK 옵션
        options = ClaudeAgentOptions(
            model=self.model,
            mcp_servers=mcp_servers,
            allowed_tools=["Read", "Write", "Bash", "Glob", "Grep"],
            agents=self._get_agent_definitions(),
            cwd=os.getcwd(),
        )

        # SDK 클라이언트
        client = ClaudeSDKClient(options=options)

        self.sessions[session_id] = {
            "workflow_id": workflow_id,
            "input_data": input_data,
            "status": "created",
            "client": client,
            "options": options,
            "created_at": asyncio.get_event_loop().time(),
        }

        self.logger.info(f"Session created: {session_id}")
        return session_id

    async def resume_session(self, session_id: str) -> dict[str, Any]:
        """세션 재개"""
        if session_id not in self.sessions:
            raise ValueError(f"Session not found: {session_id}")

        session = self.sessions[session_id]
        session["status"] = "resumed"

        self.logger.info(f"Session resumed: {session_id}")
        return session

    async def _cleanup_old_sessions(self):
        """1시간 이상 된 세션 정리"""
        current_time = asyncio.get_event_loop().time()
        timeout = 3600  # 1시간

        to_delete = []
        for session_id, session in self.sessions.items():
            if current_time - session["created_at"] > timeout:
                # SDK 클라이언트 정리
                if "client" in session:
                    try:
                        await session["client"].disconnect()
                    except Exception as e:
                        self.logger.warning(
                            f"Failed to disconnect client for session: {session_id}", error=str(e)
                        )
                to_delete.append(session_id)

        for session_id in to_delete:
            del self.sessions[session_id]
            self.logger.info(f"Cleaned up session: {session_id}")

    async def run_workflow(
        self, workflow_id: str, input_data: dict[str, Any], session_id: str | None = None
    ) -> dict[str, Any]:
        """워크플로 실행"""
        self.logger.info(f"Running workflow: {workflow_id}")

        # 세션 생성/재개
        if session_id:
            await self.resume_session(session_id)
        else:
            session_id = await self.create_session(workflow_id, input_data)

        # 워크플로 라우팅
        workflow_handler = self._get_workflow_handler(workflow_id)

        if workflow_handler is None:
            raise ValueError(f"Unknown workflow: {workflow_id}")

        # 워크플로 실행
        result = await workflow_handler(input_data, session_id)

        # 세션 업데이트
        self.sessions[session_id]["status"] = "completed"
        self.sessions[session_id]["result"] = result

        return result

    def _get_workflow_handler(self, workflow_id: str):
        """워크플로 핸들러 반환"""
        handlers = {
            "WF-01": self._run_seminar_pipeline,
            "WF-02": self._run_interview_to_brief,
            "WF-03": self._run_voc_mining,
            "WF-04": self._run_inbound_triage,
            "WF-05": self._run_kpi_digest,
            "WF-06": self._run_confluence_sync,
        }
        return handlers.get(workflow_id)

    async def _run_seminar_pipeline(
        self, input_data: dict[str, Any], session_id: str
    ) -> dict[str, Any]:
        """WF-01: Seminar Pipeline"""
        self.logger.info("Running WF-01: Seminar Pipeline")

        from backend.agent_runtime.workflows.wf_seminar_pipeline import (
            SeminarInput,
            seminar_pipeline,
        )

        # 실제 워크플로 실행
        seminar_input = SeminarInput(**input_data)
        result = await seminar_pipeline.run(seminar_input)

        return {
            "workflow_id": "WF-01",
            "status": "completed",
            "activity": result.activity,
            "aar_template": result.aar_template,
            "signals": result.signals,
            "confluence_updated": result.confluence_live_doc_updated,
        }

    async def _run_interview_to_brief(
        self, input_data: dict[str, Any], session_id: str
    ) -> dict[str, Any]:
        """WF-02: Interview to Brief"""
        self.logger.info("Running WF-02: Interview to Brief")

        # 1. Interview Miner로 Signal 추출
        # 2. Scorecard Evaluator로 평가
        # 3. Brief Writer로 Brief 생성
        # 4. 승인 요청

        return {
            "workflow_id": "WF-02",
            "status": "pending_approval",
            "signal_id": None,
            "brief_id": None,
        }

    async def _run_voc_mining(self, input_data: dict[str, Any], session_id: str) -> dict[str, Any]:
        """WF-03: VoC Mining

        Args:
            input_data: 입력 데이터
                - with_events: 이벤트 발행 여부 (기본값: False)
                - with_db: DB 저장 여부 (기본값: False)
                - 기타 VoCInput 필드
            session_id: 세션 ID

        Returns:
            워크플로 실행 결과
        """
        self.logger.info("Running WF-03: VoC Mining")

        from backend.agent_runtime.workflows.wf_voc_mining import (
            VoCInput,
            VoCMiningPipeline,
            VoCMiningPipelineWithDB,
            VoCMiningPipelineWithEvents,
        )

        # VoC 입력 생성
        voc_input = VoCInput(
            data_source=input_data.get("data_source"),
            source_type=input_data.get("source_type", "text"),
            file_content=input_data.get("file_content"),
            api_data=input_data.get("api_data"),
            text_content=input_data.get("text_content"),
            play_id=input_data.get("play_id", "KT_Desk_V01_VoC"),
            source=input_data.get("source", "KT"),
            channel=input_data.get("channel", "데스크리서치"),
            min_frequency=input_data.get("min_frequency", 5),
            max_themes=input_data.get("max_themes", 5),
        )

        # 옵션 확인
        with_events = input_data.get("with_events", False)
        with_db = input_data.get("with_db", False)

        # 파이프라인 선택 및 실행
        if with_db:
            # DB 연동 버전 (이벤트 포함)
            from backend.agent_runtime.event_manager import (
                SessionEventManager,
                WorkflowEventEmitter,
            )
            from backend.database.session import SessionLocal

            event_manager = SessionEventManager.get_or_create(session_id)
            emitter = WorkflowEventEmitter(event_manager, run_id=f"WF-03-{session_id}")

            async with SessionLocal() as db:
                pipeline = VoCMiningPipelineWithDB(emitter, db)
                result = await pipeline.run(voc_input)

            return {
                "workflow_id": "WF-03",
                "status": "completed",
                "themes": result.themes,
                "signals": result.signals,
                "brief_candidates": result.brief_candidates,
                "summary": result.summary,
            }

        elif with_events:
            # 이벤트 발행 버전
            from backend.agent_runtime.event_manager import (
                SessionEventManager,
                WorkflowEventEmitter,
            )

            event_manager = SessionEventManager.get_or_create(session_id)
            emitter = WorkflowEventEmitter(event_manager, run_id=f"WF-03-{session_id}")

            pipeline_events = VoCMiningPipelineWithEvents(emitter)
            result = await pipeline_events.run(voc_input)

            return {
                "workflow_id": "WF-03",
                "status": "completed",
                "themes": result.themes,
                "signals": result.signals,
                "brief_candidates": result.brief_candidates,
                "summary": result.summary,
            }

        else:
            # 기본 버전
            pipeline_basic = VoCMiningPipeline()
            result = await pipeline_basic.run(voc_input)

            return {
                "workflow_id": "WF-03",
                "status": "completed",
                "themes": result.themes,
                "signals": result.signals,
                "brief_candidates": result.brief_candidates,
            }

    async def _run_inbound_triage(
        self, input_data: dict[str, Any], session_id: str
    ) -> dict[str, Any]:
        """WF-04: Inbound Triage"""
        self.logger.info("Running WF-04: Inbound Triage")
        return {"workflow_id": "WF-04", "status": "completed"}

    async def _run_kpi_digest(self, input_data: dict[str, Any], session_id: str) -> dict[str, Any]:
        """WF-05: KPI Digest"""
        self.logger.info("Running WF-05: KPI Digest")
        return {"workflow_id": "WF-05", "status": "completed"}

    async def _run_confluence_sync(
        self, input_data: dict[str, Any], session_id: str
    ) -> dict[str, Any]:
        """WF-06: Confluence Sync"""
        self.logger.info("Running WF-06: Confluence Sync")
        return {"workflow_id": "WF-06", "status": "completed"}


# 싱글톤 인스턴스
runtime = AgentRuntime()


async def get_runtime() -> AgentRuntime:
    """런타임 인스턴스 반환"""
    return runtime
