"""
D1 HTTP API Repositories

D1 데이터베이스와 통신하는 repository 클래스들
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from .client import d1_client


class D1SignalRepository:
    """Signal D1 Repository"""

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[dict], int]:
        """Signal 목록 조회"""
        offset = (page - 1) * page_size

        # Count query
        count_sql = "SELECT COUNT(*) as total FROM signals"
        if status:
            count_sql += " WHERE stage = ?"
            count_result = await d1_client.execute(count_sql, [status])
        else:
            count_result = await d1_client.execute(count_sql)

        total = count_result["results"][0]["total"] if count_result["results"] else 0

        # Data query
        sql = """
            SELECT id, activity_id, title, summary, pain_points, opportunities,
                   customer_segment, industry, stage, created_at, updated_at
            FROM signals
        """
        params: list[Any] = []

        if status:
            sql += " WHERE stage = ?"
            params.append(status)

        sql += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([page_size, offset])

        result = await d1_client.execute(sql, params)
        items = result.get("results", [])

        # 필드 매핑 (D1 -> Frontend)
        mapped_items = [self._map_to_frontend(item) for item in items]

        return mapped_items, total

    async def get_by_id(self, signal_id: str) -> dict | None:
        """Signal 단일 조회"""
        sql = """
            SELECT id, activity_id, title, summary, pain_points, opportunities,
                   customer_segment, industry, stage, created_at, updated_at
            FROM signals WHERE id = ?
        """
        result = await d1_client.execute(sql, [signal_id])
        items = result.get("results", [])

        if not items:
            return None

        return self._map_to_frontend(items[0])

    async def create(self, data: dict) -> dict:
        """Signal 생성"""
        signal_id = data.get("signal_id") or f"SIG-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(UTC).isoformat()

        sql = """
            INSERT INTO signals (id, activity_id, title, summary, pain_points,
                                 customer_segment, industry, stage, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = [
            signal_id,
            data.get("activity_id"),
            data["title"],
            data.get("proposed_value", ""),  # summary
            data.get("pain", ""),  # pain_points
            data.get("customer_segment"),
            data.get("industry"),
            "NEW",  # stage
            now,
            now,
        ]

        await d1_client.execute(sql, params)

        return await self.get_by_id(signal_id)  # type: ignore

    async def update_status(self, signal_id: str, status: str) -> dict | None:
        """Signal 상태 업데이트"""
        now = datetime.now(UTC).isoformat()
        sql = "UPDATE signals SET stage = ?, updated_at = ? WHERE id = ?"
        await d1_client.execute(sql, [status, now, signal_id])

        return await self.get_by_id(signal_id)

    async def get_stats(self) -> dict:
        """Signal 통계"""
        sql = """
            SELECT stage, COUNT(*) as count
            FROM signals
            GROUP BY stage
        """
        result = await d1_client.execute(sql)
        items = result.get("results", [])

        by_status = {item["stage"]: item["count"] for item in items}
        total = sum(by_status.values())

        return {
            "total": total,
            "by_status": by_status,
            "by_source": {},  # D1 스키마에 source 없음
        }

    def _map_to_frontend(self, item: dict) -> dict:
        """D1 스키마 -> Frontend 타입 매핑"""
        return {
            "signal_id": item["id"],
            "title": item["title"],
            "source": "대외",  # 기본값
            "channel": "데스크리서치",  # 기본값
            "play_id": item.get("activity_id") or "UNKNOWN",
            "customer_segment": item.get("customer_segment"),
            "pain": item.get("pain_points") or "",
            "proposed_value": item.get("summary"),
            "status": self._map_stage_to_status(item.get("stage", "S0")),
            "owner": None,
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }

    def _map_stage_to_status(self, stage: str) -> str:
        """D1 stage -> Frontend status 매핑"""
        stage_map = {
            "S0": "NEW",
            "S1": "SCORING",
            "S2": "SCORED",
            "S3": "BRIEF_CREATED",
        }
        return stage_map.get(stage, "NEW")


class D1ScorecardRepository:
    """Scorecard D1 Repository"""

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        decision: str | None = None,
        min_score: int | None = None,
        max_score: int | None = None,
    ) -> tuple[list[dict], int]:
        """Scorecard 목록 조회"""
        offset = (page - 1) * page_size

        # Build WHERE clause
        conditions = []
        params: list[Any] = []

        if decision:
            conditions.append("recommendation = ?")
            params.append(decision)
        if min_score is not None:
            conditions.append("total_score >= ?")
            params.append(min_score)
        if max_score is not None:
            conditions.append("total_score <= ?")
            params.append(max_score)

        where_clause = " WHERE " + " AND ".join(conditions) if conditions else ""

        # Count query
        count_sql = f"SELECT COUNT(*) as total FROM scorecards{where_clause}"
        count_result = await d1_client.execute(count_sql, params.copy())
        total = count_result["results"][0]["total"] if count_result["results"] else 0

        # Data query
        sql = f"""
            SELECT s.*, sig.title as signal_title
            FROM scorecards s
            LEFT JOIN signals sig ON s.signal_id = sig.id
            {where_clause}
            ORDER BY s.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])

        result = await d1_client.execute(sql, params)
        items = result.get("results", [])

        mapped_items = [self._map_to_frontend(item) for item in items]
        return mapped_items, total

    async def get_by_signal_id(self, signal_id: str) -> dict | None:
        """Signal ID로 Scorecard 조회"""
        sql = """
            SELECT s.*, sig.title as signal_title
            FROM scorecards s
            LEFT JOIN signals sig ON s.signal_id = sig.id
            WHERE s.signal_id = ?
        """
        result = await d1_client.execute(sql, [signal_id])
        items = result.get("results", [])

        if not items:
            return None

        return self._map_to_frontend(items[0])

    async def create(self, data: dict) -> dict:
        """Scorecard 생성"""
        scorecard_id = f"SC-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(UTC).isoformat()

        sql = """
            INSERT INTO scorecards (id, signal_id, total_score, market_fit, kt_synergy,
                                    technical_feasibility, urgency, revenue_potential,
                                    recommendation, evaluator_notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = [
            scorecard_id,
            data["signal_id"],
            data.get("total_score", 0),
            data.get("market_fit", 0),
            data.get("kt_synergy", 0),
            data.get("technical_feasibility", 0),
            data.get("urgency", 0),
            data.get("revenue_potential", 0),
            data.get("recommendation", "HOLD"),
            data.get("evaluator_notes"),
            now,
        ]

        await d1_client.execute(sql, params)
        return await self.get_by_signal_id(data["signal_id"])  # type: ignore

    async def get_distribution(self) -> dict:
        """점수 분포 통계"""
        sql = """
            SELECT
                recommendation,
                COUNT(*) as count,
                AVG(total_score) as avg_score
            FROM scorecards
            GROUP BY recommendation
        """
        result = await d1_client.execute(sql)
        items = result.get("results", [])

        total_sql = "SELECT AVG(total_score) as avg FROM scorecards"
        total_result = await d1_client.execute(total_sql)
        avg_score = total_result["results"][0]["avg"] if total_result["results"] else 0

        return {
            "by_decision": {item["recommendation"]: item["count"] for item in items},
            "avg_score": avg_score or 0,
            "total": sum(item["count"] for item in items),
        }

    def _map_to_frontend(self, item: dict) -> dict:
        """D1 스키마 -> Frontend 타입 매핑"""
        return {
            "scorecard_id": item["id"],
            "signal_id": item["signal_id"],
            "signal_title": item.get("signal_title", ""),
            "total_score": item.get("total_score", 0),
            "dimensions": {
                "market_fit": {"score": item.get("market_fit", 0), "weight": 25},
                "kt_synergy": {"score": item.get("kt_synergy", 0), "weight": 20},
                "technical_feasibility": {
                    "score": item.get("technical_feasibility", 0),
                    "weight": 20,
                },
                "urgency": {"score": item.get("urgency", 0), "weight": 15},
                "revenue_potential": {"score": item.get("revenue_potential", 0), "weight": 20},
            },
            "recommendation": {
                "decision": item.get("recommendation", "HOLD"),
                "rationale": item.get("evaluator_notes") or "",
            },
            "created_at": item.get("created_at"),
        }


class D1BriefRepository:
    """Brief D1 Repository"""

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[dict], int]:
        """Brief 목록 조회"""
        offset = (page - 1) * page_size

        where_clause = ""
        params: list[Any] = []
        if status:
            where_clause = " WHERE status = ?"
            params.append(status)

        # Count query
        count_sql = f"SELECT COUNT(*) as total FROM briefs{where_clause}"
        count_result = await d1_client.execute(count_sql, params.copy())
        total = count_result["results"][0]["total"] if count_result["results"] else 0

        # Data query
        sql = f"""
            SELECT * FROM briefs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])

        result = await d1_client.execute(sql, params)
        items = result.get("results", [])

        mapped_items = [self._map_to_frontend(item) for item in items]
        return mapped_items, total

    async def get_by_id(self, brief_id: str) -> dict | None:
        """Brief 단일 조회"""
        sql = "SELECT * FROM briefs WHERE id = ?"
        result = await d1_client.execute(sql, [brief_id])
        items = result.get("results", [])

        if not items:
            return None

        return self._map_to_frontend(items[0])

    async def create(self, data: dict) -> dict:
        """Brief 생성"""
        brief_id = f"BR-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(UTC).isoformat()

        sql = """
            INSERT INTO briefs (id, signal_id, scorecard_id, title, executive_summary,
                               problem_statement, proposed_solution, target_customer,
                               business_model, competitive_advantage, next_steps,
                               status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = [
            brief_id,
            data.get("signal_id"),
            data.get("scorecard_id"),
            data["title"],
            data.get("executive_summary", ""),
            data.get("problem_statement", ""),
            data.get("proposed_solution", ""),
            data.get("target_customer", ""),
            data.get("business_model", ""),
            data.get("competitive_advantage", ""),
            data.get("next_steps", ""),
            "DRAFT",
            now,
            now,
        ]

        await d1_client.execute(sql, params)
        return await self.get_by_id(brief_id)  # type: ignore

    async def update_status(self, brief_id: str, status: str) -> dict | None:
        """Brief 상태 업데이트"""
        now = datetime.now(UTC).isoformat()
        sql = "UPDATE briefs SET status = ?, updated_at = ? WHERE id = ?"
        await d1_client.execute(sql, [status, now, brief_id])

        return await self.get_by_id(brief_id)

    def _map_to_frontend(self, item: dict) -> dict:
        """D1 스키마 -> Frontend 타입 매핑"""
        return {
            "brief_id": item["id"],
            "signal_id": item.get("signal_id", ""),
            "title": item["title"],
            "customer": {
                "segment": item.get("target_customer", ""),
                "buyer_role": "",
                "account": None,
            },
            "problem": {
                "pain": item.get("problem_statement", ""),
                "why_now": "",
            },
            "solution_hypothesis": {
                "approach": item.get("proposed_solution", ""),
            },
            "kpis": [],
            "validation_plan": {
                "method": "5DAY_SPRINT",
                "timebox_days": 5,
                "questions": [],
            },
            "risks": [],
            "status": item.get("status", "DRAFT"),
            "owner": "",
            "confluence_url": None,
            "created_at": item.get("created_at"),
            "updated_at": item.get("updated_at"),
        }


class D1PlayRepository:
    """Play D1 Repository"""

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[dict], int]:
        """Play 목록 조회"""
        offset = (page - 1) * page_size

        where_clause = ""
        params: list[Any] = []
        if status:
            where_clause = " WHERE status = ?"
            params.append(status)

        # Count query
        count_sql = f"SELECT COUNT(*) as total FROM plays{where_clause}"
        count_result = await d1_client.execute(count_sql, params.copy())
        total = count_result["results"][0]["total"] if count_result["results"] else 0

        # Data query
        sql = f"""
            SELECT * FROM plays
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([page_size, offset])

        result = await d1_client.execute(sql, params)
        items = result.get("results", [])

        mapped_items = [self._map_to_frontend(item) for item in items]
        return mapped_items, total

    async def get_by_id(self, play_id: str) -> dict | None:
        """Play 단일 조회"""
        sql = "SELECT * FROM plays WHERE id = ?"
        result = await d1_client.execute(sql, [play_id])
        items = result.get("results", [])

        if not items:
            return None

        return self._map_to_frontend(items[0])

    async def get_kpi_digest(self, period: str = "week") -> dict:
        """KPI 다이제스트 - 프론트엔드 KPIDigest 인터페이스에 맞춤"""
        # Play 통계
        play_sql = """
            SELECT
                COUNT(*) as total_plays,
                COALESCE(SUM(activity_count), 0) as total_activities
            FROM plays
        """
        play_result = await d1_client.execute(play_sql)
        play_item = play_result["results"][0] if play_result["results"] else {}

        # Signal 통계
        signal_sql = "SELECT COUNT(*) as total FROM signals"
        signal_result = await d1_client.execute(signal_sql)
        signal_count = signal_result["results"][0]["total"] if signal_result["results"] else 0

        # Brief 통계
        brief_sql = "SELECT COUNT(*) as total FROM briefs"
        brief_result = await d1_client.execute(brief_sql)
        brief_count = brief_result["results"][0]["total"] if brief_result["results"] else 0

        # S2 단계 Signal 수 (stage = 'S2')
        s2_sql = "SELECT COUNT(*) as total FROM signals WHERE stage = 'S2'"
        s2_result = await d1_client.execute(s2_sql)
        s2_count = s2_result["results"][0]["total"] if s2_result["results"] else 0

        # PoC 목표값
        targets = {
            "activity_target": 20,
            "signal_target": 30,
            "brief_target": 6,
            "s2_target": "2~4",
        }

        return {
            "period": period,
            "activity_actual": play_item.get("total_activities", 0) or 0,
            "activity_target": targets["activity_target"],
            "signal_actual": signal_count,
            "signal_target": targets["signal_target"],
            "brief_actual": brief_count,
            "brief_target": targets["brief_target"],
            "s2_actual": s2_count,
            "s2_target": targets["s2_target"],
            "avg_signal_to_brief_days": 0,  # TODO: 실제 리드타임 계산
            "avg_brief_to_s2_days": 0,  # TODO: 실제 리드타임 계산
        }

    async def get_kpi_alerts(self) -> dict:
        """KPI 알림"""
        return {
            "alerts": [],
            "red_plays": [],
            "overdue_briefs": [],
        }

    def _map_to_frontend(self, item: dict) -> dict:
        """D1 스키마 -> Frontend 타입 매핑"""
        # D1 status -> G/Y/R 매핑
        status_map = {
            "active": "G",
            "at_risk": "Y",
            "critical": "R",
        }
        status = status_map.get(item.get("status", "active"), "G")

        return {
            "play_id": item["id"],
            "play_name": item.get("name", ""),
            "status": status,
            "owner": item.get("owner"),
            "confluence_live_doc_url": None,
            "activity_qtd": item.get("activity_count", 0),
            "signal_qtd": 0,
            "brief_qtd": 0,
            "s2_qtd": 0,
            "s3_qtd": 0,
            "next_action": None,
            "due_date": None,
            "notes": None,
            "last_activity_date": item.get("last_activity_at"),
            "last_updated": item.get("updated_at"),
        }


# 싱글톤 인스턴스
signal_d1_repo = D1SignalRepository()
scorecard_d1_repo = D1ScorecardRepository()
brief_d1_repo = D1BriefRepository()
play_d1_repo = D1PlayRepository()
