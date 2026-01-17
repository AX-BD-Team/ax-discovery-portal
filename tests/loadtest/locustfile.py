"""
AX Discovery Portal - 부하 테스트

Locust 기반 API 부하 테스트 시나리오

실행 방법:
    # 웹 UI 모드 (기본)
    locust -f tests/loadtest/locustfile.py --host=http://localhost:8000

    # 헤드리스 모드 (CI/CD용)
    locust -f tests/loadtest/locustfile.py --host=http://localhost:8000 \
           --headless -u 10 -r 2 -t 60s --html=loadtest_report.html

    # 특정 사용자 클래스만 실행
    locust -f tests/loadtest/locustfile.py --host=http://localhost:8000 \
           ApiUser ReadOnlyUser

옵션:
    -u: 동시 사용자 수
    -r: 초당 사용자 증가율 (spawn rate)
    -t: 테스트 시간 (예: 60s, 5m, 1h)
    --html: HTML 리포트 출력 파일
"""

import random
import uuid
from datetime import datetime

from locust import HttpUser, between, task


class HealthCheckUser(HttpUser):
    """헬스체크 전용 사용자 - 높은 빈도로 /health, /ready 호출"""

    weight = 1  # 상대적 가중치 (낮음)
    wait_time = between(0.5, 1)  # 0.5~1초 간격

    @task(3)
    def health_check(self):
        """Liveness probe"""
        self.client.get("/health", name="/health")

    @task(1)
    def ready_check(self):
        """Readiness probe"""
        self.client.get("/ready", name="/ready")


class ReadOnlyUser(HttpUser):
    """읽기 전용 사용자 - 조회 API 위주"""

    weight = 3  # 상대적 가중치 (중간)
    wait_time = between(1, 3)  # 1~3초 간격

    @task(5)
    def get_signals(self):
        """Signal 목록 조회"""
        self.client.get(
            "/api/inbox/signals",
            params={"limit": 20, "offset": 0},
            name="/api/inbox/signals",
        )

    @task(3)
    def get_scorecards(self):
        """Scorecard 목록 조회"""
        self.client.get(
            "/api/scorecard",
            params={"limit": 10},
            name="/api/scorecard",
        )

    @task(3)
    def get_briefs(self):
        """Brief 목록 조회"""
        self.client.get(
            "/api/briefs",
            params={"limit": 10},
            name="/api/briefs",
        )

    @task(2)
    def get_plays(self):
        """Play 대시보드 조회"""
        self.client.get(
            "/api/plays",
            params={"limit": 10},
            name="/api/plays",
        )

    @task(1)
    def get_entities(self):
        """Entity 목록 조회"""
        self.client.get(
            "/api/ontology/entities",
            params={"limit": 20},
            name="/api/ontology/entities",
        )

    @task(1)
    def search_semantic(self):
        """시맨틱 검색"""
        queries = [
            "AI 기반 고객 서비스",
            "클라우드 마이그레이션",
            "데이터 분석 플랫폼",
            "보안 솔루션",
            "디지털 트랜스포메이션",
        ]
        self.client.post(
            "/api/search/semantic",
            json={"query": random.choice(queries), "top_k": 5},
            name="/api/search/semantic",
        )


