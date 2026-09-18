# Портал координации инцидентов

Защищённый SPA-портал для планирования мероприятий и координации реагирования на инциденты безопасности. Система объединяет календарь мероприятий, уровни угроз, журнал инцидентов, карту с геопозициями и управление пользователями. Интерфейс рассчитан на диспетчера и сотрудников оперативной группы: данные представлены в виде сводки, списков с фильтрами и карточек деталей.

Проект выполнен в рамках лабораторной работы №4 «Безопасность мероприятий». В репозитории находится рабочий вертикальный срез: аутентификация, RBAC, мероприятия, инциденты, карта и административное управление пользователями. Названия ролей в текущей реализации используют `coordinator` вместо `organizer`, чтобы совпадать с backend-моделями и frontend-типами.

## Возможности

- JWT access token в памяти Zustand и refresh token в `HttpOnly` cookie с ротацией и отзывом.
- Хеширование паролей bcrypt с cost factor 12.
- RBAC для администратора, координатора, сотрудника охраны, аналитика и наблюдателя.
- Dashboard со статистикой мероприятий и открытых инцидентов.
- Создание, просмотр, фильтрация, обновление и отмена мероприятий.
- Регистрация инцидентов с severity, статусами `open -> investigating -> resolved -> closed`, комментарием и координатами.
- Журнал аудита действий пользователей.
- Команды реагирования и зоны мероприятия как связанные доменные сущности.
- Интерактивная карта Leaflet с тайлами OpenStreetMap и маркерами инцидентов из `GET /api/v1/incidents/map`.
- Адаптивный React-интерфейс с защищёнными маршрутами, обработкой 401/403 и автоматическим обновлением access token.
- Docker Compose для повторяемого запуска и GitHub Actions для проверок Python, TypeScript и Docker-сборок.

## Архитектура

```text
Браузер
  |
  +-- React 18 + TypeScript + Vite + React Router
  |     Zustand, TanStack Query, Axios, React Leaflet
  |
  +-- Nginx (production static files, /api reverse proxy)
        |
        +-- FastAPI REST API (/api/v1)
              |
              +-- SQLAlchemy 2 + psycopg2
                    |
                    +-- PostgreSQL 15+
```

В Docker Compose frontend доступен на `http://localhost:8080`, а nginx проксирует `/api/` в backend. Backend доступен напрямую на `http://localhost:8000`; это удобно для Swagger и разработки. По умолчанию Compose использует PostgreSQL. При локальном запуске backend без переменных окружения используется SQLite-файл `incident_portal.db`.

### Структура

```text
backend/
  app/
    main.py              # FastAPI и dashboard
    database.py          # SQLAlchemy engine и сессии
    models.py            # ORM-сущности и enum-значения
    schemas.py           # Pydantic request/response схемы
    security.py          # JWT и bcrypt
    deps.py              # текущий пользователь и RBAC
    routers/             # auth, events, incidents, users
  seed.py                # безопасное начальное заполнение
  tests/test_smoke.py    # import/schema smoke-проверки
frontend/
  src/
    pages/               # экраны портала
    components/          # shell, карта, modal, заголовки
    api.ts               # Axios API-клиент и refresh interceptor
    store.ts             # access token и пользовательская сессия
  Dockerfile
  nginx.conf
docker-compose.yml
.github/workflows/ci.yml
```

## Сущности

| Сущность | Назначение и основные связи |
| --- | --- |
| `users` | Пользователи, email, имя, роль, активность и даты. Один пользователь создаёт мероприятия и сообщает об инцидентах. |
| `events` | Мероприятия с периодом, местом, статусом, уровнем угрозы и автором. |
| `incidents` | Инциденты мероприятия с severity, статусом, описанием, координатами и результатом разрешения. |
| `incident_updates` | Хронология изменения статуса и комментариев по инциденту. |
| `event_areas` | Именованные зоны мероприятия с координатами и радиусом. Используются для отображения контекста на карте. |
| `response_teams` | Команды реагирования мероприятия, руководитель и контакт. |
| `refresh_tokens` | Хеши refresh token, срок действия и признак отзыва. |
| `audit_logs` | Кто, когда и какое действие выполнил над сущностью; пароль и токены не записываются. |

Сущности `participants`, `access_logs` и `threat_assessments` присутствуют в исходном техническом задании как следующий этап расширения схемы. В текущем рабочем срезе для них нет ORM-моделей и API-роутов, поэтому они не выдаются за реализованную функциональность.

## Роли и доступ

