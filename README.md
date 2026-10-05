# presale-agent-promroboty

Портал валидации пресейла «Промышленные роботы»: **карточка проекта** — всё, что нужно
проверить до сборки технико-коммерческого предложения, на одной ссылке.

**v0.3** — карточка из семи вкладок: Обзор · Вводные · Процесс · Решение · Декомпозиция ·
Компоненты · ТКП. Tabler UI, CSPL-архитектура: страницы собираются детерминированными
генераторами из YAML-спек, правки проверяющих ложатся слоем поверх нашей версии.
На «Обзоре» delivery-менеджер принимает пакет — до этого ТКП не собирается.

## Устройство (CSPL)

- `data/deals/<slug>/` — спеки сделки: `deal.yaml` плюс `questions.yaml`, `process.yaml`,
  `solution.yaml`, `wbs.yaml`, `bom.yaml`, `proposal.yaml` (каждая необязательна — есть спека,
  есть вкладка), файлы в `img/` и `proposal/`. Конечный заказчик не указывается — только кодовое имя.
- `generators/` — детерминированные генераторы (`overview_page.py`, `questions_page.py`,
  `process_page.py`, `solution_page.py`, `wbs_page.py`, `bom_page.py`, `proposal_page.py`,
  `build.py`, общий каркас `common.py` с реестром вкладок `PAGES`).
  Правка страницы = правка спеки + пересборка.
  `from_lead.py` — конвертер сметы сделки в спеки (`wbs.yaml`, `bom.yaml`): чистит тексты,
  сверяет итоги; правила замен лежат в папке сделки, не здесь (репозиторий публичный).
  `check_confidential.py` — чек: заказчик не назван, внутренних денег нет (в т.ч. на живом портале).
- В `deal.yaml` необязательны `context` (суть проекта), `questions` и `notes` (по страницам `wbs`/`bom`);
  в `wbs.yaml` этап с `option: true` — опция вне итога; в позиции BOM — `group`, `range`, `weeks`, `conf_label`.
  Спеки `questions`/`process`/`solution`/`proposal` переносятся из папки сделки через `from_lead.py`
  (ключи `pass_specs` и `files` в файле правил); вводные с `internal: true` на портал не уходят.
- `build/` — собранные страницы (генерируются при старте сервера, в git не хранятся).
- `runtime/` — слои правок валидаторов (JSON, append-only). На Railway без
  подключённого volume стираются при redeploy — итоги забираем сразу после проверки.
- `main.py` — FastAPI: страницы, API сохранения правок, `/health`.

## Маршруты

- `/` — список проектов на проверке
- `/d/<slug>/` — карточка проекта (вкладка «Обзор»)
- `/d/<slug>/<page>` — вкладка: `package`, `questions`, `process`, `solution`, `wbs`, `bom`, `proposal`
- `/d/<slug>/img/<file>`, `/d/<slug>/proposal/<file>` — кадры компоновки и файл собранного ТКП
- `GET/POST /api/d/<slug>/review/<page>` — слой правок
- `GET /api/d/<slug>/status` — состояние разделов карточки (сколько правок, кто завершил проверку)

## Локальный запуск

```bash
pip install -r requirements.txt
python main.py
# http://localhost:8000
```

## Деплой

Railway, из этого репозитория: сборка по `requirements.txt`, запуск `python main.py`
(`railway.json`, `Procfile`), порт из `PORT`, проверка живости `GET /health`.

Все данные демо-сделки вымышленные.
