'use client'

interface ScoreDistributionChartProps {
  data: {
    ranges: Array<{ range: string; count: number }>
    avg_score: number
  }
}

export function ScoreDistributionChart({ data }: ScoreDistributionChartProps) {
  const maxCount = Math.max(...data.ranges.map(r => r.count), 1)

  const getRangeColor = (range: string) => {
    if (range.includes('70') || range.includes('80') || range.includes('90')) return 'bg-green-500'
    if (range.includes('50') || range.includes('60')) return 'bg-yellow-500'
    if (range.includes('30') || range.includes('40')) return 'bg-orange-500'
    return 'bg-red-500'
  }

  return (
    <div className="space-y-4">
      {/* Bar Chart */}
      <div className="space-y-3">
        {data.ranges.map(({ range, count }) => (
          <div key={range} className="flex items-center gap-3">
            <div className="w-20 text-sm font-medium text-gray-700">{range}</div>
            <div className="flex-1">
              <div className="relative h-8 overflow-hidden rounded-lg bg-gray-100">
                <div
                  className={`flex h-full items-center justify-end px-3 text-sm font-medium text-white transition-all ${getRangeColor(range)}`}
                  style={{ width: `${(count / maxCount) * 100}%` }}
                >
                  {count > 0 && <span>{count}</span>}
                </div>
              </div>
            </div>
            <div className="w-16 text-right text-sm text-gray-600">
              {count > 0 ? `${((count / data.ranges.reduce((sum, r) => sum + r.count, 0)) * 100).toFixed(0)}%` : '0%'}
            </div>
          </div>
        ))}
      </div>

      {/* Summary */}
      <div className="flex items-center justify-between rounded-lg border bg-gray-50 p-4">
        <div>
          <p className="text-sm text-gray-600">Total Evaluated</p>
          <p className="text-2xl font-bold text-gray-900">
            {data.ranges.reduce((sum, r) => sum + r.count, 0)}
          </p>
        </div>
        <div>
          <p className="text-sm text-gray-600">Average Score</p>
          <p className="text-2xl font-bold text-purple-600">{data.avg_score.toFixed(1)}</p>
        </div>
      </div>
    </div>
  )
}
