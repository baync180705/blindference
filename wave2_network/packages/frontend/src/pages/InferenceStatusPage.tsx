import { PageSection } from '../components/PageSection'
import { QuorumVisualizer } from '../components/QuorumVisualizer'
import { ResultViewer } from '../components/ResultViewer'

export function InferenceStatusPage() {
  return (
    <PageSection title="Inference Status" description="Inference status route scaffold.">
      <QuorumVisualizer />
      <div className="mt-4">
        <ResultViewer />
      </div>
    </PageSection>
  )
}
