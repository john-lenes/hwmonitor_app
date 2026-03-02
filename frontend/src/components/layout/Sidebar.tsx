import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  Wind,
  Settings,
  Cpu,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const navItems = [
  { to: '/dashboard', label: 'Painel',              icon: LayoutDashboard },
  { to: '/fans',      label: 'Perfis de Ventoinha', icon: Wind             },
  { to: '/settings',  label: 'Configurações',       icon: Settings         },
]

export default function Sidebar() {
  return (
    <aside className="flex h-screen w-56 flex-col border-r border-border bg-card">
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20">
          <Cpu className="h-5 w-5 text-primary" />
        </div>
        <span className="text-sm font-semibold tracking-wide text-foreground">
          HW Monitor
        </span>
      </div>

      <nav className="flex flex-1 flex-col gap-1 px-3 pt-2">
        {navItems.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                isActive
                  ? 'bg-primary/20 text-primary'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground',
              )
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-4 text-xs text-muted-foreground">v1.0.0</div>
    </aside>
  )
}
