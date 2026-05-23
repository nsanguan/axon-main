import { Redis } from 'ioredis'

const REDIS_URL = process.env.REDIS_URL || 'redis://localhost:6379/0'

let redis: Redis | null = null

export function getRedis(): Redis {
  if (redis) return redis

  redis = new Redis(REDIS_URL, {
    maxRetriesPerRequest: null,
    enableReadyCheck: true,
    retryStrategy(times) {
      if (times > 5) return null
      return Math.min(times * 500, 3000)
    },
    lazyConnect: false,
  })

  redis.on('error', (err) => {
    console.error('[redis] connection error:', err.message)
  })

  redis.on('connect', () => {
    console.log('[redis] connected to', REDIS_URL)
  })

  return redis
}

export async function redisHealth(): Promise<{ ok: boolean; keys: number; url: string }> {
  try {
    const r = getRedis()
    await r.ping()
    const keys = await r.keys('mcp:*')
    return { ok: true, keys: keys.length, url: REDIS_URL }
  } catch {
    return { ok: false, keys: 0, url: REDIS_URL }
  }
}
