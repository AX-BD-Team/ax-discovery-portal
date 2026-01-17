#!/usr/bin/env python
"""
외부 세미나 수집기 로컬 테스트 스크립트

사용법:
    # 모든 수집기 테스트
    python scripts/test_seminar_collectors.py

    # 특정 수집기만 테스트
    python scripts/test_seminar_collectors.py --source onoffmix
    python scripts/test_seminar_collectors.py --source eventus
    python scripts/test_seminar_collectors.py --source devevent

    # 키워드 지정
    python scripts/test_seminar_collectors.py --keywords "AI,LLM,생성형AI"

    # 결과 제한
    python scripts/test_seminar_collectors.py --limit 5
"""

import argparse
import asyncio
import io
import sys
from datetime import datetime
from pathlib import Path

# Windows 콘솔 UTF-8 출력 설정
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 프로젝트 루트를 path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


async def test_collector(collector_name: str, keywords: list[str], limit: int) -> dict:
    """단일 수집기 테스트"""
    from backend.integrations.external_sources import (
        DevEventCollector,
        EventbriteCollector,
        EventUsCollector,
        FestaCollector,
        OnOffMixCollector,
        RSSCollector,
    )

    collectors = {
        "rss": RSSCollector,
        "onoffmix": OnOffMixCollector,
        "eventus": EventUsCollector,
        "devevent": DevEventCollector,
        "eventbrite": EventbriteCollector,
        "festa": FestaCollector,  # DEPRECATED
    }

    if collector_name not in collectors:
        return {"error": f"알 수 없는 수집기: {collector_name}"}

    print(f"\n{'='*60}")
    print(f"🔍 {collector_name.upper()} 수집기 테스트")
    print(f"{'='*60}")
    print(f"키워드: {keywords}")
    print(f"제한: {limit}개")

    start_time = datetime.now()

    try:
        collector = collectors[collector_name]()
        seminars = await collector.fetch_seminars(
            keywords=keywords,
            limit=limit,
        )

        elapsed = (datetime.now() - start_time).total_seconds()

        print(f"\n✅ 수집 완료: {len(seminars)}개 ({elapsed:.2f}초)")

        if seminars:
            print(f"\n{'─'*60}")
            print("📋 수집된 세미나 목록:")
            print(f"{'─'*60}")

            for i, seminar in enumerate(seminars[:10], 1):
                print(f"\n[{i}] {seminar.title[:50]}{'...' if len(seminar.title) > 50 else ''}")
                print(f"    📅 날짜: {seminar.date or 'N/A'}")
                print(f"    🔗 URL: {seminar.url[:60]}{'...' if len(seminar.url) > 60 else ''}")
                print(f"    🏷️ 카테고리: {', '.join(seminar.categories) if seminar.categories else 'N/A'}")
                if seminar.organizer:
                    print(f"    👤 주최: {seminar.organizer[:30]}")
                if seminar.location:
                    print(f"    📍 장소: {seminar.location[:30]}")

            if len(seminars) > 10:
                print(f"\n... 외 {len(seminars) - 10}개")

        return {
            "source": collector_name,
            "count": len(seminars),
            "elapsed": elapsed,
            "seminars": seminars,
        }

    except Exception as e:
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\n❌ 오류 발생: {e}")
        return {
            "source": collector_name,
            "error": str(e),
            "elapsed": elapsed,
        }


async def test_all_collectors(keywords: list[str], limit: int) -> list[dict]:
    """모든 활성 수집기 테스트"""
    # Festa는 DEPRECATED이므로 제외
    active_sources = ["onoffmix", "eventus", "devevent"]

    results = []
    for source in active_sources:
        result = await test_collector(source, keywords, limit)
        results.append(result)

    return results


async def test_workflow(keywords: list[str], limit: int):
    """전체 워크플로 테스트"""
    from backend.agent_runtime.workflows.wf_external_scout import (
        ExternalScoutInput,
        ExternalScoutPipeline,
    )

    print(f"\n{'='*60}")
    print("🚀 WF-07 External Scout Pipeline 테스트")
    print(f"{'='*60}")

    pipeline = ExternalScoutPipeline()

    input_data = ExternalScoutInput(
        sources=["onoffmix", "eventus", "devevent"],
        keywords=keywords,
        limit_per_source=limit,
        save_to_db=False,
    )

    start_time = datetime.now()
    result = await pipeline.run(input_data)
    elapsed = (datetime.now() - start_time).total_seconds()

    print(f"\n✅ 파이프라인 완료 ({elapsed:.2f}초)")
    print("\n📊 결과 요약:")
    print(f"    총 수집: {result.total_collected}개")
    print(f"    중복 제거: {result.duplicates_skipped}개")
    print(f"    최종 Activity: {len(result.activities)}개")

    if result.by_source:
        print("\n📈 소스별 통계:")
        for source, stats in result.by_source.items():
            print(f"    {source}: 수집 {stats.get('collected', 0)}개")

    if result.errors:
        print(f"\n⚠️ 오류 {len(result.errors)}개:")
        for err in result.errors:
            print(f"    - {err.get('source', 'unknown')}: {err.get('error', 'N/A')}")

    return result


def print_summary(results: list[dict]):
    """결과 요약 출력"""
    print(f"\n{'='*60}")
    print("📊 전체 테스트 요약")
    print(f"{'='*60}")

    total_collected = 0
    total_errors = 0

    for result in results:
        source = result.get("source", "unknown")
        if "error" in result:
            print(f"  ❌ {source}: 오류 - {result['error'][:50]}")
            total_errors += 1
        else:
            count = result.get("count", 0)
            elapsed = result.get("elapsed", 0)
            print(f"  ✅ {source}: {count}개 수집 ({elapsed:.2f}초)")
            total_collected += count

    print(f"\n총 수집: {total_collected}개")
    if total_errors:
        print(f"오류: {total_errors}개")


async def main():
    parser = argparse.ArgumentParser(description="외부 세미나 수집기 테스트")
    parser.add_argument(
        "--source",
        choices=["rss", "onoffmix", "eventus", "devevent", "eventbrite", "festa", "all", "workflow"],
        default="all",
        help="테스트할 수집기 (기본: all)",
    )
    parser.add_argument(
        "--keywords",
        type=str,
        default="AI,LLM,인공지능",
        help="검색 키워드 (쉼표 구분, 기본: AI,LLM,인공지능)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="수집 제한 개수 (기본: 10)",
    )

    args = parser.parse_args()
    keywords = [k.strip() for k in args.keywords.split(",")]

    print("\n🎯 외부 세미나 수집기 테스트")
    print(f"{'─'*60}")
    print(f"대상: {args.source}")
    print(f"키워드: {keywords}")
    print(f"제한: {args.limit}개")

    if args.source == "all":
        results = await test_all_collectors(keywords, args.limit)
        print_summary(results)
    elif args.source == "workflow":
        await test_workflow(keywords, args.limit)
    else:
        await test_collector(args.source, keywords, args.limit)


if __name__ == "__main__":
    asyncio.run(main())
