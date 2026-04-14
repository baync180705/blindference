import { InferenceForm } from '../components/InferenceForm'
import { PageSection } from '../components/PageSection'
import { WalletConnect } from '../components/WalletConnect'

export function InferenceNewPage() {
  return (
    <PageSection title="Run Inference" description="Inference submission route scaffold.">
      <div className="mb-4">
        <WalletConnect />
      </div>
      <InferenceForm />
    </PageSection>
  )
}
