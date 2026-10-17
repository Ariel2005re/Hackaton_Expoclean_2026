import { NavLink, Outlet } from 'react-router-dom'

const links = [
  { to: '/nueva', label: 'Nueva cotización' },
  { to: '/borradores', label: 'Borradores' },
  { to: '/configuracion', label: 'Configuración' },
  { to: '/historial', label: 'Historial' },
]

export default function Layout() {
  return (
    <div className="app-shell">
      <nav aria-label="Navegación principal">
        <ul>
          {links.map((link) => (
            <li key={link.to}>
              <NavLink
                to={link.to}
                className={({ isActive }) => (isActive ? 'active' : undefined)}
              >
                {link.label}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <main>
        <Outlet />
      </main>
    </div>
  )
}
