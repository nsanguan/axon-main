import { NextResponse } from 'next/server'
import { getQueueStats, getRecentJobs } from '@/lib/queue'
import { redisHealth } from '@/lib/redis'

export const dynamic = 'force-dynamic'

export async function GET() {
  const [stats, jobs, health] = await Promise.all([
    getQueueStats(),
    getRecentJobs(10),
    redisHealth(),
  ])

  return NextResponse.json({
    redis: health,
    queue: {
      name: 'axon-planning-queue',
      ...stats,
    },
    recent_jobs: jobs,
  })
}