class ApiUser(HttpUser):
    """일반 API 사용자 - 읽기/쓰기 혼합"""

    weight = 5  # 상대적 가중치 (높음)
    wait_time = between(2, 5)  # 2~5초 간격

    def on_start(self):
        """사용자 세션 시작 시 실행"""
        self.signal_ids: list[str] = []
        self.scorecard_ids: list[str] = []

    @task(10)
    def get_signals(self):
        """Signal 목록 조회 (가장 빈번)"""
        response = self.client.get(
            "/api/inbox/signals",
            params={"limit": 20, "offset": 0},
            name="/api/inbox/signals",
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("items"):
                self.signal_ids = [item["id"] for item in data["items"][:5]]

    @task(5)
    def get_signal_detail(self):
        """Signal 상세 조회"""
        if self.signal_ids:
            signal_id = random.choice(self.signal_ids)
            self.client.get(
                f"/api/inbox/signals/{signal_id}",
                name="/api/inbox/signals/[id]",
            )

    @task(3)
    def create_activity(self):
        """Activity 생성"""
        activity = {
            "source_channel": random.choice(
                ["desk_research", "internal_activity", "sales_pm", "inbound", "outbound"]
            ),
            "source_origin": random.choice(["KT", "그룹사", "외부"]),
            "title": f"부하 테스트 Activity {uuid.uuid4().hex[:8]}",
            "summary": "Locust 부하 테스트에서 생성된 테스트 Activity입니다.",
            "raw_content": "테스트 콘텐츠",
            "metadata": {
                "test": True,
                "created_at": datetime.now().isoformat(),
            },
        }
        self.client.post(
            "/api/inbox/activities",
            json=activity,
            name="/api/inbox/activities [POST]",
        )

    @task(3)
    def get_scorecards(self):
        """Scorecard 목록 조회"""
        response = self.client.get(
            "/api/scorecard",
            params={"limit": 10},
            name="/api/scorecard",
        )
        if response.status_code == 200:
            data = response.json()
            if data.get("items"):
                self.scorecard_ids = [item["id"] for item in data["items"][:3]]

    @task(2)
    def get_scorecard_detail(self):
        """Scorecard 상세 조회"""
        if self.scorecard_ids:
            scorecard_id = random.choice(self.scorecard_ids)
            self.client.get(
                f"/api/scorecard/{scorecard_id}",
                name="/api/scorecard/[id]",
            )

    @task(2)
    def get_briefs(self):
        """Brief 목록 조회"""
        self.client.get(
            "/api/briefs",
            params={"limit": 10},
            name="/api/briefs",
        )

    @task(1)
    def get_plays(self):
        """Play 대시보드 조회"""
        self.client.get(
            "/api/plays",
            params={"limit": 10},
            name="/api/plays",
        )


class WorkflowUser(HttpUser):
    """워크플로 실행 사용자 - 무거운 작업"""

    weight = 1  # 상대적 가중치 (낮음 - 무거운 작업)
    wait_time = between(10, 30)  # 10~30초 간격 (긴 간격)

    @task(2)
    def run_triage(self):
        """WF-04 Inbound Triage 실행"""
        intake = {
            "company_name": f"테스트기업_{uuid.uuid4().hex[:6]}",
            "contact_name": "테스트담당자",
            "contact_email": "test@example.com",
            "inquiry_type": random.choice(["partnership", "product_inquiry", "technical_support"]),
            "description": "부하 테스트용 인바운드 문의입니다. AI 기반 솔루션에 관심이 있습니다.",
            "urgency": random.choice(["low", "normal", "urgent"]),
        }
        self.client.post(
            "/api/workflows/triage",
            json=intake,
            name="/api/workflows/triage [POST]",
        )

    @task(1)
    def preview_voc(self):
        """WF-03 VoC Mining 미리보기"""
        voc_data = {
            "source": "test",
            "content": "AI 서비스 품질 개선이 필요합니다. 응답 속도가 느립니다.",
            "format": "text",
        }
        self.client.post(
            "/api/workflows/voc-mining/preview",
            json=voc_data,
            name="/api/workflows/voc-mining/preview [POST]",
        )


class BurstUser(HttpUser):
    """버스트 사용자 - 순간적으로 높은 부하 생성"""

    weight = 1  # 상대적 가중치 (낮음)
    wait_time = between(0.1, 0.5)  # 매우 짧은 간격

    @task
    def burst_health(self):
        """빠른 헬스체크 호출"""
        self.client.get("/health", name="/health [burst]")

    @task
    def burst_signals(self):
        """빠른 Signal 조회"""
        self.client.get(
            "/api/inbox/signals",
            params={"limit": 5},
            name="/api/inbox/signals [burst]",
        )
