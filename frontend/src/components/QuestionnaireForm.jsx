import { useState, useEffect } from 'react'
import { fetchPetTypes, evaluate } from '../api'

const FIELDS = [
  { name: 'apartment_size_m2', label: 'Площадь жилья (м²)', min: 1, max: 500 },
  { name: 'monthly_budget_rub', label: 'Месячный бюджет (₽)', min: 0, max: 1_000_000 },
  { name: 'work_hours_per_day', label: 'Рабочие часы в день', min: 0, max: 24 },
]

const INITIAL_PROFILE = {
  apartment_size_m2: '',
  has_children: false,
  monthly_budget_rub: '',
  work_hours_per_day: '',
}

export default function QuestionnaireForm({ onSubmit }) {
  const [petTypes, setPetTypes] = useState([])
  const [petType, setPetType] = useState('')
  const [profile, setProfile] = useState(INITIAL_PROFILE)
  const [errors, setErrors] = useState({})
  const [loading, setLoading] = useState(false)
  const [apiError, setApiError] = useState(null)

  useEffect(() => {
    fetchPetTypes().then((types) => {
      setPetTypes(types)
      if (types.length > 0) setPetType(types[0].id)
    })
  }, [])

  function validate() {
    const next = {}
    for (const { name, label, min, max } of FIELDS) {
      const raw = profile[name]
      if (raw === '' || raw === null || raw === undefined) {
        next[name] = `${label} — обязательное поле`
        continue
      }
      const num = Number(raw)
      if (!Number.isInteger(num) || num < min || num > max) {
        next[name] = `${label} — от ${min} до ${max}`
      }
    }
    return next
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setApiError(null)

    const validationErrors = validate()
    setErrors(validationErrors)
    if (Object.keys(validationErrors).length > 0) return

    setLoading(true)
    try {
      const numericProfile = {
        apartment_size_m2: Number(profile.apartment_size_m2),
        has_children: profile.has_children,
        monthly_budget_rub: Number(profile.monthly_budget_rub),
        work_hours_per_day: Number(profile.work_hours_per_day),
      }
      const result = await evaluate(petType, numericProfile)
      onSubmit(result)
    } catch (err) {
      setApiError(err.message)
    } finally {
      setLoading(false)
    }
  }

  function handleChange(name, value) {
    setProfile((prev) => ({ ...prev, [name]: value }))
    if (errors[name]) setErrors((prev) => ({ ...prev, [name]: undefined }))
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <h2 className="text-2xl font-bold text-gray-900">Анкета совместимости</h2>

      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Тип питомца</label>
        <select
          value={petType}
          onChange={(e) => setPetType(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500"
        >
          {petTypes.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </div>

      {FIELDS.map(({ name, label, min, max }) => (
        <div key={name}>
          <label className="block text-sm font-medium text-gray-700 mb-1">{label}</label>
          <input
            type="number"
            min={min}
            max={max}
            value={profile[name]}
            onChange={(e) => handleChange(name, e.target.value)}
            className={`w-full rounded-lg border px-3 py-2 text-gray-900 focus:ring-1 ${
              errors[name]
                ? 'border-red-400 focus:border-red-500 focus:ring-red-500'
                : 'border-gray-300 focus:border-indigo-500 focus:ring-indigo-500'
            }`}
          />
          {errors[name] && <p className="mt-1 text-sm text-red-600">{errors[name]}</p>}
        </div>
      ))}

      <div className="flex items-center gap-2">
        <input
          id="has_children"
          type="checkbox"
          checked={profile.has_children}
          onChange={(e) => handleChange('has_children', e.target.checked)}
          className="h-4 w-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
        />
        <label htmlFor="has_children" className="text-sm font-medium text-gray-700">
          Есть дети
        </label>
      </div>

      {apiError && (
        <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
          {apiError}
        </div>
      )}

      <button
        type="submit"
        disabled={loading || petTypes.length === 0}
        className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
      >
        {loading ? 'Проверяем…' : 'Проверить совместимость'}
      </button>
    </form>
  )
}
