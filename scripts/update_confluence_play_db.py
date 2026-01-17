"""
Confluence Play DB 페이지 업데이트 스크립트
"""
import base64
import json
import sys
from pathlib import Path

import requests

# UTF-8 출력
sys.stdout.reconfigure(encoding='utf-8')

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent

# 환경 변수 로드
env = {}
env_file = PROJECT_ROOT / '.env'
with open(env_file, 'r', encoding='utf-8') as f:
    for line in f:
        if '=' in line and not line.startswith('#'):
            key, value = line.strip().split('=', 1)
            env[key] = value

# Confluence 설정
BASE_URL = env.get('CONFLUENCE_BASE_URL', '').rstrip('/')
EMAIL = env.get('CONFLUENCE_USER_EMAIL', '')
TOKEN = env.get('CONFLUENCE_API_TOKEN', '')
SPACE_KEY = env.get('CONFLUENCE_SPACE_KEY', 'AB')
PLAY_DB_PAGE_ID = env.get('CONFLUENCE_PLAY_DB_PAGE_ID', '720899')

# Basic Auth
auth_string = f'{EMAIL}:{TOKEN}'
auth_bytes = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')

HEADERS = {
    'Authorization': f'Basic {auth_bytes}',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}


def load_play_data():
    """Play 데이터 로드"""
    data_file = PROJECT_ROOT / 'scripts' / 'play_data.json'
    with open(data_file, 'r', encoding='utf-8') as f:
        return json.load(f)


def get_rag_emoji(rag: str) -> str:
    """RAG 상태에 따른 이모지 반환"""
    if rag == 'G':
        return '🟢'
    elif rag == 'Y':
        return '🟡'
    elif rag == 'R':
        return '🔴'
    return '⚪'


def generate_html_table(plays: list) -> str:
    """Play 데이터로 HTML 테이블 생성"""
    # 채널별 그룹화
    channels = ['데스크', '자사활동', '영업/PM', '인바운드', '아웃바운드']

    html_parts = []
    html_parts.append('<h2>Play 진행현황 DB (2026Q1)</h2>')
    html_parts.append(f'<p>총 {len(plays)}개 Play | 최종 업데이트: 2026-01-17</p>')

    for channel in channels:
        channel_plays = [p for p in plays if p['channel'] == channel]
        if not channel_plays:
            continue

        html_parts.append(f'<h3>{channel} ({len(channel_plays)}개)</h3>')
        html_parts.append('<table>')
        html_parts.append('<colgroup>')
        html_parts.append('<col style="width:180px"/>')  # Play ID
        html_parts.append('<col style="width:200px"/>')  # Play 이름
        html_parts.append('<col style="width:50px"/>')   # 원천
        html_parts.append('<col style="width:150px"/>')  # 담당
        html_parts.append('<col style="width:50px"/>')   # 주기
        html_parts.append('<col style="width:30px"/>')   # P
        html_parts.append('<col style="width:40px"/>')   # Act
        html_parts.append('<col style="width:40px"/>')   # Sig
        html_parts.append('<col style="width:40px"/>')   # Brf
        html_parts.append('<col style="width:30px"/>')   # S2
        html_parts.append('<col style="width:30px"/>')   # RAG
        html_parts.append('<col style="width:200px"/>')  # Next Action
        html_parts.append('</colgroup>')
        html_parts.append('<tr>')
        html_parts.append('<th>Play ID</th>')
        html_parts.append('<th>Play 이름</th>')
        html_parts.append('<th>원천</th>')
        html_parts.append('<th>담당</th>')
        html_parts.append('<th>주기</th>')
        html_parts.append('<th>P</th>')
        html_parts.append('<th>Act</th>')
        html_parts.append('<th>Sig</th>')
        html_parts.append('<th>Brf</th>')
        html_parts.append('<th>S2</th>')
        html_parts.append('<th>RAG</th>')
        html_parts.append('<th>Next Action</th>')
        html_parts.append('</tr>')

        for p in channel_plays:
            rag_emoji = get_rag_emoji(p['rag'])
            html_parts.append('<tr>')
            html_parts.append(f'<td><code>{p["id"]}</code></td>')
            html_parts.append(f'<td>{p["name"]}</td>')
            html_parts.append(f'<td>{p["source"]}</td>')
            html_parts.append(f'<td>{p["owner"]}</td>')
            html_parts.append(f'<td>{p["cycle"]}</td>')
            html_parts.append(f'<td>{p["priority"]}</td>')
            html_parts.append(f'<td>{p["act_qtd"]}/{p["act_goal"]}</td>')
            html_parts.append(f'<td>{p["sig_qtd"]}/{p["sig_goal"]}</td>')
            html_parts.append(f'<td>{p["brf_qtd"]}/{p["brf_goal"]}</td>')
            html_parts.append(f'<td>{p["s2_qtd"]}/{p["s2_goal"]}</td>')
            html_parts.append(f'<td>{rag_emoji}</td>')
            html_parts.append(f'<td>{p["next_action"]}</td>')
            html_parts.append('</tr>')

        html_parts.append('</table>')

    # 범례
    html_parts.append('<hr/>')
    html_parts.append('<h4>범례</h4>')
    html_parts.append('<ul>')
    html_parts.append('<li><strong>P</strong>: 우선순위 (P0=필수, P1=높음, P2=중간)</li>')
    html_parts.append('<li><strong>Act/Sig/Brf/S2</strong>: 실적(QTD)/목표</li>')
    html_parts.append('<li><strong>RAG</strong>: 🟢 Green (정상) / 🟡 Yellow (주의) / 🔴 Red (위험)</li>')
    html_parts.append('</ul>')
    html_parts.append('<p><em>이 페이지는 AX Discovery Portal에서 자동 생성되었습니다.</em></p>')

    return '\n'.join(html_parts)


