import { Button, Card, CardContent, CardDescription, CardHeader, CardTitle } from '@ax/ui'
import Link from 'next/link'

export default function Home() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-8">
      <div className="mx-auto max-w-7xl">
        <header className="mb-12 text-center">
          <h1 className="mb-4 text-5xl font-bold text-gray-900">AX Discovery Portal</h1>
          <p className="text-xl text-gray-600">
            멀티에이전트 기반 사업기회 포착 엔진
          </p>
        </header>

        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle>📥 Inbox</CardTitle>
              <CardDescription>신규 Signal 관리 및 Triage</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-gray-600">
                고객 Pain Point를 수집하고, 사업기회 신호를 등록합니다.
              </p>
              <Link href="/inbox">
                <Button className="w-full">Inbox 보기</Button>
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>📊 Scorecard</CardTitle>
              <CardDescription>Signal 평가 및 우선순위 결정</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-gray-600">
                100점 만점 스코어카드로 기회를 평가합니다.
              </p>
              <Link href="/scorecard">
                <Button className="w-full">Scorecard 보기</Button>
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>📝 Brief</CardTitle>
              <CardDescription>1-Page Opportunity Brief</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-gray-600">
                검증된 기회를 Brief로 정리하여 Confluence에 발행합니다.
              </p>
              <Link href="/brief">
                <Button className="w-full">Brief 보기</Button>
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>🎯 Play Dashboard</CardTitle>
              <CardDescription>비즈니스 케이스 추적</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-gray-600">
                Play별 진행 상황을 대시보드에서 한눈에 파악합니다.
              </p>
              <Link href="/plays">
                <Button className="w-full">Dashboard 보기</Button>
              </Link>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>🤖 Agent Workflows</CardTitle>
              <CardDescription>자동화된 워크플로우</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-gray-600">
                Claude Agent SDK 기반 6개 워크플로우를 실행합니다.
              </p>
              <Button className="w-full" variant="secondary" disabled>
                Coming Soon
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>⚙️ Settings</CardTitle>
              <CardDescription>시스템 설정</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="mb-4 text-sm text-gray-600">
                Confluence, Teams 연동 및 에이전트 설정을 관리합니다.
              </p>
              <Button className="w-full" variant="outline" disabled>
                Coming Soon
              </Button>
            </CardContent>
          </Card>
        </div>

        <footer className="mt-16 text-center text-sm text-gray-500">
          <p>Powered by Claude Agent SDK & Next.js 15</p>
          <p className="mt-2">Version 0.1.0 - PoC Phase 1</p>
        </footer>
      </div>
    </div>
  )
}
