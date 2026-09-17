import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Activity, CalendarDays, ChevronRight, CircleUserRound, LayoutDashboard, LogOut, Map, Shield, Siren, UsersRound } from 'lucide-react'
import { authApi } from '../api'
import { useAuthStore } from '../store'
import type { UserRole } from '../types'
import { useQueryClient } from '@tanstack/react-query'

const roleLabels: Record<UserRole, string> = { admin: 'Администратор', coordinator: 'Координатор', security_officer: 'Сотрудник безопасности', analyst: 'Аналитик', viewer: 'Наблюдатель' }

export default function AppShell() {
  const { user, clear } = useAuthStore()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const logout = async () => { try { await authApi.logout() } finally { queryClient.clear(); clear(); navigate('/login') } }
  const canAdmin = user?.role === 'admin'
  return <div className="app-shell">
    <aside className="sidebar">
      <div className="brand"><span className="brand-mark"><Shield size={19} /></span><span>ЗПКиРИ<small>КООРДИНАЦИЯ БЕЗОПАСНОСТИ</small></span></div>
      <nav className="nav">
        <p className="nav-label">Операционный центр</p>
        <NavLink to="/" end><LayoutDashboard size={17} /> Обзор</NavLink>
        <NavLink to="/incidents"><Siren size={17} /> Инциденты</NavLink>
        <NavLink to="/map"><Map size={17} /> Карта обстановки</NavLink>
        <p className="nav-label">Управление</p>
        <NavLink to="/events"><CalendarDays size={17} /> Мероприятия</NavLink>
        {canAdmin && <NavLink to="/users"><UsersRound size={17} /> Пользователи</NavLink>}
      </nav>
      <div className="sidebar-bottom">
        <NavLink to="/profile"><CircleUserRound size={17} /> Профиль <ChevronRight size={14} className="push" /></NavLink>
        <button className="logout-link" onClick={logout}><LogOut size={17} /> Завершить сеанс</button>
        <div className="user-mini"><span className="avatar">{user?.full_name.slice(0, 1).toUpperCase()}</span><span><strong>{user?.full_name}</strong><small>{user && roleLabels[user.role]}</small></span></div>
      </div>
    </aside>
    <main className="main-content"><Outlet /></main>
  </div>
}
