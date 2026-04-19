import { CoverageWidget } from '../components/CoverageWidget'
import { DisputeForm } from '../components/DisputeForm'
import { PageSection } from '../components/PageSection'

export function CoveragePage() {
  return (
    <PageSection
      title="Coverage & Disputes"
      description="Coverage is surfaced directly inside each signal request, but this page is still useful for demo framing."
    >
      <CoverageWidget />
      <div className="mt-4">
        <DisputeForm
          developerAddress="0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
          onSubmit={async () => {
            return
          }}
        />
      </div>
    </PageSection>
  )
}
