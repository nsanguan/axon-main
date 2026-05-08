import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Axon Control Tower',
  description: 'Strategic Administration Dashboard for Axon ASCP',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen flex">
          {/* Sidebar */}
          <aside className="w-64 bg-axon-900 text-white flex flex-col">
            <div className="p-6 border-b border-axon-700">
              <h1 className="text-xl font-bold tracking-tight">Axon</h1>
              <p className="text-sm text-axon-300 mt-1">Control Tower</p>
            </div>
            <nav className="flex-1 p-4 space-y-1">
              <NavItem href="/" label="Dashboard" icon="📊" />
              <NavItem href="/weights" label="Strategic Weights" icon="⚖️" />
              <NavItem href="/plans" label="Plan History" icon="📋" />
              <NavItem href="/approvals" label="Pending Approvals" icon="⏳" />
            </nav>
            <div className="p-4 border-t border-axon-700 text-xs text-axon-400">
              Axon v0.0.2 — ASCP
            </div>
          </aside>

          {/* Main content */}
          <main className="flex-1 overflow-auto">
            <div className="p-8">
              {children}
            </div>
          </main>
        </div>
      </body>
    </html>
  )
}

function NavItem({ href, label, icon }: { href: string; label: string; icon: string }) {
  return (
    <a
      href={href}
      className="flex items-center gap-3 px-3 py-2.5 rounded-lg text-axon-200 hover:bg-axon-800 hover:text-white transition-colors text-sm font-medium"
    >
      <span className="text-lg">{icon}</span>
      {label}
    </a>
  )
}
