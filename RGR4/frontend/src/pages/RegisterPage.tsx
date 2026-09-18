import { FormEvent, useState } from 'react'
import { ArrowLeft, UserPlus } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { authApi } from '../api'
import { notify } from '../components/ToastHost'

export default function RegisterPage() {
  const [form, setForm] = useState({ full_name: '', email: '', password: '', confirm: '' })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const set = (key: string, value: string) => setForm((current) => ({ ...current, [key]: value }))
  const submit = async (event: FormEvent) => {
    event.preventDefault()
    if (form.password !== form.confirm) return setError('Пароли не совпадают.')
    setError('')
    setLoading(true)
    try {
      await authApi.register({ full_name: form.full_name, email: form.email, password: form.password })
      notify('Учётная запись создана. Теперь войдите в систему.', 'success')
      navigate('/login', { replace: true })
    } catch {
      setError('Регистрация не выполнена. Проверьте введённые данные.')
    } finally {
      setLoading(false)
    }
  }
  return <div className="login-page"><div className="login-visual"><div className="visual-grid" /><div className="login-visual-content"><div className="visual-copy"><p className="eyebrow">Новая учётная запись</p><h1>Доступ к системе.<br /><em>Под контролем.</em></h1><p>Самостоятельная регистрация создаёт профиль наблюдателя.</p></div></div></div><div className="login-panel"><div className="login-form-wrap"><Link className="back-link" to="/login"><ArrowLeft size={15} /> Вернуться ко входу</Link><p className="eyebrow">Регистрация</p><h2>Создать профиль</h2><p className="muted">Администратор сможет изменить роль после регистрации</p><form onSubmit={submit}><label>Имя и фамилия<input required value={form.full_name} onChange={(event) => set('full_name', event.target.value)} /></label><label>Email<input required type="email" value={form.email} onChange={(event) => set('email', event.target.value)} /></label><label>Пароль<input required minLength={8} type="password" value={form.password} onChange={(event) => set('password', event.target.value)} placeholder="Не менее 8 символов и цифра" /></label><label>Повторите пароль<input required minLength={8} type="password" value={form.confirm} onChange={(event) => set('confirm', event.target.value)} /></label>{error && <div className="form-error">{error}</div>}<button className="button button-primary button-wide" disabled={loading}><UserPlus size={17} /> {loading ? 'Создание...' : 'Зарегистрироваться'}</button></form></div></div></div>
}
