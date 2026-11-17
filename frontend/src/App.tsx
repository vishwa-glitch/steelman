import { BrowserRouter, Route, Routes, useParams } from 'react-router-dom'
import { Layout } from './components/Layout'
import { DebatePage } from './pages/DebatePage'
import { Home } from './pages/Home'
import { HowPage } from './pages/HowPage'
import { JudgePage } from './pages/JudgePage'
import { RecordedPage, SharedPage } from './pages/ReadOnly'

/** A new debate id gets a fresh page, so nothing in flight for one debate can land on another. */
function DebateRoute() {
  const { id } = useParams()
  return <DebatePage key={id} />
}

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/debate/:id" element={<DebateRoute />} />
          <Route path="/d/:slug" element={<SharedPage />} />
          <Route path="/how" element={<HowPage />} />
          <Route path="/judge" element={<JudgePage />} />
          <Route path="/recorded/:key" element={<RecordedPage />} />
          <Route path="*" element={<p>Page not found.</p>} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
