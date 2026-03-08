const RISK_STYLES = {
  low: 'bg-green-100 text-green-800',
  medium: 'bg-yellow-100 text-yellow-800',
  high: 'bg-red-100 text-red-800',
}

const RISK_LABELS = {
  low: 'Низкий',
  medium: 'Средний',
  high: 'Высокий',
}

export default function EvaluationResult({ result, onReset }) {
  const { compatible, risk_level, risk_score, reasons, positives, alternatives } = result

  return (
    <div className="space-y-6">
      {/* Verdict */}
      <div
        className={`rounded-xl p-6 ${compatible ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}
      >
        <div className="flex items-center justify-between">
          <div>
            <h2 className={`text-2xl font-bold ${compatible ? 'text-green-800' : 'text-red-800'}`}>
              {compatible ? 'Совместимы ✓' : 'Не совместимы ✗'}
            </h2>
            <p className="mt-1 text-sm text-gray-600">Суммарный балл риска: {risk_score}</p>
          </div>
          <span
            className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${RISK_STYLES[risk_level]}`}
          >
            Риск: {RISK_LABELS[risk_level]}
          </span>
        </div>
      </div>

      {/* Reasons */}
      {reasons.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Риски</h3>
          <ul className="space-y-2">
            {reasons.map((reason, i) => (
              <li
                key={i}
                className="flex gap-2 rounded-lg bg-red-50 border border-red-100 px-4 py-2.5 text-sm text-red-800"
              >
                <span className="shrink-0">⚠</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Positives */}
      {positives.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Позитивные моменты</h3>
          <ul className="space-y-2">
            {positives.map((positive, i) => (
              <li
                key={i}
                className="flex gap-2 rounded-lg bg-green-50 border border-green-100 px-4 py-2.5 text-sm text-green-800"
              >
                <span className="shrink-0">✓</span>
                <span>{positive}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Alternatives */}
      {alternatives.length > 0 && (
        <div>
          <h3 className="text-lg font-semibold text-gray-900 mb-2">Альтернативы</h3>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {alternatives.map((alt) => (
              <div
                key={alt.pet_type}
                className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm"
              >
                <h4 className="font-semibold text-gray-900">{alt.name}</h4>
                <ul className="mt-2 space-y-1">
                  {alt.why.map((reason, i) => (
                    <li key={i} className="text-sm text-gray-600">
                      • {reason}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}

      <button
        onClick={onReset}
        className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-semibold text-gray-700 hover:bg-gray-50 transition-colors"
      >
        Заполнить заново
      </button>
    </div>
  )
}
