# Приемка по `тзЛабы4.txt`

## Автоматические проверки

Запуск из корня проекта:

```powershell
cd backend
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q .
alembic upgrade head
cd ../frontend
npm ci
npm run build
```

Backend HTTP-тесты проверяют регистрацию с безопасной ролью `viewer`, вход, refresh-ротацию, logout и отзыв refresh-токена, ответы `401/403/409/422`, trace id, заголовки ответа, CRUD мероприятий и CRUD пользователей. Frontend build выполняет TypeScript-проверку и production-сборку SPA.

## Сценарий демонстрации

1. Запустить `docker compose up --build` и открыть `http://localhost:8080`.
2. Открыть `/register`, создать пользователя и убедиться, что после входа доступна роль `viewer`.
3. Войти под `admin@example.com` / `Admin1234!`, открыть dashboard и проверить статистику.
4. На странице мероприятий создать запись, изменить ее, применить фильтр/дату, перейти по страницам и отменить запись.
5. На странице инцидентов создать запись, открыть детали, изменить статус с комментарием, отредактировать и удалить ее администратором.
6. На странице пользователей применить фильтр роли, создать, изменить, деактивировать и удалить пользователя.
7. В DevTools проверить, что access token отсутствует в `localStorage` и `sessionStorage`, а refresh cookie имеет `HttpOnly` и `SameSite=Strict`.
8. Открыть недоступный раздел ролью `viewer` и убедиться в уведомлении `Недостаточно прав`; удалить access token и проверить переход на `/login` с сохранением маршрута.

## Матрица соответствия

| Требование общего ТЗ | Реализация |
| --- | --- |
| БД и связи | SQLAlchemy-модели, PostgreSQL в Compose, Alembic, FK, индексы, `end_dt > start_dt` |
| REST GET/POST/PUT/DELETE | FastAPI routers для мероприятий, инцидентов и пользователей |
| Регистрация и вход | `/auth/register`, `/auth/login`, bcrypt, JWT |
| Защищенные ресурсы | Bearer access token, RBAC, проверка владельца |
| Продление сессии | HttpOnly refresh cookie, ротация и отзыв |
| SPA и routing | React, Vite, React Router, protected routes |
| Работа с данными | Списки, детали инцидента, добавление, изменение, удаление |
| Фильтрация и пагинация | Server-side query params и UI Pagination для мероприятий, инцидентов, пользователей |
| Ошибки | Единый JSON error-контракт, toast, перехват `401/403`, trace id |
| XSS/CSRF | React text rendering, CSP, HttpOnly/SameSite cookie, ограниченный CORS |
| Деплой и CI | Docker Compose и GitHub Actions на push/PR |

Скриншоты демонстрации следует сохранить в отчет после прохождения сценария выше. Приложение не генерирует фиктивные скриншоты автоматически, поскольку они должны показывать фактический запуск в браузере.
