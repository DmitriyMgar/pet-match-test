# Architecture — PetMatch Backend

## Обзор

```
                         ┌─────────────────────────────────────────────┐
  HTTP request ─────────▶│                 FastAPI                     │
                         │                                             │
                         │  routes/          evaluator       database  │
                         │  ┌──────────┐     ┌──────────┐   ┌───────┐ │
                         │  │ evaluate │────▶│ evaluate │──▶│SQLite │ │
                         │  │ rules    │     │ _and_save│   │       │ │
                         │  │ stats    │     └────┬─────┘   └───────┘ │
                         │  └──────────┘          │                   │
                         │       │           ┌────▼──────────┐        │
                         │       └──────────▶│ RulesEngine   │        │
                         │                   │  ┌───────────┐│        │
                         │   rules.yaml ────▶│  │ Expression││        │
                         │                   │  │ Parser    ││        │
                         │                   │  └───────────┘│        │
                         │                   └───────────────┘        │
                         └─────────────────────────────────────────────┘
```

Backend — один процесс FastAPI (uvicorn), без внешних зависимостей кроме файловой системы. Все данные — в SQLite-файле и YAML-конфиге.

## Модули

```
app/
├── main.py               # FastAPI app, lifespan, CORS, router registration
├── config.py             # RULES_PATH, DATABASE_PATH, CORS_ORIGINS (env vars)
├── models.py             # все Pydantic-модели (domain + rules)
├── expression_parser.py  # парсер SQL-подобных условий → AST → eval
├── rules_engine.py       # загрузка YAML, скоринг, альтернативы
├── evaluator.py          # оркестратор: engine.evaluate() + database.save()
├── database.py           # SQLite через aiosqlite
├── dependencies.py       # Annotated Depends для engine и database
└── routes/
    ├── evaluate.py       # POST /api/evaluate
    ├── rules.py          # GET/POST rules, reload, validate, pet-types
    └── stats.py          # GET /api/stats, GET /api/evaluations
```

### main.py — точка входа

FastAPI-приложение с `lifespan` context manager. При старте:
1. Создаёт `RulesEngine(RULES_PATH)` — загружает и валидирует `rules.yaml`. Если файл невалиден — приложение не запускается (fail fast).
2. Создаёт `Database(DATABASE_PATH)`, вызывает `connect()` — создаёт файл БД и таблицы.
3. Оба объекта сохраняются в `app.state`.

При shutdown — закрывает соединение с БД.

### dependencies.py — внедрение зависимостей

`Engine` и `DatabaseDep` — `Annotated`-типы с `Depends()`, которые извлекают экземпляры из `request.app.state`. Роуты получают зависимости через аннотации аргументов:

```python
Engine = Annotated[RulesEngine, Depends(_get_engine)]
DatabaseDep = Annotated[Database, Depends(_get_database)]
```

### config.py — конфигурация

Три переменные окружения с дефолтами:

| Переменная | Дефолт | Описание |
|------------|--------|----------|
| `RULES_PATH` | `rules.yaml` | Путь к файлу правил |
| `DATABASE_PATH` | `data/petmatch.db` | Путь к SQLite-файлу |
| `CORS_ORIGINS` | `*` | Разрешённые CORS-домены через запятую |

## Модели (models.py)

Все Pydantic-модели в одном файле. Две группы:

### Domain-модели (API request/response)

```
EvaluationRequest
├── pet_type: str
└── profile: UserProfile
        ├── apartment_size_m2: int    [1..500]
        ├── has_children: bool
        ├── monthly_budget_rub: int   [0..1_000_000]
        └── work_hours_per_day: int   [0..24]

EvaluationResponse
├── compatible: bool
├── risk_level: RiskLevel (low | medium | high)
├── risk_score: int
├── reasons: list[str]          # сообщения от условий с risk_score > 0
├── positives: list[str]        # сообщения от условий с risk_score == 0
└── alternatives: list[Alternative]
        ├── pet_type: str
        ├── name: str
        └── why: list[str]
```

`UserProfile` — поля с `Field(ge=..., le=...)` — Pydantic отдаёт 422 при нарушении.

### Rules-модели (конфигурация)