| Роль | Назначение | Реализованный доступ |
| --- | --- | --- |
| `admin` | Администрирование портала | Полный доступ к мероприятиям, инцидентам и пользователям; создание пользователей, активация/деактивация, удаление. |
| `coordinator` | Координация мероприятий | Создание мероприятий; редактирование своих мероприятий, зон и команд; обновление инцидента, если пользователь является автором. |
| `security_officer` | Регистрация событий безопасности | Просмотр данных и создание инцидентов. |
| `analyst` | Анализ и контроль статусов | Просмотр данных и продвижение статуса инцидента. |
| `viewer` | Наблюдение | Только чтение доступных данных и карты. |

Backend проверяет роль через dependency `require_role` и дополнительно проверяет владельца мероприятия или автора инцидента, где это требуется. Frontend скрывает административные разделы, однако окончательное решение о доступе всегда принимает API.

## API

Базовый адрес: `/api/v1`. Полная интерактивная схема доступна в Swagger после запуска по адресу [`http://localhost:8000/docs`](http://localhost:8000/docs).

### Аутентификация

| Метод | Endpoint | Назначение |
| --- | --- | --- |
| `POST` | `/auth/login` | Проверка email/пароля, выдача access token и refresh cookie. |
| `POST` | `/auth/refresh` | Ротация refresh token и выдача нового access token. |
| `POST` | `/auth/logout` | Отзыв refresh token и удаление cookie. |
| `GET` | `/auth/me` | Текущий пользователь. |
| `POST` | `/auth/register` | Регистрация пользователя. Без токена создаётся только роль `viewer`; администратор может выбрать роль. |

### Мероприятия и dashboard

| Метод | Endpoint | Назначение |
| --- | --- | --- |
| `GET` | `/dashboard`, `/dashboard/stats` | Число мероприятий, активных мероприятий, инцидентов и открытых инцидентов. |
| `GET` | `/events` | Список с фильтрами `status`, `threat_level`, `date`, `skip`, `limit`. |
| `POST` | `/events` | Создать мероприятие. |
| `GET` | `/events/{id}` | Получить мероприятие. |
| `PUT`, `PATCH` | `/events/{id}` | Полное или частичное обновление. |
| `DELETE` | `/events/{id}` | Мягкая отмена: статус `cancelled`. |
| `GET` | `/events/{id}/incidents` | Инциденты мероприятия. |
| `GET` | `/events/{id}/stats` | Счётчики инцидентов мероприятия. |
| `GET`, `POST` | `/events/{id}/areas`, `/events/{id}/teams` | Просмотр и добавление зон или команд. |

### Инциденты и пользователи

| Метод | Endpoint | Назначение |
| --- | --- | --- |
| `GET` | `/incidents` | Список с фильтрами `event_id`, `severity`, `status`, `skip`, `limit`. |
| `GET` | `/incidents/map` | Инциденты, у которых заданы latitude/longitude. |
| `POST` | `/incidents` | Создать инцидент сотруднику охраны или администратору. |
| `GET` | `/incidents/{id}` | Детали и хронология обновлений. |
| `PUT` | `/incidents/{id}` | Изменить данные инцидента с проверкой владельца. |
| `PATCH` | `/incidents/{id}/status` | Продвинуть статус и добавить комментарий/решение. |
| `DELETE` | `/incidents/{id}` | Удалить инцидент администратору. |
| `GET` | `/users` | Список пользователей администратору с фильтром `role` и пагинацией `skip`, `limit`. |
| `POST` | `/users` | Создать пользователя. |
| `GET` | `/users/{id}` | Получить пользователя. |
| `PUT` | `/users/{id}` | Обновить профиль, роль или пароль. |
| `PATCH` | `/users/{id}/deactivate` | Переключить активность пользователя. |
| `DELETE` | `/users/{id}` | Удалить пользователя, кроме собственной учётной записи. |

Ошибки валидации и конфликты возвращаются с JSON-объектом `error` и кодами `VALIDATION_ERROR` или `CONFLICT`; стандартные ошибки доступа используют HTTP `401`, `403`, `404`, `409` и `422`.

## Карта OpenStreetMap

`MapView` использует Leaflet и официальный публичный URL тайлов `https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png` с атрибуцией `OpenStreetMap contributors`. Экран карты запрашивает `/api/v1/incidents/map`, показывает только записи с обеими координатами, автоматически подбирает границы и выводит severity/status в popup. Для production-среды необходимо учитывать [политику использования тайлов OSM](https://operations.osmfoundation.org/policies/tiles/) и при высокой нагрузке выбрать подходящий tile provider.

## Запуск через Docker Compose

Требования: Docker Desktop с Compose v2.

1. Скопируйте `.env.example` в `.env` и замените `POSTGRES_PASSWORD` и `SECRET_KEY` на собственные значения.
2. Выполните из корня проекта:

   ```bash
   docker compose up --build
   ```

3. Откройте [`http://localhost:8080`](http://localhost:8080). API и Swagger доступны по [`http://localhost:8000/docs`](http://localhost:8000/docs), проверка состояния: [`http://localhost:8000/health`](http://localhost:8000/health).
4. Для остановки используйте `Ctrl+C`. Для фонового режима: `docker compose up --build -d`; логи: `docker compose logs -f backend`.
5. Для полного удаления данных PostgreSQL: `docker compose down -v`.

Перед запуском API контейнер выполняет `alembic upgrade head`, после чего приложение проверяет наличие таблиц и один раз добавляет администратора и демонстрационное мероприятие. Первая миграция использует ORM-модели как единственный источник схемы, поэтому PostgreSQL ENUM-типы совпадают с runtime-кодом.

## Локальная разработка без Compose

Backend:

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Frontend в другом терминале:

```bash
cd frontend
npm ci
# Windows PowerShell: $env:VITE_API_URL="http://localhost:8000/api/v1"
npm run dev
```

После старта Vite откройте [`http://localhost:5173`](http://localhost:5173). Для локального backend без `DATABASE_URL` используется `backend/incident_portal.db`; этот файл игнорируется Git.

## Демонстрационный вход

| Поле | Значение |
| --- | --- |
| Email | `admin@example.com` |
| Пароль | `Admin1234!` |
| Роль | `admin` |

Учётная запись создаётся seed-скриптом только если база пуста. Демонстрационный пароль предназначен исключительно для лабораторной демонстрации и должен быть заменён в реальной среде.

## Проверки

Backend smoke- и HTTP-тесты используют изолированную SQLite-базу и запускаются стандартным модулем Python:

```bash
cd backend
python -m unittest discover -s tests -p "test_*.py" -v
python -m compileall -q .
alembic upgrade head
```

Frontend type-check и production build:

```bash
cd frontend
npm ci
npm run build
```

GitHub Actions (`.github/workflows/ci.yml`) запускает эти проверки на `push`/`pull_request` в `main` и `develop`, после чего собирает оба Docker-образа. `test_api.py` проверяет реальные HTTP-сценарии регистрации, входа, refresh-ротации, `401`, `403` и CRUD мероприятий; `test_smoke.py` проверяет импорт приложения, маршруты, модели и ключевую валидацию Pydantic.

## Безопасность и обработка ошибок

- Access token хранится только в памяти Zustand. `localStorage` сохраняет токен между перезапусками, но доступен JavaScript и поэтому увеличивает последствия XSS; поэтому в проекте он не используется.
- Refresh token хранится только в БД в виде bcrypt-хеша и передаётся браузеру в cookie с `HttpOnly`, `SameSite=Strict`, ограниченным путем `/api/v1/auth` и сроком жизни 7 дней. Для production включается `COOKIE_SECURE=true` только при HTTPS; локальный HTTP Compose оставляет его `false`.
- React выводит пользовательские значения как текст, не использует `dangerouslySetInnerHTML`, а production nginx задаёт CSP, `X-Content-Type-Options`, `X-Frame-Options` и `Referrer-Policy`.
- `SameSite=Strict` снижает CSRF-риск для refresh cookie; state-changing API дополнительно требуют Bearer access token. В production следует использовать HTTPS и ограниченный `ALLOWED_ORIGINS`.
- Все входные данные проходят Pydantic-валидацию. Ошибки возвращаются в едином формате `error.code`, `error.message`, `error.details`, `error.trace_id` со статусами `401`, `403`, `404`, `409`, `422` и `500`.
- Сервер пишет структурированные JSON-логи в stdout. В ошибках фиксируются timestamp, level, message, path, user_id и trace_id; пароли и токены в логи не попадают.

## Состояние для сдачи

Готовы к демонстрации: регистрация и вход, защищённый выход, refresh-ротация, RBAC, dashboard, фильтрация и пагинация, CRUD-поток мероприятий, CRUD-инцидентов, CRUD пользователей, смена статусов инцидентов, журнал аудита, карта OSM, Docker Compose, health endpoint, README и CI с backend/frontend/docker jobs.

Для production-режима следует добавить участников и контроль проходов, оценки угроз, полноценные интеграционные тесты с PostgreSQL, строгие secrets, HTTPS и `COOKIE_SECURE=true`. Для лабораторной работы текущий вертикальный срез уже включает миграцию, seed, API, UI и карту.
