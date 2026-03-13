"""Anthropic API Agent Adapter — 멀티턴 대화 + 도구 호출 지원"""

import json
import os
from typing import Any

import structlog

from backend.evals.adapters.base import AdapterResult, AgentAdapterBase
from backend.evals.models.configs import AgentConfig

logger = structlog.get_logger()

DEFAULT_MODEL = "claude-sonnet-4-20250514"

# ──────────────────────────────────────────────
# 도구 스키마 매핑 (실제 MCP 도구 정의 기반)
# ──────────────────────────────────────────────
_TOOL_SCHEMA_MAP: dict[str, dict[str, Any]] = {
    # === Confluence 도구 (7개) ===
    "confluence.search_pages": {
        "description": "Confluence 페이지 검색",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "검색 키워드"},
                "limit": {"type": "integer", "description": "최대 결과 수"},
            },
            "required": ["query"],
        },
    },
    "confluence.get_page": {
        "description": "Confluence 페이지 조회",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "페이지 ID"},
            },
            "required": ["page_id"],
        },
    },
    "confluence.create_page": {
        "description": "Confluence 페이지 생성",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "페이지 제목"},
                "body_md": {"type": "string", "description": "마크다운 본문"},
                "parent_page_id": {"type": "string", "description": "부모 페이지 ID"},
            },
            "required": ["title", "body_md", "parent_page_id"],
        },
    },
    "confluence.update_page": {
        "description": "Confluence 페이지 업데이트",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "페이지 ID"},
                "body_md": {"type": "string", "description": "마크다운 본문"},
                "title": {"type": "string", "description": "페이지 제목"},
            },
            "required": ["page_id", "body_md"],
        },
    },
    "confluence.append_to_page": {
        "description": "Confluence 페이지 하단에 내용 추가",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "페이지 ID"},
                "append_md": {"type": "string", "description": "추가할 마크다운 내용"},
            },
            "required": ["page_id", "append_md"],
        },
    },
    "confluence.add_labels": {
        "description": "Confluence 페이지에 라벨 추가",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "페이지 ID"},
                "labels": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "추가할 라벨 목록",
                },
            },
            "required": ["page_id", "labels"],
        },
    },
    "confluence.increment_play_activity_count": {
        "description": "Play DB Activity 카운트 증가",
        "input_schema": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string", "description": "Play DB 페이지 ID"},
                "play_id": {"type": "string", "description": "Play 항목 ID"},
            },
            "required": ["page_id", "play_id"],
        },
    },
    # === Teams 도구 (5개) ===
    "teams.send_message": {
        "description": "Teams 채널에 메시지 전송",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "메시지 본문"},
                "title": {"type": "string", "description": "메시지 제목"},
            },
            "required": ["text"],
        },
    },
    "teams.send_notification": {
        "description": "Teams 알림 전송",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "알림 내용"},
                "title": {"type": "string", "description": "알림 제목"},
                "level": {
                    "type": "string",
                    "description": "알림 수준 (info/warning/error)",
                },
            },
            "required": ["text"],
        },
    },
    "teams.send_card": {
        "description": "Teams Adaptive Card 전송",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "카드 제목"},
                "subtitle": {"type": "string", "description": "카드 부제목"},
                "text": {"type": "string", "description": "카드 본문"},
                "buttons": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "액션 버튼 목록",
                },
            },
            "required": ["title", "text"],
        },
    },
    "teams.request_approval": {
        "description": "Teams 승인 요청 전송",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "승인 요청 내용"},
                "title": {"type": "string", "description": "승인 요청 제목"},
                "approvers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "승인자 목록",
                },
            },
            "required": ["text", "approvers"],
        },
    },
    "teams.send_kpi_digest": {
        "description": "Teams KPI 다이제스트 전송",
        "input_schema": {
            "type": "object",
            "properties": {
                "metrics": {"type": "object", "description": "KPI 지표 딕셔너리"},
                "period": {"type": "string", "description": "기간 (예: 2026-W11)"},
            },
            "required": ["metrics", "period"],
        },
    },
    # === Slack 도구 (5개) ===
    "slack.send_message": {
        "description": "Slack 채널에 메시지 전송",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "메시지 본문"},
                "channel": {"type": "string", "description": "채널명 또는 ID"},
            },
            "required": ["text", "channel"],
        },
    },
    "slack.send_notification": {
        "description": "Slack 알림 전송",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "알림 내용"},
                "channel": {"type": "string", "description": "채널명 또는 ID"},
                "level": {
                    "type": "string",
                    "description": "알림 수준 (info/warning/error)",
                },
            },
            "required": ["text", "channel"],
        },
    },
    "slack.send_blocks": {
        "description": "Slack Block Kit 메시지 전송",
        "input_schema": {
            "type": "object",
            "properties": {
                "blocks": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "Block Kit 블록 배열",
                },
                "channel": {"type": "string", "description": "채널명 또는 ID"},
            },
            "required": ["blocks", "channel"],
        },
    },
    "slack.request_approval": {
        "description": "Slack 승인 요청 전송",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "승인 요청 내용"},
                "approvers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "승인자 목록",
                },
            },
            "required": ["text", "approvers"],
        },
    },
    "slack.send_kpi_digest": {
        "description": "Slack KPI 다이제스트 전송",
        "input_schema": {
            "type": "object",
            "properties": {
                "metrics": {"type": "object", "description": "KPI 지표 딕셔너리"},
                "period": {"type": "string", "description": "기간 (예: 2026-W11)"},
            },
            "required": ["metrics", "period"],
        },
    },
}

