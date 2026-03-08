# PetMatch

Сервис оценки совместимости человека с питомцем. Пользователь заполняет анкету (тип питомца, жильё, бюджет, дети, график), сервис оценивает совместимость, объясняет риски и предлагает альтернативы.

## Технологии

| Компонент | Стек |
|-----------|------|
| Backend | Python 3.12, FastAPI, Pydantic v2, aiosqlite |
| Frontend | React 19, Vite 7, Tailwind CSS 4, React Router 7 |
| Database | SQLite |
| Инфраструктура | Docker, Docker Compose, GitHub Actions |
| Линтинг | ruff (Python), ESLint (JS) |
| Тесты | pytest, httpx (async), pytest-asyncio |

## Быстрый старт

### Docker Compose (рекомендуется)

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Health check: http://localhost:8000/api/health

### Локальная разработка

**Backend:**

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend доступен на http://localhost:8000.

**Frontend:**

```bash
cd frontend
npm install
npm run dev
```

Frontend доступен на http://localhost:5173, API проксируется на backend через vite dev server.

## Структура проекта

```
pet-match/
├── docker-compose.yml
├── .github/workflows/ci.yml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml
│   ├── rules.yaml                  # конфигурация правил
│   ├── app/
│   │   ├── main.py                 # FastAPI app, lifespan
│   │   ├── config.py               # env-настройки
│   │   ├── models.py               # Pydantic-модели
│   │   ├── expression_parser.py    # парсер SQL-подобных условий
│   │   ├── rules_engine.py         # движок правил
│   │   ├── evaluator.py            # оркестратор (engine + DB)
│   │   ├── database.py             # SQLite (aiosqlite)
│   │   ├── dependencies.py         # FastAPI Depends
│   │   └── routes/
│   │       ├── evaluate.py         # POST /api/evaluate
│   │       ├── rules.py            # CRUD правил
│   │       └── stats.py            # статистика, история
│   └── tests/
│       ├── conftest.py
│       ├── test_expression_parser.py
│       ├── test_rules_engine.py
│       └── test_api.py
└── frontend/
    ├── Dockerfile
    ├── nginx.conf
    ├── package.json
    └── src/
        ├── App.jsx
        ├── api.js
        ├── pages/
        │   ├── EvaluatePage.jsx    # анкета + результат
        │   └── AdminPage.jsx       # дашборд + правила
        └── components/
            ├── QuestionnaireForm.jsx
            └── EvaluationResult.jsx
```

## API

### POST /api/evaluate

Оценка совместимости с питомцем.

**Запрос:**

```json
{
  "pet_type": "dog",
  "profile": {
    "apartment_size_m2": 40,
    "has_children": true,
    "monthly_budget_rub": 20000,
    "work_hours_per_day": 9
  }
}
```

**Ответ:**

```json
{
  "compatible": true,
  "risk_level": "low",
  "risk_score": 0,
  "reasons": [],
  "positives": [
    "Бюджет достаточный для большинства питомцев",
    "Площадь жилья подходит для собаки",
    "Бюджет достаточный для содержания собаки",
    "Графика работы достаточно для ухода за собакой"
  ],
  "alternatives": [
    {"pet_type": "fish", "name": "Рыбки", "why": ["..."]},
    {"pet_type": "cat", "name": "Кошка", "why": ["..."]}
  ]
}
```

### Все endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/health` | Health check |
| GET | `/api/pet-types` | Список типов питомцев |
| POST | `/api/evaluate` | Оценка совместимости |
| GET | `/api/rules` | Текущие правила (structured) |
| GET | `/api/rules/raw` | Сырой YAML |
| POST | `/api/rules` | Сохранить правила (body: `yaml_content`) |
| POST | `/api/rules/reload` | Перезагрузить с диска |
| POST | `/api/rules/validate` | Валидация без применения (dry-run) |
| GET | `/api/stats` | Статистика |
| GET | `/api/evaluations` | История оценок (query: `limit`, `offset`) |

## Правила

Правила хранятся в `backend/rules.yaml` и полностью отделены от кода. Добавление нового типа питомца — только через конфиг, без изменения кода.

### Формат

Каждое правило — if-else цепочка из conditions. Первое сработавшее условие побеждает:

```yaml
pet_types:
  hamster:
    name: "Хомяк"
    rules:
      - name: "Бюджет"
        conditions:
          - condition: "monthly_budget_rub < 2000"
            risk_score: 3
            message: "Бюджет может быть мал для хомяка"
          - condition: "true"       # catch-all (else)
            risk_score: 0
            message: "Бюджет достаточный для хомяка"
```

### Условия

SQL-подобные выражения: `<`, `>`, `<=`, `>=`, `==`, `!=`, `AND`, `OR`, скобки.

Доступные поля: `apartment_size_m2`, `has_children`, `monthly_budget_rub`, `work_hours_per_day`.

Литерал `"true"` как отдельное условие — catch-all (default/else ветка).

### Скоринг

- `risk_score` каждого условия (0–10) суммируется по всем правилам
- `risk_level` определяется по порогам: low (< 5), medium (< 8), high (>= 8)
- `compatible = total_score < thresholds.high` (при дефолтных порогах: < 10)
- Сообщения с `risk_score > 0` → `reasons` (риски)
- Сообщения с `risk_score == 0` → `positives` (позитивные моменты)

### Горячая перезагрузка

Правила можно обновить без перезапуска сервиса:

```bash
# Reload с диска
curl -X POST http://localhost:8000/api/rules/reload

# Или валидация без применения (dry-run)
curl -X POST http://localhost:8000/api/rules/validate

# Или сохранение нового YAML через API
curl -X POST http://localhost:8000/api/rules \
  -H "Content-Type: application/json" \
  -d '{"yaml_content": "..."}'
```

Safe reload: загрузка → парсинг → валидация → атомарная замена. При ошибке старые правила остаются.

## Тесты

54 теста: парсер выражений, движок правил, API.

```bash
cd backend
source venv/bin/activate
pytest tests/ -v
```

Покрытие:
- **Expression parser** (18): операторы сравнения, AND/OR, скобки, catch-all, булевы литералы, ошибки
- **Rules engine** (17): compatible/incompatible, альтернативы, позитивы, unknown pet type, safe reload, валидация, версионирование
- **API** (19): evaluate, pet-types, rules CRUD, reload, validate, stats, evaluations, pagination, health

## Линтинг

```bash
# Python
ruff check backend/
ruff format --check backend/

# JavaScript
cd frontend && npm run lint
```

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`): lint → test → docker build.
