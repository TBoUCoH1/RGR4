import { FormEvent, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRight, Eye, EyeOff, KeyRound, Shield } from 'lucide-react'
import { authApi } from '../api'
import { useAuthStore } from '../store'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [requires2FA, setRequires2FA] = useState(false)
  const [show, setShow] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const navigate = useNavigate()
  const location = useLocation()
  const setSession = useAuthStore((s) => s.setSession)

  const submit = async (event: FormEvent) => {
    event.preventDefault()
    setError('')

    if (!email.trim() || !password.trim()) {
      setError('Пожалуйста, введите email и пароль')
      return
    }

    if (requires2FA && code.trim().length !== 6) {
      setError('Введите 6-значный код из приложения аутентификации')
      return
    }

    setLoading(true)

    try {
      const data = await authApi.login(email.trim(), password, requires2FA ? code.trim() : undefined)
      setSession(data.access_token, data.user)
      navigate((location.state as { from?: string } | null)?.from || '/', { replace: true })
    } catch (err: any) {
      if (err.response?.status === 403 && err.response?.data?.detail === 'totp_required') {
        setRequires2FA(true)
        setError('')
      } else if (err.response?.status === 401 && err.response?.data?.detail === 'Invalid 2FA code') {
        setError('Неверный код 2ФА. Проверьте время на устройстве и повторите ввод.')
      } else {
        setError('Не удалось войти. Проверьте email и пароль.')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleReset2FA = () => {
    setRequires2FA(false)
    setCode('')
    setError('')
  }

  return (
    <div className="login-page">
      <div className="login-visual">
        <div className="visual-grid" />
        <div className="login-visual-content">
          <div className="brand brand-large">
            <span className="brand-mark">
              <Shield size={24} />
            </span>
            <span>
              ЗПКиРИ<small>КООРДИНАЦИЯ БЕЗОПАСНОСТИ</small>
            </span>
          </div>
          <div className="visual-copy">
            <p className="eyebrow">Центр координации</p>
            <h1>
              Контроль
              <br />
              <em>инцидентов.</em>
            </h1>
            <p>Безопасность начинается здесь.</p>
          </div>
        </div>
      </div>

      <div className="login-panel">
        <div className="login-form-wrap">
          <p className="eyebrow">Защищённый доступ</p>
          <h2>{requires2FA ? 'Второй фактор (2FA)' : 'Добро пожаловать'}</h2>
          <p className="muted">
            {requires2FA
              ? 'Введите 6-значный одноразовый код из Google Authenticator или 2FAS'
              : 'Войдите в операционную панель ЗПКиРИ'}
          </p>

          <form onSubmit={submit}>
            {!requires2FA ? (
              <>
                <label>
                  Email
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="Введите email"
                  />
                </label>
                <label>
                  Пароль
                  <div className="input-icon">
                    <input
                      type={show ? 'text' : 'password'}
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Введите пароль"
                    />
                    <button type="button" onClick={() => setShow(!show)} aria-label="Показать пароль">
                      {show ? <EyeOff size={17} /> : <Eye size={17} />}
                    </button>
                  </div>
                </label>
              </>
            ) : (
              <>
                <label>
                  Код подтверждения
                  <div className="input-icon">
                    <input
                      type="text"
                      inputMode="numeric"
                      pattern="[0-9]*"
                      maxLength={6}
                      autoFocus
                      required
                      value={code}
                      onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                      placeholder="000000"
                      style={{ letterSpacing: '0.3em', textAlign: 'center', fontSize: '1.25rem', fontWeight: 700 }}
                    />
                    <span>
                      <KeyRound size={17} />
                    </span>
                  </div>
                </label>
                <button
                  type="button"
                  className="button button-ghost button-wide"
                  style={{ marginBottom: '0.75rem' }}
                  onClick={handleReset2FA}
                >
                  ← Назад к вводу пароля
                </button>
              </>
            )}

            {error && <div className="form-error">{error}</div>}

            <button className="button button-primary button-wide" disabled={loading}>
              {loading ? (
                'Проверка доступа...'
              ) : (
                <>
                  {requires2FA ? 'Подтвердить код' : 'Войти в систему'} <ArrowRight size={17} />
                </>
              )}
            </button>
          </form>

          {!requires2FA && (
            <>
              <Link className="text-link register-link" to="/register">
                Создать учётную запись
              </Link>
              <div className="demo-hint">
                <span>Демо-доступ</span>
                <code>admin@example.com</code>
                <code>Admin1234!</code>
              </div>
            </>
          )}

          <p className="login-legal">
            Доступ только для авторизованных сотрудников.
            <br />
            Все действия записываются в журнал аудита.
          </p>
        </div>
      </div>
    </div>
  )
}