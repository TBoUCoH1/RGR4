import { FormEvent, useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ArrowRight, Eye, EyeOff, Shield } from 'lucide-react'
import { authApi } from '../api'
import { useAuthStore } from '../store'

export default function LoginPage() {
  const [email, setEmail] = useState(''); 
  const [password, setPassword] = useState(''); 
  const [show, setShow] = useState(false); 
  const [error, setError] = useState(''); 
  const [loading, setLoading] = useState(false); 
  const navigate = useNavigate(); 
  const location = useLocation(); 
  const setSession = useAuthStore((s) => s.setSession)
  const submit = async (event: FormEvent) => { 
  event.preventDefault(); 
  setError('');
  if (!email.trim() || !password.trim()) {
    setError('Пожалуйста, введите email и пароль');
    return;
  }
  setLoading(true);
    
    try { const data = await authApi.login(email, password); setSession(data.access_token, data.user); navigate((location.state as { from?: string } | null)?.from || '/', { replace: true }) } catch { setError('Не удалось войти. Проверьте email и пароль.') } finally { setLoading(false) } }
  return (
  <div className="login-page">
    <div className="login-visual">
      <div className="visual-grid" />
      <div className="login-visual-content">
        <div className="brand brand-large">
          <span className="brand-mark"><Shield size={24} /></span>
          <span>ЗПКиРИ<small>КООРДИНАЦИЯ БЕЗОПАСНОСТИ</small></span>
        </div>
        <div className="visual-copy">
          <p className="eyebrow">Центр координации</p>
          <h1>Контроль<br /><em>инцидентов.</em></h1>
          <p>Безопасность начинается здесь.</p>
        </div>
      </div>
    </div>
    <div className="login-panel">
      <div className="login-form-wrap">
        <p className="eyebrow">Защищённый доступ</p>
        <h2>Добро пожаловать</h2>
        <p className="muted">Войдите в операционную панель ЗПКиРИ</p>
        <form onSubmit={submit}>
          <label>Email
            <input 
              type="email" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)} 
              placeholder="Введите email"
            />
          </label>
          <label>Пароль
            <div className="input-icon">
              <input 
                type={show ? 'text' : 'password'} 
                value={password} 
                onChange={(e) => setPassword(e.target.value)} 
                placeholder="Введите пароль"
              />
              <button type="button" onClick={() => setShow(!show)} aria-label="Показать пароль">
                {show ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </div>
          </label>
          {error && <div className="form-error">{error}</div>}
          <button className="button button-primary button-wide" disabled={loading}>
            {loading ? 'Проверка доступа...' : <>Войти в систему <ArrowRight size={17} /></>}
          </button>
        </form>
        <Link className="text-link register-link" to="/register">Создать учётную запись</Link>
        <div className="demo-hint">
          <span>Демо-доступ</span>
          <code>admin@example.com</code>
          <code>Admin1234!</code>
        </div>
        <p className="login-legal">
          Доступ только для авторизованных сотрудников.<br />
          Все действия записываются в журнал аудита.
        </p>
      </div>
    </div>
  </div>
);
}
