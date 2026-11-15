import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

export function Layout({ children }: { children: ReactNode }) {
  return (
    <>
      <header className="site-head">
        <Link to="/" className="wordmark">
          Steelman
        </Link>
        <nav>
          <Link to="/">Debate</Link>
          <Link to="/judge">Judge report card</Link>
        </nav>
      </header>
      <main>{children}</main>
      <footer className="site-foot">
        <p>
          Steelman is a practice tool. The AI's arguments are not fact-checked, and the judge scores how well a
          case is argued, not whether it is true.
        </p>
      </footer>
    </>
  )
}