def get_page_version(page_id: str) -> int:
    """페이지 현재 버전 조회"""
    response = requests.get(
        f'{BASE_URL}/rest/api/content/{page_id}?expand=version',
        headers=HEADERS
    )
    if response.status_code == 200:
        return response.json()['version']['number']
    return 1


def update_page(page_id: str, title: str, body: str) -> dict:
    """Confluence 페이지 업데이트"""
    current_version = get_page_version(page_id)

    data = {
        'id': page_id,
        'type': 'page',
        'title': title,
        'space': {'key': SPACE_KEY},
        'body': {
            'storage': {
                'value': body,
                'representation': 'storage'
            }
        },
        'version': {
            'number': current_version + 1
        }
    }

    response = requests.put(
        f'{BASE_URL}/rest/api/content/{page_id}',
        headers=HEADERS,
        json=data
    )

    return {
        'status': response.status_code,
        'success': response.status_code == 200,
        'response': response.json() if response.status_code == 200 else response.text
    }


def main():
    print('=' * 60)
    print('Confluence Play DB 업데이트')
    print('=' * 60)

    # Play 데이터 로드
    plays = load_play_data()
    print(f'[INFO] Play 데이터 로드: {len(plays)}개')

    # HTML 테이블 생성
    html_body = generate_html_table(plays)
    print(f'[INFO] HTML 테이블 생성 완료')

    # Confluence 페이지 업데이트
    print(f'[INFO] 페이지 업데이트 시작: {PLAY_DB_PAGE_ID}')
    result = update_page(
        PLAY_DB_PAGE_ID,
        'AX Discovery Portal - Play 진행현황 DB',
        html_body
    )

    if result['success']:
        print(f'[OK] 페이지 업데이트 완료!')
        print(f'[URL] {BASE_URL}/spaces/{SPACE_KEY}/pages/{PLAY_DB_PAGE_ID}')
    else:
        print(f'[FAIL] 업데이트 실패: {result["status"]}')
        print(f'[ERROR] {result["response"][:500]}')

    return result['success']


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
