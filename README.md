# Ассистент разработчика с применением RAG

AI-ассистент для разработки ПО представляет собой автономный агент с поддержкой вызова инструментов для поиска по коду, чтения и редактирования файлов, выполнения команд в терминале и других задач. Поиск по исходному коду проектов реализована через RAG (Retrieval-Augmented Generation). Для более качественного разбиения файлов исходного кода на фрагменты применяется алгоритм AST Splitter. Взаимодействие с ассистентом производится через UI на базе HTML-страницы.

В состав также входит оператор для **Apache Airflow**, предназначенный для периодической индексации репозиториев GitLab в векторную базу Qdrant.

## Возможности

- **Поиск по кодовой базе** - семантический поиск с помощью RAG
- **Работа с файлами** - чтение, создание и редактирование файлов проекта
- **Терминал** - выполнение команд в терминале
- **Кэлькулятор** - арифметические вычисления
- **Подтверждение действий** - пользователь контролирует вызов инструментов путем явного подтверждения
- **Многофайловые вложения** - указание файлов через `@путь` для встраивания в контекст модели
- **Мультисессийность** - независимые сессии с сохранением истории, краткосрочной и долгосрочной памятью
- **Асинхронная индексация проекта** - индексация текущего проекта в векторную базу
- **Индексация GitLab-репозиториев** - периодическая индексация репозиториев GitLab

## Архитектура

<img src="assets/arch.png" width="50%"/>

### Стек технологий

| Компонент       | Технология            |
|-----------------|-----------------------|
| Бэкенд          | Python, FastAPI       |
| Агент           | LlamaIndex            |
| Векторная БД    | Qdrant                |
| Брокер задач    | Redis + Celery        |
| Инференс-движок | vLLM, либо llama.cpp  |
| Проксирование   | LiteLLM               |
| Фронтенд        | Vue, TypeScript       |
| Парсер          | tree-sitter           |
| Наблюдаемость   | OpenTelemetry, Prometheus, Grafana, Loki, Tempo  |

## Структура проекта

```
.
├── dev-assistant/              # Сервис ассистента (FastAPI + LlamaIndex)
│   ├── dev_assistant/          
│   │   ├── agent.py            # Реализация агента
│   │   ├── server.py           # API-сервер
│   │   ├── rag.py              # RAG (клиент Qdrant, индексация)
│   │   ├── chunking.py         # Реализация алгоритма AST Splitter
│   │   ├── config.py           # Управление конфигурацией
│   │   ├── celery_app.py       # Приложение Celery
│   │   ├── celery_tasks.py     # Задача по индексации рабочего проекта
│   │   ├── tools/              # Доступные для агента инструменты
├── dev-assistant-ui/           # Фронтенд (Vue, TypeScript)
│   ├── src/                    # Компоненты: App, Messages, Prompt, Settings...
├── airflow/                    # Оператор Apache Airflow для индексации репозиториев GitLab
│   ├── Dockerfile              # Образ airflow
│   ├── dags/                   # DAG-файлы (gitlab_indexer.py)
├── vllm-cuda/                  # Исправление Docker-образа vLLM для CUDA
├── etc/                        # Файлы конфигурации (vLLM, LiteLLM, OTel и т.д.)
├── docker-compose.yaml         # Запуск инфраструктуры с использованием vLLM
├── docker-compose.llama.yaml   # Альтернатива с использованием llama.cpp
├── docker-compose.airflow.yaml # Запуск Airflow для индексации репозиториев GitLab
└── ir-benchmark/               # Бенчмарк алгоритмов сегментации кода
```

## Быстрый старт

### Требования

- Docker и Docker Compose
- NVIDIA GPU с драйверами
- `uv` - менеджер пакетов Python
- Node.js 20+ (для сборки UI)

### Запуск всех сервисов

**Вариант 1: vLLM (рекомендуется)**

```bash
# Настройте модели в .env
docker compose up -d
```

**Вариант 2: llama.cpp**

```bash
# Поместите GGUF-модели в ./llama-models/ и настройте пути в .env
docker compose -f docker-compose.llama.yaml up -d
```

**Запуск Airflow**

