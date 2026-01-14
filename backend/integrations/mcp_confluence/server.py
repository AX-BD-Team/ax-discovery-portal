"""
Confluence MCP Server

Confluence API 연동을 위한 MCP 서버
"""

import os
from typing import Any
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
                url=self.base_url,
                username=self.user_email,
                password=self.api_token,
                cloud=True
            )
        return self._client
    
    # ========== 페이지 Tools ==========
    
    async def search_pages(
        self,
        query: str,
        limit: int = 10
    ) -> dict[str, Any]:
        """페이지 검색"""
        self.logger.info("search_pages", query=query, limit=limit)
        
        try:
            results = self.client.cql(
                f'space = "{self.space_key}" AND text ~ "{query}"',
                limit=limit
            )
            
            pages = [
                {
                    "id": r["content"]["id"],
                    "title": r["content"]["title"],
                    "url": f"{self.base_url}/wiki{r['content']['_links']['webui']}"
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
            page = self.client.get_page_by_id(
                page_id,
                expand="body.storage,version"
            )
            
            return {
                "id": page["id"],
                "title": page["title"],
                "body": page["body"]["storage"]["value"],
                "version": page["version"]["number"],
                "url": f"{self.base_url}/wiki{page['_links']['webui']}"
            }
        except Exception as e:
            self.logger.error("get_page_failed", error=str(e))
            raise
    
    async def create_page(
        self,
        title: str,
        body_md: str,
        parent_id: str | None = None,
        labels: list[str] | None = None
    ) -> dict[str, Any]:
        """페이지 생성"""
        self.logger.info("create_page", title=title, parent_id=parent_id)
        
        try:
            # Markdown to Confluence Wiki 변환
            body_html = self._markdown_to_confluence(body_md)
            
            page = self.client.create_page(
                space=self.space_key,
                title=title,
                body=body_html,
                parent_id=parent_id
            )
            
            page_id = page["id"]
            
            # 라벨 추가
            if labels:
                for label in labels:
                    self.client.set_page_label(page_id, label)
            
            return {
                "page_id": page_id,
                "url": f"{self.base_url}/wiki/spaces/{self.space_key}/pages/{page_id}",
                "title": title
            }
        except Exception as e:
            self.logger.error("create_page_failed", error=str(e))
            raise
    
    async def update_page(
        self,
        page_id: str,
        body_md: str,
        version: int | None = None
    ) -> dict[str, Any]:
        """페이지 수정"""
        self.logger.info("update_page", page_id=page_id)
        
        try:
            # 현재 페이지 정보 조회
            current = await self.get_page(page_id)
            current_version = version or current["version"]
            
            body_html = self._markdown_to_confluence(body_md)
            
            page = self.client.update_page(
                page_id=page_id,
                title=current["title"],
                body=body_html
            )
            
            return {
                "page_id": page_id,
                "version": page["version"]["number"],
                "url": current["url"]
            }
        except Exception as e:
            self.logger.error("update_page_failed", error=str(e))
            raise
    
    async def append_to_page(
        self,
        page_id: str,
        append_md: str
    ) -> dict[str, Any]:
        """페이지에 내용 추가"""
        self.logger.info("append_to_page", page_id=page_id)
        
        try:
            current = await self.get_page(page_id)
            append_html = self._markdown_to_confluence(append_md)
            new_body = current["body"] + append_html
            
            return await self.update_page(
                page_id=page_id,
                body_md=new_body  # 이미 HTML이므로 변환 없이 전달
            )
        except Exception as e:
            self.logger.error("append_to_page_failed", error=str(e))
            raise
    
    async def add_labels(
        self,
        page_id: str,
        labels: list[str]
    ) -> dict[str, Any]:
        """라벨 추가"""
        self.logger.info("add_labels", page_id=page_id, labels=labels)
        
        try:
            for label in labels:
                self.client.set_page_label(page_id, label)
            
            return {"page_id": page_id, "labels": labels}
        except Exception as e:
            self.logger.error("add_labels_failed", error=str(e))
            raise
    
    # ========== DB Tools (Confluence Database) ==========
    
    async def db_query(
        self,
        database_id: str,
        filters: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """DB 조회"""
        # TODO: Confluence Database API 구현
        # 현재 Confluence Cloud API는 DB 기능이 제한적
        self.logger.info("db_query", database_id=database_id)
        return {"rows": [], "total": 0}
    
    async def db_upsert_row(
        self,
        database_id: str,
        row_id: str,
        data: dict[str, Any]
    ) -> dict[str, Any]:
        """DB 행 업데이트/삽입"""
        # TODO: Confluence Database API 구현
        self.logger.info("db_upsert_row", database_id=database_id, row_id=row_id)
        return {"row_id": row_id, "status": "upserted"}
    
    async def db_insert_row(
        self,
        database_id: str,
        data: dict[str, Any]
    ) -> dict[str, Any]:
        """DB 행 삽입"""
        # TODO: Confluence Database API 구현
        self.logger.info("db_insert_row", database_id=database_id)
        return {"status": "inserted"}
    
    # ========== 유틸리티 ==========
    
    def _markdown_to_confluence(self, md: str) -> str:
        """Markdown to Confluence Wiki 변환 (간단 버전)"""
        # TODO: 더 완전한 변환 구현
        # 현재는 기본 HTML 래핑만
        return f"<p>{md}</p>".replace("\n", "<br/>")


# MCP Tool 정의
MCP_TOOLS = [
    {
        "name": "confluence.search_pages",
        "description": "Confluence 페이지 검색",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "limit": {"type": "integer", "default": 10}
            },
            "required": ["query"]
        }
    },
    {
        "name": "confluence.get_page",
        "description": "Confluence 페이지 조회",
        "parameters": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string"}
            },
            "required": ["page_id"]
        }
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
                "labels": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["title", "body_md"]
        }
    },
    {
        "name": "confluence.update_page",
        "description": "Confluence 페이지 수정",
        "parameters": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string"},
                "body_md": {"type": "string"},
                "version": {"type": "integer"}
            },
            "required": ["page_id", "body_md"]
        }
    },
    {
        "name": "confluence.append_to_page",
        "description": "Confluence 페이지에 내용 추가",
        "parameters": {
            "type": "object",
            "properties": {
                "page_id": {"type": "string"},
                "append_md": {"type": "string"}
            },
            "required": ["page_id", "append_md"]
        }
    },
    {
        "name": "confluence.db_upsert_row",
        "description": "Confluence DB 행 업데이트/삽입",
        "parameters": {
            "type": "object",
            "properties": {
                "database_id": {"type": "string"},
                "row_id": {"type": "string"},
                "data": {"type": "object"}
            },
            "required": ["database_id", "row_id", "data"]
        }
    }
]


# MCP 서버 진입점
if __name__ == "__main__":
    import asyncio
    
    async def main():
        mcp = ConfluenceMCP()
        print(f"Confluence MCP Server")
        print(f"Base URL: {mcp.base_url}")
        print(f"Space: {mcp.space_key}")
        print(f"Tools: {[t['name'] for t in MCP_TOOLS]}")
    
    asyncio.run(main())