```
RulesConfig
├── scoring: ScoringConfig
│       └── thresholds: ScoringThresholds
│               ├── low: int
│               ├── medium: int      # model_validator: low < medium < high
│               └── high: int
├── common_rules: list[Rule]
└── pet_types: dict[str, PetConfig]
        ├── name: str
        └── rules: list[Rule]
                ├── name: str | None
                └── conditions: list[Condition]
                        ├── condition: str        # SQL-подобное выражение
                        ├── risk_score: int [0..10]
                        └── message: str
```

## Expression Parser (expression_parser.py)

Самописный рекурсивный спуск (~200 строк). Без `eval()`, без внешних библиотек.

### Пайплайн

```
"apartment_size_m2 < 30 AND has_children == true"
        │
        ▼ tokenize()
[IDENT:apartment_size_m2, OP:<, INT:30, AND, IDENT:has_children, OP:==, BOOL:true]
        │
        ▼ _Parser.parse()
{op: "AND",
  left:  {op: "<",  left: {field: "apartment_size_m2"}, right: {literal: 30}},
  right: {op: "==", left: {field: "has_children"},      right: {literal: true}}}
        │
        ▼ _eval_node(ast, values)
True / False
```

### Грамматика

```
expr       → or_expr
or_expr    → and_expr ( "OR" and_expr )*
and_expr   → comparison ( "AND" comparison )*
comparison → atom ( OP atom )?
atom       → "(" expr ")" | INT | BOOL | IDENT
```

Операторы: `<`, `>`, `<=`, `>=`, `==`, `!=`, `AND`, `OR`, скобки.

### Catch-all

Строка `"true"` как полное значение `condition` — всегда `True`. Используется как default/else ветка в if-else цепочке. Внутри выражений `true`/`false` — булевы литералы для сравнений (`has_children == true`).

### Валидация при загрузке

`validate_expression(expr, allowed_fields)` — парсит выражение, собирает имена полей из AST, проверяет что все они входят в `UserProfile.model_fields`. Ошибка при загрузке, а не при первом запросе.

## Rules Engine (rules_engine.py)

### Загрузка и валидация

```
rules.yaml → yaml.safe_load() → Pydantic RulesConfig.model_validate()
           → validate_expression() для каждого condition
           → sha256(raw)[:16] как rules_version
```

Fail fast: невалидный YAML или выражение → `RulesEngineError` → приложение не запускается.

### Оценка (evaluate)

```
          UserProfile
              │
              ▼
    ┌─────────────────────┐
    │  common_rules       │──▶ (common_score, common_reasons, common_positives)
    │  (if-else per rule) │
    └─────────────────────┘
              +
    ┌─────────────────────┐
    │  pet_types[type]    │──▶ (pet_score, pet_reasons, pet_positives)
    │  .rules             │
    └─────────────────────┘
              │
              ▼
    total_score = common_score + pet_score
    reasons     = common_reasons + pet_reasons
    positives   = common_positives + pet_positives
              │
              ▼
    risk_level: total < low → LOW, < medium → MEDIUM, else → HIGH
    compatible: total < thresholds.high
```

Каждое правило — if-else цепочка: conditions проверяются по порядку, первое сработавшее побеждает (`break`). `risk_score > 0` → message идёт в reasons. `risk_score == 0` → message идёт в positives.

### Подбор альтернатив

Для каждого другого типа питомца прогоняются common_rules + его pet_rules с тем же профилем. Фильтр: только compatible (`total < thresholds.high`). Сортировка по score. Top-3.

`why` формируется из positives альтернативы. Если positives пустой — fallback: `"Общий уровень риска ниже: {alt_score} vs {original_score}"`.

### Safe reload

`reload()`: загрузка → парсинг → валидация → атомарная замена `self._config`. При ошибке на любом этапе — старые правила остаются, выбрасывается exception.

`save_yaml(content)`: валидация YAML-строки → запись на диск → замена config. Тоже атомарно: запись на диск происходит только после успешной валидации.

`rules_version` — первые 16 символов SHA-256 от содержимого YAML-файла. Привязывается к каждой оценке в БД.

## Database (database.py)

SQLite через aiosqlite. Одна таблица:

