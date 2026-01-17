"""
Play 데이터 DB 적재 스크립트

play_data.json → play_records 테이블 적재
"""

import asyncio
import json
import sys
from datetime import date, datetime
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.database.models.play_record import PlayRecord
from backend.database.session import SessionLocal as AsyncSessionLocal
from backend.database.session import engine


async def load_play_data(json_path: Path, db: AsyncSession) -> dict:
    """
    JSON 파일에서 Play 데이터를 읽어 DB에 적재

    Args:
        json_path: play_data.json 경로
        db: 데이터베이스 세션

    Returns:
        dict: 적재 결과 통계
    """
    # JSON 파일 로드
    with open(json_path, encoding="utf-8") as f:
        plays_data = json.load(f)

    stats = {"total": len(plays_data), "created": 0, "updated": 0, "errors": []}

    for play_data in plays_data:
        try:
            play_id = play_data["id"]

            # 기존 레코드 확인
            result = await db.execute(
                text("SELECT play_id FROM play_records WHERE play_id = :play_id"), {"play_id": play_id}
            )
            existing = result.scalar_one_or_none()

            # due_date 파싱
            due_date_str = play_data.get("due")
            due_date = None
            if due_date_str:
                try:
                    due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
                except ValueError:
                    pass

            # 채널 매핑 (JSON의 channel → DB 형식)
            channel_map = {
                "데스크": "데스크",
                "자사활동": "자사활동",
                "영업/PM": "영업/PM",
                "인바운드": "인바운드",
                "아웃바운드": "아웃바운드",
            }
            channel = channel_map.get(play_data.get("channel"), play_data.get("channel"))

            # 원천 매핑
            source_map = {
                "KT": "KT",
                "그룹사": "그룹사",
                "대외": "대외",
                "공통": "공통",
            }
            source = source_map.get(play_data.get("source"), play_data.get("source"))

            if existing:
                # UPDATE
                await db.execute(
                    text("""
                        UPDATE play_records SET
                            play_name = :play_name,
                            owner = :owner,
                            source = :source,
                            channel = :channel,
                            cycle = :cycle,
                            priority = :priority,
                            quarter = :quarter,
                            status = :status,
                            activity_goal = :activity_goal,
                            signal_goal = :signal_goal,
                            brief_goal = :brief_goal,
                            s2_goal = :s2_goal,
                            activity_qtd = :activity_qtd,
                            signal_qtd = :signal_qtd,
                            brief_qtd = :brief_qtd,
                            s2_qtd = :s2_qtd,
                            lead_time_target = :lead_time_target,
                            next_action = :next_action,
                            due_date = :due_date,
                            blocker = :blocker,
                            last_updated = :last_updated
                        WHERE play_id = :play_id
                    """),
                    {
                        "play_id": play_id,
                        "play_name": play_data["name"],
                        "owner": play_data.get("owner"),
                        "source": source,
                        "channel": channel,
                        "cycle": play_data.get("cycle"),
                        "priority": play_data.get("priority"),
                        "quarter": play_data.get("quarter"),
                        "status": play_data.get("rag", "G"),
                        "activity_goal": play_data.get("act_goal", 0),
                        "signal_goal": play_data.get("sig_goal", 0),
                        "brief_goal": play_data.get("brf_goal", 0),
                        "s2_goal": play_data.get("s2_goal", 0),
                        "activity_qtd": play_data.get("act_qtd", 0),
                        "signal_qtd": play_data.get("sig_qtd", 0),
                        "brief_qtd": play_data.get("brf_qtd", 0),
                        "s2_qtd": play_data.get("s2_qtd", 0),
                        "lead_time_target": play_data.get("lead_time"),
                        "next_action": play_data.get("next_action"),
                        "due_date": due_date,
                        "blocker": play_data.get("blocker") or None,
                        "last_updated": datetime.utcnow(),
                    },
                )
                stats["updated"] += 1
            else:
                # INSERT
                await db.execute(
                    text("""
                        INSERT INTO play_records (
                            play_id, play_name, owner, source, channel, cycle, priority, quarter,
                            status, activity_goal, signal_goal, brief_goal, s2_goal,
                            activity_qtd, signal_qtd, brief_qtd, s2_qtd, s3_qtd,
                            lead_time_target, next_action, due_date, blocker,
                            created_at, last_updated
                        ) VALUES (
                            :play_id, :play_name, :owner, :source, :channel, :cycle, :priority, :quarter,
                            :status, :activity_goal, :signal_goal, :brief_goal, :s2_goal,
                            :activity_qtd, :signal_qtd, :brief_qtd, :s2_qtd, :s3_qtd,
                            :lead_time_target, :next_action, :due_date, :blocker,
                            :created_at, :last_updated
                        )
                    """),
                    {
                        "play_id": play_id,
                        "play_name": play_data["name"],
                        "owner": play_data.get("owner"),
                        "source": source,
                        "channel": channel,
                        "cycle": play_data.get("cycle"),
                        "priority": play_data.get("priority"),
                        "quarter": play_data.get("quarter"),
                        "status": play_data.get("rag", "G"),
                        "activity_goal": play_data.get("act_goal", 0),
                        "signal_goal": play_data.get("sig_goal", 0),
                        "brief_goal": play_data.get("brf_goal", 0),
                        "s2_goal": play_data.get("s2_goal", 0),
                        "activity_qtd": play_data.get("act_qtd", 0),
                        "signal_qtd": play_data.get("sig_qtd", 0),
                        "brief_qtd": play_data.get("brf_qtd", 0),
                        "s2_qtd": play_data.get("s2_qtd", 0),
                        "s3_qtd": 0,
                        "lead_time_target": play_data.get("lead_time"),
                        "next_action": play_data.get("next_action"),
                        "due_date": due_date,
                        "blocker": play_data.get("blocker") or None,
                        "created_at": datetime.utcnow(),
                        "last_updated": datetime.utcnow(),
                    },
                )
                stats["created"] += 1

        except Exception as e:
            stats["errors"].append({"play_id": play_data.get("id", "unknown"), "error": str(e)})

    await db.commit()
    return stats


async def main():
    """메인 실행 함수"""
    # JSON 파일 경로
    json_path = project_root / "scripts" / "play_data.json"

    if not json_path.exists():
        print(f"오류: {json_path} 파일을 찾을 수 없습니다.")
        sys.exit(1)

    print(f"Play 데이터 적재 시작: {json_path}")

    async with AsyncSessionLocal() as db:
        stats = await load_play_data(json_path, db)

    print("\n=== 적재 완료 ===")
    print(f"전체: {stats['total']}건")
    print(f"생성: {stats['created']}건")
    print(f"업데이트: {stats['updated']}건")

    if stats["errors"]:
        print(f"\n오류: {len(stats['errors'])}건")
        for err in stats["errors"]:
            print(f"  - {err['play_id']}: {err['error']}")


if __name__ == "__main__":
    asyncio.run(main())
