import { Queue, QueueEvents, type Job } from 'bullmq'
import { getRedis } from './redis'

export interface PlanningJobData {
  event_type: string
  raw_detail: string
  affected_departments: string[]
  thread_id?: string
}

export interface PlanningJobResult {
  thread_id: string
  status: string
  severity_score: number
  summary: string | null
}

const QUEUE_NAME = 'axon-planning-queue'

let queue: Queue<PlanningJobData, PlanningJobResult> | null = null
let queueEvents: QueueEvents | null = null

export function getPlanningQueue(): Queue<PlanningJobData, PlanningJobResult> {
  if (queue) return queue

  const connection = getRedis()
  queue = new Queue<PlanningJobData, PlanningJobResult>(QUEUE_NAME, {
    connection,
    defaultJobOptions: {
      attempts: 3,
      backoff: { type: 'exponential', delay: 2000 },
      removeOnComplete: { age: 3600 * 24 },
      removeOnFail: { age: 3600 * 24 * 7 },
    },
  })

  return queue
}

export function getQueueEvents(): QueueEvents {
  if (queueEvents) return queueEvents

  const connection = getRedis()
  queueEvents = new QueueEvents(QUEUE_NAME, { connection })

  return queueEvents
}

export async function getQueueStats(): Promise<{
  waiting: number
  active: number
  completed: number
  failed: number
  delayed: number
}> {
  try {
    const q = getPlanningQueue()
    const [waiting, active, completed, failed, delayed] = await Promise.all([
      q.getWaitingCount(),
      q.getActiveCount(),
      q.getCompletedCount(),
      q.getFailedCount(),
      q.getDelayedCount(),
    ])
    return { waiting, active, completed, failed, delayed }
  } catch {
    return { waiting: 0, active: 0, completed: 0, failed: 0, delayed: 0 }
  }
}

export async function getRecentJobs(limit: number = 20): Promise<
  Array<{ id: string; name: string; status: string; data: PlanningJobData; result: PlanningJobResult | null }>
> {
  try {
    const q = getPlanningQueue()
    const allStatuses = ['completed', 'failed', 'active', 'waiting', 'delayed'] as const
    const jobs: Array<{ job: Job<PlanningJobData, PlanningJobResult>; status: string }> = []

    for (const status of allStatuses) {
      const statusJobs = await q.getJobs(status, 0, limit)
      jobs.push(...statusJobs.map(job => ({ job, status })))
      if (jobs.length >= limit) break
    }

    return jobs.slice(0, limit).map(({ job, status }) => ({
      id: job.id || 'unknown',
      name: job.name,
      status,
      data: job.data,
      result: job.returnvalue || null,
    }))
  } catch {
    return []
  }
}
