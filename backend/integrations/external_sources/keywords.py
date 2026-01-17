"""
AI/AX 관련 키워드 상수 정의

외부 세미나 수집 시 필터링에 사용
"""

# AI/AX 핵심 키워드 (한글 + 영문)
AI_AX_KEYWORDS: list[str] = [
    # 핵심 키워드
    "AI",
    "인공지능",
    "LLM",
    "생성형AI",
    "생성형 AI",
    "GenAI",
    "Generative AI",
    "에이전트",
    "Agent",
    "자동화",
    "Automation",
    # 기술 키워드
    "GPT",
    "Claude",
    "Gemini",
    "ChatGPT",
    "RAG",
    "파인튜닝",
    "Fine-tuning",
    "프롬프트",
    "Prompt",
    "ML",
    "머신러닝",
    "Machine Learning",
    "딥러닝",
    "Deep Learning",
    "NLP",
    "자연어처리",
    "컴퓨터비전",
    "Computer Vision",
    "신경망",
    "Neural Network",
    # 비즈니스 키워드
    "AI 도입",
    "AI 전환",
    "AI 트랜스포메이션",
    "디지털 전환",
    "DX",
    "Digital Transformation",
    "AI 솔루션",
    "AI 플랫폼",
    "AI 서비스",
    "AI 비즈니스",
    "AI 활용",
    "AI 적용",
    # AX 관련 키워드
    "AX",
    "AI Experience",
    "AI 경험",
    "Copilot",
    "Assistant",
    "챗봇",
    "Chatbot",
]

# 카테고리별 키워드 그룹
CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "ai_general": [
        "AI",
        "인공지능",
        "Artificial Intelligence",
        "머신러닝",
        "Machine Learning",
        "딥러닝",
        "Deep Learning",
    ],
    "llm": [
        "LLM",
        "Large Language Model",
        "GPT",
        "Claude",
        "Gemini",
        "ChatGPT",
        "생성형AI",
        "GenAI",
        "Generative AI",
    ],
    "automation": [
        "자동화",
        "Automation",
        "RPA",
        "워크플로",
        "Workflow",
        "프로세스 자동화",
        "업무 자동화",
    ],
    "agent": [
        "에이전트",
        "Agent",
        "AI Agent",
        "멀티에이전트",
        "Multi-Agent",
        "Agentic",
        "자율 에이전트",
        "Autonomous Agent",
    ],
    "data": [
        "데이터",
        "Data",
        "빅데이터",
        "Big Data",
        "데이터 분석",
        "Data Analytics",
        "데이터 사이언스",
        "Data Science",
    ],
}

# 제외 키워드 (노이즈 필터링)
EXCLUDE_KEYWORDS: list[str] = [
    "채용",
    "구인",
    "모집",
    "hiring",
    "job",
    "career",
    "취업",
    "인턴",
    "intern",
]

# 플랫폼별 카테고리 매핑
ONOFFMIX_CATEGORIES: dict[str, str] = {
    "it": "104",  # IT/인터넷
    "startup": "105",  # 스타트업
    "education": "106",  # 교육/강연
}

EVENTUS_CATEGORIES: dict[str, str] = {
    "it": "IT/프로그래밍",
    "startup": "스타트업",
    "business": "비즈니스",
}


def filter_by_ai_keywords(text: str, min_matches: int = 1) -> bool:
    """
    텍스트에 AI/AX 키워드가 포함되어 있는지 확인

    Args:
        text: 검사할 텍스트
        min_matches: 최소 매칭 키워드 수

    Returns:
        bool: 키워드 포함 여부
    """
    if not text:
        return False

    text_lower = text.lower()
    matches = sum(1 for kw in AI_AX_KEYWORDS if kw.lower() in text_lower)

    return matches >= min_matches


def filter_excludes(text: str) -> bool:
    """
    제외 키워드가 포함되어 있는지 확인

    Args:
        text: 검사할 텍스트

    Returns:
        bool: 제외해야 하면 True
    """
    if not text:
        return False

    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in EXCLUDE_KEYWORDS)


def get_search_keywords(categories: list[str] | None = None) -> list[str]:
    """
    검색에 사용할 키워드 목록 반환

    Args:
        categories: 카테고리 목록 (ai_general, llm, automation, agent, data)

    Returns:
        list[str]: 키워드 목록
    """
    if not categories:
        return AI_AX_KEYWORDS[:10]  # 기본 상위 10개

    keywords = []
    for cat in categories:
        if cat in CATEGORY_KEYWORDS:
            keywords.extend(CATEGORY_KEYWORDS[cat])

    return list(set(keywords)) if keywords else AI_AX_KEYWORDS[:10]