```sql
evaluations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pet_type        TEXT NOT NULL,
    profile_json    TEXT NOT NULL,       -- JSON: {apartment_size_m2, has_children, ...}
    compatible      BOOLEAN NOT NULL,
    risk_level      TEXT NOT NULL,       -- "low" | "medium" | "high"
    risk_score      INTEGER NOT NULL,
    reasons_json    TEXT NOT NULL,       -- JSON: ["reason1", "reason2", ...]
    positives_json  TEXT NOT NULL,       -- JSON: ["positive1", ...]
    alternatives_json TEXT NOT NULL,     -- JSON: [{pet_type, name, why}, ...]
    rules_version   TEXT NOT NULL,       -- SHA-256[:16] правил на момент оценки
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

Индексы: `created_at` (сортировка в списке), `pet_type` (группировка в статистике).

JSON-поля хранятся как TEXT — десериализация в `_row_to_dict()` при чтении.

### Операции

- `save_evaluation()` — INSERT + commit
- `get_evaluations(limit, offset)` — SELECT ORDER BY created_at DESC с пагинацией
- `get_stats()` — COUNT + GROUP BY агрегаты (total, compatible, today, by_pet_type)

## Evaluator (evaluator.py)

Оркестратор — единственный модуль, знающий и про engine, и про database:

```
EvaluationRequest → engine.evaluate() → EvaluationResponse
                                             │
                                    database.save_evaluation()
```

Тонкая прослойка без собственной логики.

## Routes

Тонкие обработчики — принимают запрос, вызывают сервис, возвращают ответ. Вся логика — в engine/evaluator/database.

### evaluate.py

`POST /api/evaluate` — принимает `EvaluationRequest`, вызывает `evaluate_and_save()`. Неизвестный pet_type → `RulesEngineError` → HTTP 404.

### rules.py

| Endpoint | Описание |
|----------|----------|
| `GET /api/pet-types` | Список типов из engine |
| `GET /api/rules` | Structured rules + rules_version |
| `GET /api/rules/raw` | Сырой YAML (PlainTextResponse) |
| `POST /api/rules` | Принимает `{yaml_content}`, валидирует, пишет на диск, reload |
| `POST /api/rules/reload` | Перечитывает rules.yaml с диска |
| `POST /api/rules/validate` | Dry-run — валидация без применения |

Ошибки валидации (RulesEngineError, YAMLError, ValidationError) → HTTP 422.

### stats.py

| Endpoint | Описание |
|----------|----------|
| `GET /api/stats` | Агрегаты из БД |
| `GET /api/evaluations` | Список оценок (query: `limit` 1–100, `offset` >= 0) |

## Обработка ошибок

| Код | Когда |
|-----|-------|
| 400 | Невалидный JSON |
| 404 | Неизвестный `pet_type` |
| 422 | Pydantic validation (автоматически), невалидный YAML при reload/save |
| 500 | Необработанное исключение |

## Потоки данных

### Оценка анкеты

```
Client → POST /api/evaluate
       → Pydantic валидация (EvaluationRequest)
       → evaluator.evaluate_and_save()
           → engine.evaluate(pet_type, profile)
               → _evaluate_rules(common_rules, values)
               → _evaluate_rules(pet_rules, values)
               → _determine_risk_level()
               → _find_alternatives()
           → database.save_evaluation()
       ← EvaluationResponse (JSON)
```

### Reload правил

```
Client → POST /api/rules/reload
       → engine.reload()
           → path.read_text()
           → yaml.safe_load()
           → RulesConfig.model_validate()
           → validate_expression() for each condition
           → self._config = new_config  (атомарная замена)
       ← {"status": "ok", "rules_version": "..."}
```

При ошибке на любом шаге — `self._config` не меняется, возвращается 422.

## Тестирование

54 теста. Три уровня:

| Уровень | Файл | Что тестирует |
|---------|------|---------------|
| Unit | `test_expression_parser.py` (18) | Токенизация, парсинг, вычисление, catch-all, ошибки |
| Integration | `test_rules_engine.py` (17) | Скоринг, compatible/incompatible, альтернативы, reload, версионирование |
| E2E | `test_api.py` (19) | HTTP endpoints через `httpx.AsyncClient` |

Тесты используют `tmp_path` для изолированных rules.yaml и SQLite. Фикстуры в `conftest.py`: `rules_path`, `async_client`.
