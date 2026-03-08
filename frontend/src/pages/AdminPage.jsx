import { useState, useEffect, useCallback, useRef } from 'react'
import {
  fetchStats, fetchEvaluations, fetchRules, fetchRulesRaw,
  reloadRules, validateRules, saveRules,
} from '../api'

const RISK_STYLES = {
  low: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-red-100 text-red-800',
}

function StatsBar({ stats }) {
  const items = [
    { label: 'Всего оценок', value: stats.total_count },
    { label: 'Совместимы', value: stats.compatible_count, className: 'text-green-700' },
    { label: 'Не совместимы', value: stats.incompatible_count, className: 'text-red-700' },
    { label: 'Сегодня', value: stats.today_count },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
      {items.map((item) => (
        <div key={item.label} className="rounded-lg border border-gray-200 bg-white p-4">
          <p className="text-sm text-gray-500">{item.label}</p>
          <p className={`text-2xl font-bold ${item.className || 'text-gray-900'}`}>
            {item.value}
          </p>
        </div>
      ))}
    </div>
  )
}

function EvaluationsTable({ evaluations }) {
  if (evaluations.length === 0) {
    return <p className="text-sm text-gray-500">Оценок пока нет</p>
  }

  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200 bg-white text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-4 py-2.5 text-left font-medium text-gray-500">Дата</th>
            <th className="px-4 py-2.5 text-left font-medium text-gray-500">Питомец</th>
            <th className="px-4 py-2.5 text-left font-medium text-gray-500">Вердикт</th>
            <th className="px-4 py-2.5 text-left font-medium text-gray-500">Риск</th>
            <th className="px-4 py-2.5 text-right font-medium text-gray-500">Балл</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {evaluations.map((ev) => (
            <tr key={ev.id}>
              <td className="px-4 py-2.5 text-gray-600 whitespace-nowrap">
                {new Date(ev.created_at).toLocaleString('ru-RU', {
                  day: '2-digit',
                  month: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                })}
              </td>
              <td className="px-4 py-2.5 text-gray-900">{ev.pet_type}</td>
              <td className="px-4 py-2.5">
                <span
                  className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${ev.compatible ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}
                >
                  {ev.compatible ? 'Совместим' : 'Не совместим'}
                </span>
              </td>
              <td className="px-4 py-2.5">
                <span
                  className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${RISK_STYLES[ev.risk_level]}`}
                >
                  {ev.risk_level}
                </span>
              </td>
              <td className="px-4 py-2.5 text-right text-gray-900">{ev.risk_score}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function RuleConditions({ conditions }) {
  return (
    <div className="space-y-1.5 text-sm">
      {conditions.map((c, i) => (
        <div key={i} className="flex gap-2 items-baseline">
          <span className="shrink-0 font-mono text-xs text-gray-400">
            {i === 0 ? 'if' : c.condition === 'true' ? 'else' : 'elif'}
          </span>
          <div className="min-w-0">
            {c.condition !== 'true' && (
              <code className="text-xs bg-gray-100 rounded px-1.5 py-0.5">{c.condition}</code>
            )}
            <span className="ml-2 text-gray-600">{c.message}</span>
            <span
              className={`ml-2 inline-flex rounded-full px-1.5 py-0.5 text-xs font-medium ${c.risk_score > 0 ? 'bg-red-50 text-red-700' : 'bg-green-50 text-green-700'}`}
            >
              {c.risk_score > 0 ? `+${c.risk_score}` : '0'}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}

function RulesSection({ rulesData }) {
  const [expanded, setExpanded] = useState({})

  const toggle = (key) =>
    setExpanded((prev) => ({ ...prev, [key]: !prev[key] }))

  const sections = [
    { key: 'common', label: 'Общие правила', rules: rulesData.common_rules },
    ...Object.entries(rulesData.pet_types).map(([id, pet]) => ({
      key: id,
      label: pet.name,
      rules: pet.rules,
    })),
  ]

  return (
    <div className="space-y-2">
      {sections.map(({ key, label, rules }) => (
        <div key={key} className="rounded-lg border border-gray-200 bg-white">
          <button
            onClick={() => toggle(key)}
            className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition-colors"
          >
            <span className="font-medium text-gray-900">
              {label}
              <span className="ml-2 text-sm text-gray-400">
                ({rules.length} {rules.length === 1 ? 'правило' : 'правил'})
              </span>
            </span>
            <span className="text-gray-400">{expanded[key] ? '▲' : '▼'}</span>
          </button>
          {expanded[key] && (
            <div className="border-t border-gray-100 px-4 py-3 space-y-4">
              {rules.map((rule, i) => (
                <div key={i}>
                  {rule.name && (
                    <p className="text-sm font-medium text-gray-700 mb-1">{rule.name}</p>
                  )}
                  <RuleConditions conditions={rule.conditions} />
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

function YamlEditor({ onSaved }) {
  const [yaml, setYaml] = useState('')
  const [loading, setLoading] = useState(true)
  const [result, setResult] = useState(null)
  const fileInputRef = useRef(null)

  useEffect(() => {
    fetchRulesRaw().then((text) => { setYaml(text); setLoading(false) })
  }, [])

  const handleSave = async () => {
    setResult(null)
    try {
      const res = await saveRules(yaml)
      setResult({ ok: true, text: `Сохранено (${res.rules_version.slice(0, 8)})` })
      onSaved()
    } catch (err) {
      setResult({ ok: false, text: err.message })
    }
  }

  const handleDownload = () => {
    const blob = new Blob([yaml], { type: 'application/x-yaml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'rules.yaml'
    a.click()
    URL.revokeObjectURL(url)
  }

  const handleUpload = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => setYaml(reader.result)
    reader.readAsText(file)
    e.target.value = ''
  }

  if (loading) return <p className="text-sm text-gray-500">Загрузка YAML...</p>

  return (
    <div className="space-y-3">
      <div className="flex gap-2 flex-wrap">
        <button
          onClick={handleSave}
          className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 transition-colors"
        >
          Сохранить
        </button>
        <button
          onClick={handleDownload}
          className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Скачать файл
        </button>
        <button
          onClick={() => fileInputRef.current?.click()}
          className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Загрузить файл
        </button>
        <input ref={fileInputRef} type="file" accept=".yaml,.yml" onChange={handleUpload} className="hidden" />
      </div>

      {result && (
        <div
          className={`rounded-lg border px-4 py-2.5 text-sm ${result.ok ? 'bg-green-50 border-green-200 text-green-800' : 'bg-red-50 border-red-200 text-red-800'}`}
        >
          {result.text}
        </div>
      )}

      <textarea
        value={yaml}
        onChange={(e) => setYaml(e.target.value)}
        spellCheck={false}
        className="w-full h-96 rounded-lg border border-gray-300 bg-white p-4 font-mono text-sm leading-relaxed focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
      />
    </div>
  )
}

export default function AdminPage() {
  const [stats, setStats] = useState(null)
  const [evaluations, setEvaluations] = useState([])
  const [rulesData, setRulesData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [editing, setEditing] = useState(false)

  const loadData = useCallback(async () => {
    try {
      setError(null)
      const [s, e, r] = await Promise.all([fetchStats(), fetchEvaluations(10), fetchRules()])
      setStats(s)
      setEvaluations(e)
      setRulesData(r)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  if (loading) {
    return <p className="text-center text-gray-500 py-12">Загрузка...</p>
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-red-800">
        Ошибка загрузки: {error}
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-gray-900">Админка</h1>

      {stats && <StatsBar stats={stats} />}

      <section>
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Последние оценки</h2>
        <EvaluationsTable evaluations={evaluations} />
      </section>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-gray-900">
            Правила
            {rulesData && (
              <span className="ml-2 text-sm font-normal text-gray-400">
                v{rulesData.rules_version?.slice(0, 8)}
              </span>
            )}
          </h2>
          <button
            onClick={() => setEditing(!editing)}
            className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            {editing ? 'Просмотр' : 'Редактировать YAML'}
          </button>
        </div>

        {editing ? (
          <YamlEditor onSaved={() => { loadData(); setEditing(false) }} />
        ) : (
          rulesData && <RulesSection rulesData={rulesData} />
        )}
      </section>
    </div>
  )
}
