# PR2 Backend

Учебное веб-приложение для практической работы №2. Разворачивается в нескольких
идентичных экземплярах за reverse-proxy Apache/Nginx (лабораторная работа №3)
с балансировкой нагрузки, DNS-балансировкой, TLS/SSL-терминацией и обработкой
асинхронных запросов.

## Стек

- **FastAPI** — HTTP-фреймворк, асинхронный, легко масштабируется
- **PostgreSQL** — внешнее хранилище данных
- **Redis** — внешнее хранилище счётчиков и (при необходимости) сессий
- **Docker + docker-compose** — запуск двух и более идентичных нод

Все ноды одинаковые. Состояние — только в PostgreSQL и Redis.

## Соответствие ограничениям задания

1. **Идентификация узла** — эндпоинт `/whoami` и главная страница возвращают
   `instance_id`, `hostname`, `boot_uuid`, `pid`. Видно, какая нода ответила.
2. **Отказоустойчивое хранилище** — PostgreSQL и Redis вынесены в отдельные
   контейнеры. Все ноды ходят в одно хранилище, локальных файлов нет.
3. **Никакого TLS/SSL внутри приложения** — приложение слушает только HTTP.
   Сертификаты и HTTPS — задача Nginx/Apache в лабе №3.
4. **Сессии — только во внешнем хранилище** — счётчик визитов хранится в Redis,
   общий для всех нод. Локальной памяти/файлов нет.



### Описание файлов

| Файл                    | Что делает |
|-------------------------|-----------|
| `docker-compose.yml`    | Поднимает 4 контейнера: `db` (Postgres), `redis`, `app1`, `app2`. Каждой ноде задаёт свой `INSTANCE_ID` и одинаковые `DATABASE_URL`/`REDIS_URL`. |
| `Dockerfile`            | Собирает образ приложения: ставит зависимости, копирует `src`, запускает `uvicorn`. |
| `requirements.txt`      | Список Python-пакетов с фиксированными версиями. |
| `.env`                  | Значения переменных окружения для локального запуска. Внутрь контейнера напрямую не копируется — переменные передаются через `docker-compose.yml`. |
| `src/main.py`           | Точка входа FastAPI. Содержит эндпоинты `/`, `/whoami`, `/visits`, `/health`. При старте создаёт таблицы в БД с retry-циклом. |
| `src/db.py`             | Создаёт `engine` и `SessionLocal`, отдаёт `Base` для моделей и `get_db()` для FastAPI-зависимостей. |
| `src/models.py`         | Модель `Visit` — таблица `visits` со столбцами `id`, `instance_id`, `path`, `created_at`. |
| `src/config.py`         | Читает `DATABASE_URL`, `REDIS_URL`, `INSTANCE_ID` из переменных окружения, с разумными дефолтами. |

## Эндпоинты

| Метод | Путь      | Описание |
|-------|-----------|----------|
| GET   | `/`       | Главная HTML-страница с идентификацией ноды |
| GET   | `/whoami` | JSON: какая нода ответила (instance_id, hostname, boot_uuid, pid) |
| GET   | `/visits` | JSON: счётчик визитов из Redis + идентификация ноды |
| GET   | `/health` | JSON: проверка доступности PostgreSQL и Redis |
| GET   | `/docs`   | Автогенерируемая документация FastAPI (Swagger UI) |

## Запуск

### Требования

- Docker Desktop
- Docker Compose (входит в Docker Desktop)
- Свободные порты 8081 и 8082 на хосте

### Команды

```bash
docker compose up --build
```

Поднимутся четыре контейнера:

pr2-db-1 — PostgreSQL, слушает только внутри docker-сети

pr2-redis-1 — Redis, слушает только внутри docker-сети

pr2-app1-1 — первая нода приложения, порт хоста 8081

pr2-app2-1 — вторая нода приложения, порт хоста 8082

Проверка

# кто ответил на первой ноде
curl http://localhost:8081/whoami

# кто ответил на второй ноде
curl http://localhost:8082/whoami

# счётчик в Redis общий для всех нод
curl http://localhost:8081/visits
curl http://localhost:8082/visits

# проверка, что БД и Redis доступны
curl http://localhost:8081/health
curl http://localhost:8082/health

В браузере:

http://localhost:8081/

http://localhost:8082/

Остановка
```bash
docker compose down
```

Полный сброс (с удалением данных PostgreSQL)
```bash
docker compose down -v
```

Флаг ```-v``` удаляет volume pgdata. Используется, если нужно пересоздать базу
с нуля (например, после смены имени БД в конфиге).


## Переменные окружения

### Задаются в ```docker-compose.yml``` для каждого инстанса:

INSTANCE_ID — пример значения app1 — идентификатор ноды для эндпоинта
/whoami.

DATABASE_URL — пример значения postgresql://app:app@db:5432/appdb —
строка подключения к PostgreSQL.

REDIS_URL — пример значения redis://redis:6379/0 — строка подключения
к Redis.


### Параметры самого PostgreSQL (создаются один раз при инициализации volume):

POSTGRES_USER = app

POSTGRES_PASSWORD = app

POSTGRES_DB = appdb

## Как масштабировать на 3+ ноды
Добавь в ```docker-compose.yml``` ещё один блок по образцу app2:
```bash
  app3:
    build: .
    environment:
      INSTANCE_ID: app3
      DATABASE_URL: postgresql://app:app@db:5432/appdb
      REDIS_URL: redis://redis:6379/0
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    ports:
      - "8083:8080"
```

## Особенности реализации

Таблицы создаются при старте приложения через Base.metadata.create_all
с retry-циклом. Это нужно, потому что вторая нода может стартовать
одновременно с первой и попытаться создать ту же таблицу.

pool_pre_ping=True в SQLAlchemy — если соединение с PostgreSQL оборвётся,
оно будет переподнято при следующем запросе.

Приложение не хранит никакого состояния в памяти и на диске: всё, что нужно
пережить падение ноды, лежит в PostgreSQL или Redis.
