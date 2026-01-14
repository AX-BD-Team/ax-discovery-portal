-- AX Discovery Portal - 초기 스키마
-- Cloudflare D1 (SQLite)

-- Activities 테이블 (외부 활동 기록)
CREATE TABLE IF NOT EXISTS activities (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,              -- KT, 그룹사, 대외
    channel TEXT NOT NULL,             -- 데스크리서치, 자사활동, 영업PM, 인바운드, 아웃바운드
    title TEXT NOT NULL,
    description TEXT,
    url TEXT,                          -- 원본 URL
    raw_data TEXT,                     -- JSON 원본 데이터
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Signals 테이블 (사업 기회 신호)
CREATE TABLE IF NOT EXISTS signals (
    id TEXT PRIMARY KEY,
    activity_id TEXT REFERENCES activities(id),
    title TEXT NOT NULL,
    summary TEXT,
    pain_points TEXT,                  -- JSON 배열
    opportunities TEXT,                -- JSON 배열
    customer_segment TEXT,
    industry TEXT,
    stage TEXT DEFAULT 'S0',           -- S0, S1, S2, S3
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Scorecards 테이블 (Signal 평가)
CREATE TABLE IF NOT EXISTS scorecards (
    id TEXT PRIMARY KEY,
    signal_id TEXT REFERENCES signals(id) UNIQUE,
    total_score INTEGER NOT NULL,      -- 100점 만점
    market_fit INTEGER,                -- 시장 적합성 (20점)
    kt_synergy INTEGER,                -- KT 시너지 (20점)
    technical_feasibility INTEGER,     -- 기술 실현 가능성 (20점)
    urgency INTEGER,                   -- 긴급성 (20점)
    revenue_potential INTEGER,         -- 수익 잠재력 (20점)
    recommendation TEXT,               -- GO, WATCH, PASS
    evaluator_notes TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Briefs 테이블 (1-Page Brief)
CREATE TABLE IF NOT EXISTS briefs (
    id TEXT PRIMARY KEY,
    signal_id TEXT REFERENCES signals(id),
    scorecard_id TEXT REFERENCES scorecards(id),
    title TEXT NOT NULL,
    executive_summary TEXT,
    problem_statement TEXT,
    proposed_solution TEXT,
    target_customer TEXT,
    business_model TEXT,
    competitive_advantage TEXT,
    next_steps TEXT,
    confluence_page_id TEXT,           -- Confluence 페이지 ID
    status TEXT DEFAULT 'draft',       -- draft, review, approved, published
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Plays 테이블 (Play DB)
CREATE TABLE IF NOT EXISTS plays (
    id TEXT PRIMARY KEY,
    brief_id TEXT REFERENCES briefs(id),
    name TEXT NOT NULL,
    stage TEXT DEFAULT 'S1',           -- S1, S2, S3
    owner TEXT,
    activity_count INTEGER DEFAULT 0,
    last_activity_at TEXT,
    confluence_page_id TEXT,
    status TEXT DEFAULT 'active',      -- active, on_hold, completed, abandoned
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 인덱스
CREATE INDEX IF NOT EXISTS idx_activities_source ON activities(source);
CREATE INDEX IF NOT EXISTS idx_activities_channel ON activities(channel);
CREATE INDEX IF NOT EXISTS idx_signals_stage ON signals(stage);
CREATE INDEX IF NOT EXISTS idx_signals_activity ON signals(activity_id);
CREATE INDEX IF NOT EXISTS idx_scorecards_total ON scorecards(total_score);
CREATE INDEX IF NOT EXISTS idx_scorecards_recommendation ON scorecards(recommendation);
CREATE INDEX IF NOT EXISTS idx_briefs_status ON briefs(status);
CREATE INDEX IF NOT EXISTS idx_briefs_signal ON briefs(signal_id);
CREATE INDEX IF NOT EXISTS idx_plays_stage ON plays(stage);
CREATE INDEX IF NOT EXISTS idx_plays_status ON plays(status);