# ──────────────────────────────────────────────
# 도구별 시뮬레이션 응답 매핑 (17개 전체)
# ──────────────────────────────────────────────
_TOOL_SIMULATION_DEFAULTS: dict[str, dict[str, Any]] = {
    # === Confluence ===
    "confluence_search_pages": {
        "results": [
            {"page_id": "12345", "title": "검색 결과 1", "status": "current"},
            {"page_id": "12347", "title": "검색 결과 2", "status": "current"},
        ],
        "total": 2,
    },
    "confluence_get_page": {
        "page_id": "12345",
        "title": "테스트 페이지",
        "content": "페이지 본문 내용입니다.",
        "version": 3,
        "status": "current",
    },
    "confluence_create_page": {
        "page_id": "12346",
        "title": "새 페이지",
        "url": "https://wiki.example.com/pages/12346",
        "version": 1,
        "status": "created",
    },
    "confluence_update_page": {
        "page_id": "12345",
        "title": "업데이트된 페이지",
        "version": 4,
        "status": "updated",
    },
    "confluence_append_to_page": {
        "page_id": "12345",
        "version": 5,
        "status": "appended",
    },
    "confluence_add_labels": {
        "page_id": "12345",
        "labels": ["signal", "brief"],
        "status": "labels_added",
    },
    "confluence_increment_play_activity_count": {
        "page_id": "12345",
        "play_id": "PLAY-001",
        "activity_count": 15,
        "status": "incremented",
    },
    # === Teams ===
    "teams_send_message": {
        "message_id": "msg-001",
        "status": "sent",
        "channel": "ax-bd-general",
    },
    "teams_send_notification": {
        "message_id": "notif-001",
        "status": "sent",
        "level": "info",
    },
    "teams_send_card": {
        "message_id": "card-001",
        "status": "sent",
        "card_type": "adaptive_card",
    },
    "teams_request_approval": {
        "approval_id": "appr-001",
        "status": "pending",
        "approvers": ["manager@example.com"],
    },
    "teams_send_kpi_digest": {
        "message_id": "kpi-001",
        "status": "sent",
        "period": "2026-W11",
    },
    # === Slack ===
    "slack_send_message": {
        "message_id": "slack-msg-001",
        "ts": "1741868400.000100",
        "status": "sent",
        "channel": "#ax-bd-general",
    },
    "slack_send_notification": {
        "message_id": "slack-notif-001",
        "ts": "1741868401.000200",
        "status": "sent",
        "level": "info",
    },
    "slack_send_blocks": {
        "message_id": "slack-blocks-001",
        "ts": "1741868402.000300",
        "status": "sent",
        "channel": "#ax-bd-general",
    },
    "slack_request_approval": {
        "approval_id": "slack-appr-001",
        "status": "pending",
        "approvers": ["manager"],
    },
    "slack_send_kpi_digest": {
        "message_id": "slack-kpi-001",
        "ts": "1741868403.000400",
        "status": "sent",
        "period": "2026-W11",
    },
}


