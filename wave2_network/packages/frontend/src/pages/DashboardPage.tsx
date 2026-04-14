import { MetricChart } from '../components/MetricChart'
import { PageSection } from '../components/PageSection'

export function DashboardPage() {
  return (
    <PageSection title="Dashboard" description="Developer dashboard route scaffold.">
      <MetricChart />
    </PageSection>
  )
}
