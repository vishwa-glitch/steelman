import type { ReactNode } from 'react'
import { NavLink, Link } from 'react-router-dom'

export const REPO_URL = 'https://github.com/vishwa-glitch/steelman'

export function Layout({ children }: { children: ReactNode }) {
  const cls = ({ isActive }: { isActive: boolean }) => (isActive ? 'nav-btn on' : 'nav-btn')
  return (
    <>
      <header className="top">
        <Link to="/" className="mark" aria-label="Steelman, home">
          <span className="logo" aria-hidden="true">
            ◎
          </span>
          Steelman
        </Link>
        <nav aria-label="Main">
          <NavLink to="/" end className={cls}>
            Debate
          </NavLink>
          <NavLink to="/judge" className={cls}>
            Judge report card
          </NavLink>
          <a className="nav-btn" href={REPO_URL} target="_blank" rel="noreferrer">
            Code
          </a>
        </nav>
      </header>
      <main>{children}</main>
      <footer className="foot">
        <p>
          Steelman is a practice tool. The AI's arguments are not fact-checked, and the judge scores how well a case is
          argued, not whether it is true.
        </p>
        <p>
          <a href={REPO_URL} target="_blank" rel="noreferrer">
            Source code on GitHub
          </a>
        </p>
      </footer>
    </>
  )
}
