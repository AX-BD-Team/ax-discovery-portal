"""
Confluence MCP Server

Confluence API 연동을 위한 MCP 서버
"""

import os
import re
from typing import Any

import markdown2
import structlog
from atlassian import Confluence

logger = structlog.get_logger()


class ConfluenceMCP:
    """
    Confluence MCP 서버

    Tools:
    - confluence.search_pages
    - confluence.get_page
    - confluence.create_page
    - confluence.update_page
    - confluence.append_to_page
    - confluence.add_labels
    - confluence.db_query
    - confluence.db_upsert_row
    - confluence.db_insert_row
    """

    def __init__(self):
        self.base_url = os.getenv("CONFLUENCE_BASE_URL", "")
        self.api_token = os.getenv("CONFLUENCE_API_TOKEN", "")
        self.user_email = os.getenv("CONFLUENCE_USER_EMAIL", "")
        self.space_key = os.getenv("CONFLUENCE_SPACE_KEY", "AXBD")

        self._client: Confluence | None = None
        self.logger = logger.bind(mcp="confluence")

    @property
    def client(self) -> Confluence:
        """Confluence 클라이언트 (lazy init)"""
        if self._client is None:
            if not all([self.base_url, self.api_token, self.user_email]):
                raise ValueError("Confluence credentials not configured")

            self._client = Confluence(
                url=self.base_url, username=self.user_email, password=self.api_token, cloud=True
            )
        return self._client

    # ========== 페이지 Tools ==========

    async def search_pages(self, query: str, limit: int = 10) -> dict[str, Any]:
        """페이지 검색"""
        self.logger.info("search_pages", query=query, limit=limit)

        try:
            results = self.client.cql(
                f'space = "{self.space_key}" AND text ~ "{query}"', limit=limit
            )

            pages = [
                {
                    "id": r["content"]["id"],
                    "title": r["content"]["title"],
                    "url": f"{self.base_url}/wiki{r['content']['_links']['webui']}",
                }
                for r in results.get("results", [])
            ]

            return {"pages": pages, "total": len(pages)}
        except Exception as e:
            self.logger.error("search_pages_failed", error=str(e))
            raise

    async def get_page(self, page_id: str) -> dict[str, Any]:
        """페이지 조회"""
        self.logger.info("get_page", page_id=page_id)

        try:
            page = self.client.get_page_by_id(page_id, expand="body.storage,version")

            return {
                "id": page["id"],
                "title": page["title"],
                "body": page["body"]["storage"]["value"],
                "version": page["version"]["number"],
                "url": f"{self.base_url}/wiki{page['_links']['webui']}",
            }
        except Exception as e:
            self.logger.error("get_page_failed", error=str(e))
            raise

    async def create_page(
        self,
        title: str,
        body_md: str,
        parent_id: str | None = None,
        labels: list[str] | None = None,
    ) -> dict[str, Any]:
        """페이지 생성"""
        self.logger.info("create_page", title=title, parent_id=parent_id)

        try:
            # Markdown to Confluence Wiki 변환
            body_html = self._markdown_to_confluence(body_md)

            page = self.client.create_page(
                space=self.space_key, title=title, body=body_html, parent_id=parent_id
            )

            page_id = page["id"]

            # 라벨 추가
            if labels:
                for label in labels:
                    self.client.set_page_label(page_id, label)

            return {
                "page_id": page_id,
                "url": f"{self.base_url}/wiki/spaces/{self.space_key}/pages/{page_id}",
                "title": title,
            }
        except Exception as e:
            self.logger.error("create_page_failed", error=str(e))
            raise

    async def update_page(
        self, page_id: str, body_md: str, version: int | None = None
    ) -> dict[str, Any]:
        """페이지 수정"""
        self.logger.info("update_page", page_id=page_id)

        try:
            # 현재 페이지 정보 조회
            current = await self.get_page(page_id)
            # version 파라미터는 향후 낙관적 잠금에 사용 예정
            _ = version or current["version"]

            body_html = self._markdown_to_confluence(body_md)

            page = self.client.update_page(
                page_id=page_id, title=current["title"], body=body_html, type="page"
            )

            return {"page_id": page_id, "version": page["version"]["number"], "url": current["url"]}
        except Exception as e:
            self.logger.error("update_page_failed", error=str(e))
            raise

    async def append_to_page(self, page_id: str, append_md: str) -> dict[str, Any]:
        """페이지에 내용 추가"""
        self.logger.info("append_to_page", page_id=page_id)

        try:
            current = await self.get_page(page_id)
            append_html = self._markdown_to_confluence(append_md)
            new_body = current["body"] + append_html

            return await self.update_page(
                page_id=page_id,
                body_md=new_body,  # 이미 HTML이므로 변환 없이 전달
            )
        except Exception as e:
            self.logger.error("append_to_page_failed", error=str(e))
            raise

    async def add_labels(self, page_id: str, labels: list[str]) -> dict[str, Any]:
        """라벨 추가"""
        self.logger.info("add_labels", page_id=page_id, labels=labels)

        try:
            for label in labels:
                self.client.set_page_label(page_id, label)

            return {"page_id": page_id, "labels": labels}
        except Exception as e:
            self.logger.error("add_labels_failed", error=str(e))
            raise

    # ========== DB Tools (PostgreSQL 위임) ==========
    #
    # Confluence Cloud API는 Database 기능을 지원하지 않습니다.
    # 대신 PostgreSQL 기반의 PlayRecordRepository를 사용합니다.
    #
    # 권장 사용법:
    #   from backend.database.repositories.play_record import play_record_repo
    #   from backend.services.play_sync_service import play_sync_service
    #
    # 예시:
    #   play = await play_record_repo.get_by_id(db, play_id)
    #   await play_sync_service.sync_play_to_confluence(db, play_id)

    async def db_query(
        self, database_id: str, filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        [DEPRECATED] DB 조회 - PostgreSQL PlayRecordRepository 사용 권장

        Confluence Cloud API는 Database 기능을 지원하지 않습니다.
        대신 play_record_repo.get_multi_filtered() 또는
        play_record_repo.get_all()을 사용하세요.

        Args:
            database_id: 무시됨 (하위 호환성용)
            filters: 무시됨 (하위 호환성용)

        Returns:
            dict: 빈 결과와 함께 PostgreSQL 사용 안내
        """
        self.logger.warning(
            "db_query is deprecated. Use PlayRecordRepository instead.",
            database_id=database_id,
        )
        return {
            "rows": [],
            "total": 0,
            "deprecated": True,
            "message": "Confluence Database API는 지원되지 않습니다. "
            "PostgreSQL 기반의 play_record_repo를 사용하세요.",
            "alternative": "play_record_repo.get_multi_filtered(db, status, owner, skip, limit)",
        }

    async def db_upsert_row(
        self, database_id: str, row_id: str, data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        [DEPRECATED] DB 행 업데이트/삽입 - PostgreSQL 사용 권장

        Confluence Cloud API는 Database 기능을 지원하지 않습니다.
        대신 play_sync_service.sync_play_to_confluence()를 사용하세요.

        Args:
            database_id: 무시됨 (하위 호환성용)
            row_id: Play ID (참고용)
            data: 무시됨 (하위 호환성용)

        Returns:
            dict: PostgreSQL 사용 안내
        """
        self.logger.warning(
            "db_upsert_row is deprecated. Use PlaySyncService instead.",
            database_id=database_id,
            row_id=row_id,
        )
        return {
            "row_id": row_id,
            "status": "deprecated",
            "deprecated": True,
            "message": "Confluence Database API는 지원되지 않습니다. "
            "PostgreSQL 기반의 play_sync_service를 사용하세요.",
            "alternative": "play_sync_service.sync_play_to_confluence(db, play_id)",
        }

    async def db_insert_row(self, database_id: str, data: dict[str, Any]) -> dict[str, Any]:
        """
        [DEPRECATED] DB 행 삽입 - PostgreSQL 사용 권장

        Confluence Cloud API는 Database 기능을 지원하지 않습니다.
        대신 play_record_repo.create()를 사용하세요.

        Args:
            database_id: 무시됨 (하위 호환성용)
            data: 무시됨 (하위 호환성용)

        Returns:
            dict: PostgreSQL 사용 안내
        """
        self.logger.warning(
            "db_insert_row is deprecated. Use PlayRecordRepository instead.",
            database_id=database_id,
        )
        return {
            "status": "deprecated",
            "deprecated": True,
            "message": "Confluence Database API는 지원되지 않습니다. "
            "PostgreSQL 기반의 play_record_repo를 사용하세요.",
            "alternative": "play_record_repo.create(db, PlayRecord(...))",
        }

    async def increment_play_activity_count(self, page_id: str, play_id: str) -> dict[str, Any]:
        """Play DB 테이블에서 activity_qtd 증가"""
        self.logger.info("increment_play_activity_count", page_id=page_id, play_id=play_id)

        try:
            # 1. 페이지 조회
            page = await self.get_page(page_id)
            body = page["body"]

            # 2. 정규표현식으로 테이블 행 찾기 & 카운트 증가
            import re

            pattern = rf"\|(\s*{re.escape(play_id)}\s*)\|([^|]*)\|([^|]*)\|(\s*\d+\s*)\|"

            def increment_match(match):
                count = int(match.group(4).strip())
                return f"|{match.group(1)}|{match.group(2)}|{match.group(3)}| {count + 1} |"

            updated_body = re.sub(pattern, increment_match, body)

            # 3. 페이지 업데이트
            if updated_body != body:
                await self.update_page(page_id=page_id, body_md=updated_body)
                self.logger.info("Play DB updated", play_id=play_id)
                return {"status": "updated", "play_id": play_id}
            else:
                self.logger.warning("Play ID not found in table", play_id=play_id)
                return {"status": "not_found", "play_id": play_id}

        except Exception as e:
            self.logger.error("increment_play_activity_count failed", error=str(e))
            raise

    # ========== 유틸리티 ==========

    def _markdown_to_confluence(self, md: str) -> str:
        """
        Markdown to Confluence Storage Format 변환

        지원 요소:
        - 헤더 (h1~h6)
        - 표 (테이블)
        - 링크
        - 목록 (순서/비순서)
        - 강조 (bold, italic)
        - 코드 블록
        - 취소선
        """
        if not md or not md.strip():
            return ""

        # 1. markdown2로 HTML 변환 (테이블, 코드 하이라이팅 지원)
        html = markdown2.markdown(
            md,
            extras=[
                "tables",
                "fenced-code-blocks",
                "strike",
                "task_list",
                "header-ids",
            ],
        )

        # 2. Confluence Storage Format 호환 처리

        # 2-1. 코드 블록 (codehilite div) → Confluence 코드 매크로
        # markdown2 codehilite 패턴: <div class="codehilite"><pre>...</pre></div>
        def replace_codehilite(match):
            code_content = match.group(1)
            # HTML 태그 제거하고 순수 코드만 추출
            code_content = re.sub(r"<[^>]+>", "", code_content)
            # HTML 엔티티 디코딩
            code_content = code_content.replace("&quot;", '"')
            code_content = code_content.replace("&lt;", "<")
            code_content = code_content.replace("&gt;", ">")
            code_content = code_content.replace("&amp;", "&")
            return f'<ac:structured-macro ac:name="code"><ac:plain-text-body><![CDATA[{code_content}]]></ac:plain-text-body></ac:structured-macro>'

        html = re.sub(
            r'<div class="codehilite">\s*<pre[^>]*><span></span><code>(.*?)</code></pre>\s*</div>',
            replace_codehilite,
            html,
            flags=re.DOTALL,
        )

        # 2-2. 일반 코드 블록: <pre><code> → <ac:structured-macro>
        html = re.sub(
            r'<pre><code class="([^"]+)">(.*?)</code></pre>',
            r'<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">\1</ac:parameter><ac:plain-text-body><![CDATA[\2]]></ac:plain-text-body></ac:structured-macro>',
            html,
            flags=re.DOTALL,
        )
        html = re.sub(
            r"<pre><code>(.*?)</code></pre>",
            r'<ac:structured-macro ac:name="code"><ac:plain-text-body><![CDATA[\1]]></ac:plain-text-body></ac:structured-macro>',
            html,
            flags=re.DOTALL,
        )

        # 2-3. 테이블 스타일 추가 (Confluence 기본 테이블 스타일)
        html = html.replace("<table>", '<table class="wrapped">')
        html = html.replace("<th>", '<th class="confluenceTh">')
        html = html.replace("<td>", '<td class="confluenceTd">')

        # 2-4. 체크박스 (Task list)
        html = html.replace(
            '<input type="checkbox" disabled>',
            "<ac:task-status>incomplete</ac:task-status>",
        )
        html = html.replace(
            '<input type="checkbox" checked disabled>',
            "<ac:task-status>complete</ac:task-status>",
        )

        # 2-5. 취소선: <s> → <span style>
        html = html.replace("<s>", "<span style='text-decoration: line-through;'>")
        html = html.replace("</s>", "</span>")

        # 2-6. <del> 태그도 처리 (일부 Markdown 파서 호환)
        html = html.replace("<del>", "<span style='text-decoration: line-through;'>")
        html = html.replace("</del>", "</span>")

        return html


# MCP Tool 정의
MCP_TOOLS = [
    {
        "name": "confluence.search_pages",
        "description": "Confluence 페이지 검색",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["query"],
        },
    },
    {
        "name": "confluence.get_page",
        "description": "Confluence 페이지 조회",
        "parameters": {
            "type": "object",
            "properties": {"page_id": {"type": "string"}},
            "required": ["page_id"],
        },
    },
    {
        "name": "confluence.create_page",
        "description": "Confluence 페이지 생성",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "body_md": {"type": "string"},
                "parent_id": {"type": "string"},
                "labels": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "body_md"],
        },
    },
    {
        "name": "confluence.update_page",
        "description": "Confluence 페이지 수정",
        "parameters": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string"},
                "body_md": {"type": "string"},
                "version": {"type": "integer"},
            },
            "required": ["page_id", "body_md"],
        },
    },
    {
        "name": "confluence.append_to_page",
        "description": "Confluence 페이지에 내용 추가",
        "parameters": {
            "type": "object",
            "properties": {"page_id": {"type": "string"}, "append_md": {"type": "string"}},
            "required": ["page_id", "append_md"],
        },
    },
    {
        "name": "confluence.db_upsert_row",
        "description": "Confluence DB 행 업데이트/삽입",
        "parameters": {
            "type": "object",
            "properties": {
                "database_id": {"type": "string"},
                "row_id": {"type": "string"},
                "data": {"type": "object"},
            },
            "required": ["database_id", "row_id", "data"],
        },
    },
]


# MCP 서버 진입점
if __name__ == "__main__":
    import asyncio

    async def main():
        mcp = ConfluenceMCP()
        print("Confluence MCP Server")
        print(f"Base URL: {mcp.base_url}")
        print(f"Space: {mcp.space_key}")
        print(f"Tools: {[t['name'] for t in MCP_TOOLS]}")

    asyncio.run(main())
