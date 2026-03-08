import { useState } from 'react'
import QuestionnaireForm from '../components/QuestionnaireForm'
import EvaluationResult from '../components/EvaluationResult'

export default function EvaluatePage() {
  const [result, setResult] = useState(null)

  if (result) {
    return <EvaluationResult result={result} onReset={() => setResult(null)} />
  }

  return <QuestionnaireForm onSubmit={setResult} />
}