```bash
# Настройте переменные в .env (GITLAB_TOKEN, GITLAB_URL, QDRANT_URL и др.)
docker compose -f docker-compose.airflow.yaml up -d
```

Airflow веб-интерфейс доступен на `http://localhost:8080` (логин/пароль: `airflow`/`airflow`).

### Запуск бэкенда локально

```bash
cd dev-assistant

# Установка зависимостей
uv sync

# Настройка переменных окружения (см. dev-assistant/.env)
export API_BASE_URL=http://your-host:4000/v1
export QDRANT_URL=http://your-host

# Запуск сервера
uv run -m dev_assistant

# Воркер Celery (для переиндексации)
uv run celery -A dev_assistant.celery_app worker --concurrency=3 -P solo
```

Сервер доступен на `http://localhost:8000` с OpenAI-совместимым API.

### Сборка UI

```bash
cd dev-assistant-ui
npm install
npm run build
```

Результат сборки будет доступен в `dist/chat.html`.

## Переменные окружения

Полные списки переменных - в `.env.example` (корень) и `dev-assistant/.env.example`.

### dev-assistant

| Переменная              | Описание                               | По умолчанию               |
|-------------------------|----------------------------------------|----------------------------|
| `API_BASE_URL`          | LiteLLM endpoint (OpenAI-compatible)   | - (обязательна)            |
| `QDRANT_URL`            | Адрес Qdrant                           | - (обязательна)            |
| `REDIS_URL`             | Redis broker для Celery                | `redis://localhost:6379/0` |
| `PROXY_URL`             | HTTP-прокси                            | -                          |
| `OTEL_SERVICE_NAME`     | Название сервиса для observability     | `dev-assistant`            |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OpenTelemetry Collector endpoint | `http://localhost:4317`    |
| `RAG_TOP_K`             | Количество возвращаемых фрагментов     | `10`                       |
| `RAG_CHUNK_SIZE`        | Размер чанка при парсинге кода         | `256`                      |

### Root `.env` (vLLM, Airflow, индексация)

| Переменная              | Описание                               | По умолчанию               |
|-------------------------|----------------------------------------|----------------------------|
| `VLLM_LLM_MODEL`        | Основная LLM-модель                    | `Qwen/Qwen2.5-3B-Instruct` |
| `VLLM_LLM_DRAFT_MODEL`  | Черновая модель для Speculative Decoding | -                        |
| `VLLM_EMB_MODEL`        | Модель эмбеддингов                     | `BAAI/bge-base-en`         |
| `VLLM_RANK_MODEL`       | Модель ранжирования                    | `BAAI/bge-reranker-v2-m3`  |
| `VLLM_GPU_DEVICE`       | Номер GPU для vLLM                     | `0`                        |
| `GITLAB_URL`            | Адрес GitLab для индексации            | -                          |
| `GITLAB_TOKEN`          | Токен доступа к GitLab                 | -                          |
| `GITLAB_FILE_FILTER`    | Фильтр файлов (через `;`)              | `*.*`                      |
| `AIRFLOW_PROJ_DIR`      | Каталог с Airflow-проектом             | `./airflow`                |

## Поддерживаемые языки

AST-парсинг для RAG-индексации поддерживает: C#, TypeScript, JavaScript, Python, Go, Java.

## Наблюдаемость

Система включает полный стек observability:
- **Prometheus** - метрики на порту 9090
- **Grafana** - дашборды на порту 3000 (анонимный доступ)
- **Loki** - агрегация логов
- **Tempo** - трейсы на порту 3200
- **OTel Collector** - сбор метрик и трасс на портах 4317/4318

## IR-бенчмарк

Директория `ir-benchmark/` содержит бенчмарк для оценки качества извлечения документов по описаниям типов, методов, либо функций. Сравниваются стандартные алгоритмы сегментации из библиотеки LlamaIndex с представленным в работе алгоритмом AST Splitter, а также оценивается гибридный поиск и ранжирование ответов. См. подробнее [здесь](ir-benchmark/README.md).

## Оценка производительности генерации

Директория `llm-benchmark/` содержит бенчмарк для оценки скорости генерации в зависимости от различного количества черновых токенов в подходе Speculative Decoding. См. подробнее [здесь](llm-benchmark/README.md).

## Лицензия

MIT
