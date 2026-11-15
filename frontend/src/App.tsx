import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { DebatePage } from './pages/DebatePage'
import { Home } from './pages/Home'
import { JudgePage } from './pages/JudgePage'
import { RecordedPage, SharedPage } from './pages/ReadOnly'

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/debate/:id" element={<DebatePage />} />
          <Route path="/d/:slug" element={<SharedPage />} />
          <Route path="/judge" element={<JudgePage />} />
          <Route path="/recorded/:key" element={<RecordedPage />} />
          <Route path="*" element={<p>Page not found.</p>} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}
