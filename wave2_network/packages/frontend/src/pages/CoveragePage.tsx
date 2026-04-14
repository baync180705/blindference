import { CoverageWidget } from '../components/CoverageWidget'
import { DisputeForm } from '../components/DisputeForm'
import { PageSection } from '../components/PageSection'

export function CoveragePage() {
  return (
    <PageSection title="Coverage & Disputes" description="Coverage route scaffold.">
      <CoverageWidget />
      <div className="mt-4">
        <DisputeForm />
      </div>
    </PageSection>
  )
}