class AnthropicAdapter(AgentAdapterBase):
    """Anthropic API를 직접 호출하는 어댑터 (멀티턴 + 도구 호출)"""

    def __init__(self) -> None:
        import anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY 환경변수가 설정되지 않았습니다")
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def run(self, prompt: str, agent_config: AgentConfig) -> AdapterResult:
        model = agent_config.model or DEFAULT_MODEL
        max_turns = agent_config.max_turns
        tools = self._build_tools(agent_config.tools_allowed)

        logger.info(
            "Anthropic API 멀티턴 시작",
            model=model,
            prompt_length=len(prompt),
            max_turns=max_turns,
            tools_count=len(tools),
        )

        system_prompt = agent_config.system_prompt_override or self._build_system_prompt(
            agent_config
        )

        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        all_messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]
        all_tool_calls: list[dict[str, Any]] = []

        total_input_tokens = 0
        total_output_tokens = 0
        n_turns = 0
        last_stop_reason: str | None = None

        create_kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": 4096,
            "system": system_prompt,
        }
        if tools:
            create_kwargs["tools"] = tools

        for _turn in range(max_turns):
            response = await self._client.messages.create(
                messages=messages,
                **create_kwargs,
            )

            # 토큰 누적
            total_input_tokens += response.usage.input_tokens
            total_output_tokens += response.usage.output_tokens
            n_turns += 1
            last_stop_reason = response.stop_reason

            # assistant 메시지 직렬화 (content 블록 → 딕셔너리)
            assistant_content = self._serialize_content(response.content)
            assistant_msg: dict[str, Any] = {
                "role": "assistant",
                "content": assistant_content,
            }
            messages.append(assistant_msg)
            all_messages.append(assistant_msg)

            # tool_use 블록 추출 및 처리
            tool_use_blocks = [b for b in response.content if b.type == "tool_use"]

            if response.stop_reason != "tool_use" or not tool_use_blocks:
                # end_turn 또는 도구 호출 없음 → 루프 종료
                break

            # 도구 호출 기록 + tool_result 메시지 생성
            tool_results: list[dict[str, Any]] = []
            for block in tool_use_blocks:
                all_tool_calls.append(
                    {
                        "tool_name": block.name,
                        "tool_input": block.input,
                        "tool_use_id": block.id,
                    }
                )

                sim_result = self._simulate_tool_result(block.name, block.input)
                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(sim_result, ensure_ascii=False),
                    }
                )

            tool_result_msg: dict[str, Any] = {
                "role": "user",
                "content": tool_results,
            }
            messages.append(tool_result_msg)
            all_messages.append(tool_result_msg)

            logger.debug(
                "도구 호출 턴 완료",
                turn=n_turns,
                tool_calls=[b.name for b in tool_use_blocks],
            )

        # 최종 텍스트 추출 (마지막 assistant 메시지에서)
        output_text = self._extract_text(response.content)
        total_tokens = total_input_tokens + total_output_tokens
        cost_usd = self._estimate_cost(model, total_input_tokens, total_output_tokens)

        logger.info(
            "Anthropic API 멀티턴 완료",
            model=model,
            n_turns=n_turns,
            tool_calls_count=len(all_tool_calls),
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            cost_usd=f"${cost_usd:.4f}",
            stop_reason=last_stop_reason,
        )

        return AdapterResult(
            success=True,
            output=output_text,
            messages=all_messages,
            n_turns=n_turns,
            cost_usd=cost_usd,
            total_tokens=total_tokens,
            input_tokens=total_input_tokens,
            output_tokens=total_output_tokens,
            tool_calls=all_tool_calls,
            model=model,
            stop_reason=last_stop_reason,
        )

    @property
    def adapter_name(self) -> str:
        return "anthropic"

    def _build_tools(self, tools_allowed: list[str]) -> list[dict[str, Any]]:
        """tools_allowed 리스트에서 Anthropic API 도구 스키마 생성 (MCP 정의 기반)"""
        if not tools_allowed:
            return []

        generic_schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "입력 파라미터"},
            },
            "required": ["query"],
        }

        tools: list[dict[str, Any]] = []
        for tool_name in tools_allowed:
            api_name = tool_name.replace(".", "_")
            schema_entry = _TOOL_SCHEMA_MAP.get(tool_name)
            if schema_entry:
                tools.append(
                    {
                        "name": api_name,
                        "description": schema_entry["description"],
                        "input_schema": schema_entry["input_schema"],
                    }
                )
            else:
                tools.append(
                    {
                        "name": api_name,
                        "description": f"{tool_name} 도구",
                        "input_schema": generic_schema,
                    }
                )
        return tools

    def _simulate_tool_result(
        self, tool_name: str, tool_input: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """도구 이름 + 입력 기반 시뮬레이션 응답 반환"""
        defaults = _TOOL_SIMULATION_DEFAULTS.get(tool_name)
        if defaults is None:
            return {"status": "ok", "result": "시뮬레이션 결과"}

        result = dict(defaults)

        # tool_input이 있으면 응답에 반영
        if tool_input:
            for key in ("page_id", "play_id", "title", "channel", "level", "period"):
                if key in tool_input:
                    result[key] = tool_input[key]
            if "labels" in tool_input and isinstance(tool_input["labels"], list):
                result["labels"] = tool_input["labels"]
            if "approvers" in tool_input and isinstance(tool_input["approvers"], list):
                result["approvers"] = tool_input["approvers"]
            if "query" in tool_input and "results" in result:
                for item in result["results"]:
                    if isinstance(item, dict) and "title" not in tool_input:
                        item["title"] = f"{tool_input['query']} 결과"

        return result

    def _serialize_content(self, content: Any) -> list[dict[str, Any]]:
        """응답 content 블록을 직렬화 가능한 딕셔너리 리스트로 변환"""
        serialized: list[dict[str, Any]] = []
        for block in content:
            if block.type == "text":
                serialized.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                serialized.append(
                    {
                        "type": "tool_use",
                        "id": block.id,
                        "name": block.name,
                        "input": block.input,
                    }
                )
        return serialized

    def _extract_text(self, content: Any) -> str:
        """content 블록에서 텍스트만 추출"""
        parts: list[str] = []
        for block in content:
            if block.type == "text":
                parts.append(block.text)
        return "".join(parts)

    def _build_system_prompt(self, config: AgentConfig) -> str:
        parts = [
            "당신은 AX Discovery Portal의 에이전트입니다.",
        ]
        if config.agent_id:
            parts.append(f"역할: {config.agent_id}")
        if config.tools_allowed:
            parts.append(f"사용 가능 도구: {', '.join(config.tools_allowed)}")
        return "\n".join(parts)

    def _estimate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """모델별 토큰 비용 추정 (USD)"""
        # 2025-05 기준 가격
        rates = {
            "claude-sonnet-4-20250514": (3.0 / 1_000_000, 15.0 / 1_000_000),
            "claude-opus-4-20250514": (15.0 / 1_000_000, 75.0 / 1_000_000),
            "claude-haiku-3-5-20241022": (0.80 / 1_000_000, 4.0 / 1_000_000),
        }
        input_rate, output_rate = rates.get(model, (3.0 / 1_000_000, 15.0 / 1_000_000))
        return input_tokens * input_rate + output_tokens * output_rate
