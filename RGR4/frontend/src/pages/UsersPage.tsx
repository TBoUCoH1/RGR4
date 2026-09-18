import React, { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2, Edit3, Plus, RefreshCw, ShieldCheck, Trash2 } from 'lucide-react'
import { usersApi, fetchAuditLogs, type AuditLogItem } from '../api'
import { notify } from '../components/ToastHost'
import Pagination from '../components/Pagination'
import Modal from '../components/Modal'
import PageHeader from '../components/PageHeader'
import type { User, UserRole } from '../types'

const roles: Record<UserRole, string> = {
  admin: 'Администратор',
  coordinator: 'Координатор',
  security_officer: 'Безопасность',
  analyst: 'Аналитик',
  viewer: 'Наблюдатель',
}
type UserForm = { full_name: string; email: string; role: UserRole; password?: string }

export default function UsersPage() {
  const [role, setRole] = useState<UserRole | ''>('')
  const [page, setPage] = useState({ skip: 0, limit: 10 })
  const [editing, setEditing] = useState<User | null>(null)
  const [creating, setCreating] = useState(false)
  const qc = useQueryClient()

  const query = useQuery({
    queryKey: ['users', role, page],
    queryFn: () => usersApi.list({ role: role || undefined, ...page }),
  })

  const create = useMutation({
    mutationFn: usersApi.create,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setCreating(false)
      notify('Пользователь создан', 'success')
    },
  })

  const update = useMutation({
    mutationFn: ({ id, data }: { id: number; data: UserForm }) => usersApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setEditing(null)
      notify('Пользователь обновлён', 'success')
    },
  })

  const toggle = useMutation({
    mutationFn: usersApi.toggle,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      notify('Статус пользователя изменён', 'success')
    },
  })

  const remove = useMutation({
    mutationFn: usersApi.remove,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      notify('Пользователь удалён', 'success')
    },
  })

  if (query.isLoading) {
    return (
      <div className="page">
        <div className="loading">Загрузка пользователей...</div>
      </div>
    )
  }

  return (
    <div className="page">
      <PageHeader
        eyebrow="Управление / Доступ"
        title="Пользователи и безопасность"
        description="Управление учетными записями, ролевым доступом и аудит действий"
        action={
          <button className="button button-primary" onClick={() => setCreating(true)}>
            <Plus size={17} /> Добавить пользователя
          </button>
        }
      />

      <section className="panel filter-panel">
        <strong>Фильтр по роли</strong>
        <select
          value={role}
          onChange={(event) => {
            setRole(event.target.value as UserRole | '')
            setPage((current) => ({ ...current, skip: 0 }))
          }}
        >
          <option value="">Все роли</option>
          {Object.entries(roles).map(([key, label]) => (
            <option key={key} value={key}>
              {label}
            </option>
          ))}
        </select>
        <span className="filter-count">
          Найдено: <strong>{query.data?.total ?? 0}</strong>
        </span>
      </section>

      <section className="panel table-panel">
        <div className="users-summary">
          <div>
            <strong>{query.data?.total ?? '—'}</strong>
            <span>учётных записей</span>
          </div>
          <div>
            <CheckCircle2 size={17} />
            <span>Доступ контролируется политиками ролей</span>
          </div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Сотрудник</th>
                <th>Роль</th>
                <th>Статус</th>
                <th>Дата регистрации</th>
                <th>Действия</th>
              </tr>
            </thead>
            <tbody>
              {query.data?.items.map((person) => (
                <tr key={person.id}>
                  <td>
                    <div className="person-cell">
                      <span className="avatar avatar-table">{person.full_name.slice(0, 1).toUpperCase()}</span>
                      <span>
                        <strong>{person.full_name}</strong>
                        <small>{person.email}</small>
                      </span>
                    </div>
                  </td>
                  <td>
                    <span className="role-cell">
                      <ShieldCheck size={14} /> {roles[person.role]}
                    </span>
                  </td>
                  <td>
                    <button
                      className={person.is_active ? 'active-status status-button' : 'inactive-status status-button'}
                      onClick={() => toggle.mutate(person.id)}
                    >
                      <i /> {person.is_active ? 'Активен' : 'Отключён'}
                    </button>
                  </td>
                  <td className="muted">
                    {new Intl.DateTimeFormat('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' }).format(
                      new Date(person.created_at)
                    )}
                  </td>
                  <td>
                    <span className="event-actions">
                      <button className="icon-button" title="Редактировать пользователя" onClick={() => setEditing(person)}>
                        <Edit3 size={15} />
                      </button>
                      <button
                        className="icon-button danger"
                        title="Удалить пользователя"
                        onClick={() => window.confirm('Удалить пользователя?') && remove.mutate(person.id)}
                      >
                        <Trash2 size={15} />
                      </button>
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <Pagination
        skip={page.skip}
        limit={page.limit}
        total={query.data?.total || 0}
        onChange={(skip, limit) => setPage({ skip, limit })}
      />

      {/* Журнал аудита действий */}
      <AuditLogSection />

      {(creating || editing) && (
        <UserModal
          user={editing}
          loading={create.isPending || update.isPending}
          error={create.isError || update.isError}
          onClose={() => {
            setCreating(false)
            setEditing(null)
          }}
          onSubmit={(data) =>
            editing
              ? update.mutate({ id: editing.id, data })
              : create.mutate({
                  email: data.email,
                  full_name: data.full_name,
                  role: data.role,
                  password: data.password || '',
                })
          }
        />
      )}
    </div>
  )
}

function UserModal({
  user,
  onClose,
  onSubmit,
  loading,
  error,
}: {
  user: User | null
  onClose: () => void
  onSubmit: (data: UserForm) => void
  loading: boolean
  error: boolean
}) {
  const [form, setForm] = useState<UserForm>(
    user
      ? { full_name: user.full_name, email: user.email, role: user.role }
      : { full_name: '', email: '', role: 'viewer', password: '' }
  )
  const set = (key: keyof UserForm, value: string) => setForm((current) => ({ ...current, [key]: value }))

  return (
    <Modal
      eyebrow={user ? 'Доступ / Редактирование' : 'Доступ / Новая учётная запись'}
      title={user ? 'Изменить пользователя' : 'Добавить пользователя'}
      onClose={onClose}
    >
      <form
        className="modal-form"
        onSubmit={(event) => {
          event.preventDefault()
          onSubmit(form)
        }}
      >
        <label>
          Имя и фамилия
          <input required value={form.full_name} onChange={(event) => set('full_name', event.target.value)} />
        </label>
        <label>
          Email
          <input required type="email" value={form.email} onChange={(event) => set('email', event.target.value)} />
        </label>
        <label>
          Роль
          <select value={form.role} onChange={(event) => set('role', event.target.value as UserRole)}>
            {Object.entries(roles).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </label>
        <label>
          {user ? 'Новый пароль (необязательно)' : 'Пароль'}
          <input
            required={!user}
            minLength={8}
            type="password"
            value={form.password || ''}
            onChange={(event) => set('password', event.target.value)}
            placeholder="Не менее 8 символов и цифра"
          />
        </label>
        {error && <div className="form-error">Операция не выполнена. Проверьте данные и права.</div>}
        <div className="modal-actions">
          <button type="button" className="button button-ghost" onClick={onClose}>
            Отмена
          </button>
          <button className="button button-primary" disabled={loading}>
            {loading ? 'Сохранение...' : user ? 'Сохранить изменения' : 'Создать аккаунт'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

export const AuditLogSection: React.FC = () => {
  const [logs, setLogs] = useState<AuditLogItem[]>([])
  const [loading, setLoading] = useState(false)
  const [skip, setSkip] = useState(0)
  const [total, setTotal] = useState(0)
  const limit = 15

  const loadLogs = async (offset: number) => {
    setLoading(true)
    try {
      const data = await fetchAuditLogs(offset, limit)
      setLogs(data.items)
      setTotal(data.total)
      setSkip(data.skip)
    } catch (e) {
      console.error('Ошибка загрузки аудита', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLogs(0)
  }, [])

  return (
    <section className="panel table-panel" style={{ marginTop: '2rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <div>
          <h3 style={{ margin: 0 }}>Журнал событий безопасности (Audit Log)</h3>
          <small className="muted">Фиксация действий пользователей и попыток входа</small>
        </div>
        <button className="button button-ghost" onClick={() => loadLogs(skip)}>
          <RefreshCw size={14} /> Обновить
        </button>
      </div>

      {loading ? (
        <div className="loading">Загрузка журнала...</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Время (UTC)</th>
                <th>Инициатор</th>
                <th>Действие</th>
                <th>Объект</th>
                <th>IP-адрес</th>
              </tr>
            </thead>
            <tbody>
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ textAlign: 'center', padding: '1.5rem' }}>
                    Записей аудита пока нет
                  </td>
                </tr>
              ) : (
                logs.map((log) => (
                  <tr key={log.id}>
                    <td className="muted">{new Date(log.created_at).toLocaleString('ru-RU')}</td>
                    <td>
                      <strong>{log.actor_email || 'Система'}</strong>
                    </td>
                    <td>
                      <span
                        style={{
                          padding: '2px 8px',
                          borderRadius: '4px',
                          fontSize: '11px',
                          fontWeight: 600,
                          backgroundColor:
                            log.action.includes('failed') || log.action === 'delete' || log.action === 'cancel'
                              ? 'rgba(239, 68, 68, 0.15)'
                              : 'rgba(16, 185, 129, 0.15)',
                          color:
                            log.action.includes('failed') || log.action === 'delete' || log.action === 'cancel'
                              ? '#f87171'
                              : '#34d399',
                          border:
                            log.action.includes('failed') || log.action === 'delete' || log.action === 'cancel'
                              ? '1px solid rgba(239, 68, 68, 0.3)'
                              : '1px solid rgba(16, 185, 129, 0.3)',
                        }}
                      >
                        {log.action}
                      </span>
                    </td>
                    <td>
                      {log.entity_type} {log.entity_id ? `(#${log.entity_id})` : ''}
                    </td>
                    <td>
                      <code>{log.ip_address || '—'}</code>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ display: 'flex', gap: '8px', marginTop: '1rem', alignItems: 'center', justifyContent: 'flex-end' }}>
        <button
          className="button button-ghost"
          disabled={skip <= 0}
          onClick={() => loadLogs(Math.max(0, skip - limit))}
        >
          Назад
        </button>
        <span className="muted" style={{ fontSize: '13px' }}>
          Показано {logs.length} из {total}
        </span>
        <button
          className="button button-ghost"
          disabled={skip + limit >= total}
          onClick={() => loadLogs(skip + limit)}
        >
          Вперед
        </button>
      </div>
    </section>
  )
}