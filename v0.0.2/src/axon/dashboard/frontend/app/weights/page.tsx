"use client"

import { useState, useEffect } from 'react'

interface Weights {
  cost: number
  delivery: number
  quality: number
  sustainability: number
  flexibility: number
}

const WEIGHT_LABELS: Record<keyof Weights, string> = {
  cost: 'Cost',
  delivery: 'Delivery',
  quality: 'Quality',
  sustainability: 'Sustainability',
  flexibility: 'Flexibility',
}

const WEIGHT_COLORS: Record<keyof Weights, string> = {
  cost: 'red',
  delivery: 'blue',
  quality: 'green',
  sustainability: 'emerald',
  flexibility: 'purple',
}

export default function WeightsPage() {
  const [weights, setWeights] = useState<Weights | null>(null)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    fetch('/api/weights')
      .then(r => r.json())
      .then(d => setWeights(d.weights))
      .catch(() => setMessage('Failed to load weights'))
  }, [])

  const handleChange = (key: keyof Weights, value: number) => {
    if (!weights) return
    const newWeights = { ...weights, [key]: value / 100 }
    setWeights(newWeights)
  }

  const handleSave = async () => {
    if (!weights) return
    setSaving(true)
    setMessage('')
    try {
      const res = await fetch('/api/weights', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(weights),
      })
      if (res.ok) {
        setMessage('Weights saved successfully')
      } else {
        setMessage('Failed to save weights')
      }
    } catch {
      setMessage('Network error')
    }
    setSaving(false)
  }

  const handleReset = async () => {
    setSaving(true)
    try {
      const res = await fetch('/api/weights/defaults')
      if (res.ok) {
        const data = await res.json()
        setWeights(data.weights)
        setMessage('Reset to defaults')
      }
    } catch {
      setMessage('Failed to reset')
    }
    setSaving(false)
  }

  if (!weights) {
    return <p className="text-gray-500">Loading weights...</p>
  }

  const total = Object.values(weights).reduce((a, b) => a + b, 0)

  return (
    <div className="space-y-8 max-w-2xl">
      <div>
        <h2 className="text-2xl font-bold text-gray-900">Strategic Weights</h2>
        <p className="text-gray-500 mt-1">
          Adjust the relative importance of each planning dimension.
          Weights are used by the Utility Scoring Engine during negotiation.
        </p>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 space-y-6">
        {(Object.keys(WEIGHT_LABELS) as (keyof Weights)[]).map(key => {
          const pct = Math.round(weights[key] * 100)
          return (
            <div key={key}>
              <div className="flex justify-between mb-1">
                <label className="text-sm font-medium text-gray-700">{WEIGHT_LABELS[key]}</label>
                <span className="text-sm text-gray-500">{pct}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={pct}
                onChange={e => handleChange(key, parseInt(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-blue-600"
              />
            </div>
          )
        })}

        <div className="pt-4 border-t border-gray-100">
          <div className="flex items-center justify-between text-sm">
            <span className="font-medium text-gray-700">Total</span>
            <span className={`font-bold ${Math.abs(total - 1.0) < 0.01 ? 'text-green-600' : 'text-red-600'}`}>
              {Math.round(total * 100)}%
            </span>
          </div>
          {Math.abs(total - 1.0) >= 0.01 && (
            <p className="text-xs text-red-500 mt-1">Weights must sum to 100%</p>
          )}
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={handleSave}
          disabled={saving || Math.abs(total - 1.0) >= 0.01}
          className="px-6 py-2.5 bg-axon-600 text-white rounded-lg hover:bg-axon-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium"
        >
          {saving ? 'Saving...' : 'Save Weights'}
        </button>
        <button
          onClick={handleReset}
          disabled={saving}
          className="px-6 py-2.5 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors text-sm font-medium"
        >
          Reset to Defaults
        </button>
      </div>

      {message && (
        <div className={`px-4 py-3 rounded-lg text-sm ${message.includes('success') ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {message}
        </div>
      )}
    </div>
  )
}
