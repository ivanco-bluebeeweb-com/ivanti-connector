# Ivanti Connector — UI component plan

Источники: `Docs/session-notes/UI_COMPONENT_VOCABULARY.md`, `UI_INTERFACE_STANDARD.md`,
`concepts/panels.md`. Основано на функционале `ivanti-connector`.

## 0. Разница с IDEAL_ONBOARDING.md
Идеал предполагает мгновенную проверку через реальный OData-запрос прямо в форме
подключения. Реализация делает это тем же способом, что и другие dual-auth коннекторы
портфеля (ServiceNow) — `connect_ivanti` сам выполняет пробный запрос перед сохранением,
и форма показывает результат через стандартный error/success путь `ui.Form`.

## 1. Компоненты

| Экран | Примитивы | Почему именно эти |
|---|---|---|
| Sidebar (left) | `ui.Stack`(v) + `ui.Text`(tenant label) + `ui.Divider` + `ui.Button`×6 (Incidents/Requests/Problems/Changes/CIs/Knowledge) + `ui.Button`("App settings") | Без карточек, без дублирования инструкций. |
| Connect form (not connected) | `ui.Form` + `ui.Select`(auth_mode: oauth2/basic) + labelled `ui.Input`×N (host, client_id/secret ИЛИ username/password) | Один переключатель режима определяет видимые поля, как у ServiceNow. |
| Help panel | `ext.panel`(center_overlay=True) + `ui.Text`(объяснение разницы cloud/on-prem host + OData query syntax) | Единственное место с инструкциями подключения. |
| Incidents list (center, `center_overlay=True`) | `ui.Header` + `ui.Input`(OData $filter) + `ui.DataTable`(id/summary/status/priority) | Табличный список инцидентов с фильтром. |
| Service Requests / Problems / Changes panels | Аналогичная структура `ui.DataTable` + create `ui.Form` | Единый паттерн по всем ITSM-объектам. |
| CMDB (CIs) panel | `ui.DataTable`(CI name/class/status) | Просмотр конфигурационных единиц. |
| Knowledge panel | `ui.DataTable`(title/status) | Просмотр статей базы знаний. |
| Generic BO passthrough | `ui.Form`(BO name + $filter query) → `ui.DataTable` | Доступ к любому Business Object, не покрытому типизированными обёртками. |
| App settings | `ext.panel`(slot=center) + список подключённых тенантов + `ui.Button`("Disconnect") | Управление подключениями отдельно от sidebar. |

## 2. Формы: обязательные лейблы, контекстные плейсхолдеры
Каждый `ui.Input`/`ui.Select` обёрнут в `_field(label, node)` с текстовым лейблом.
Плейсхолдеры конкретны под Ivanti: `https://acme.ivanticloud.com`, `Incident#`,
`Status eq 'Open'` — не generic "введите значение".

## 3. Контейнер формы
Sidebar-форма подключения растянута на всю ширину левого сайдбара
(`ui.Stack(direction="v", gap=3, align="stretch")` на каждом уровне), содержимое
растянуто внутри неё самой — без узких/нецентрированных полей.

## 4. Разделение инструкций
Sidebar не дублирует инструкции по подключению — только сама форма + одна кнопка
"Where do I find my credentials?" ведущая в модалку с полным объяснением. Модалка
хранит все объяснения (OAuth2 vs Basic, cloud vs on-prem host format, OData syntax).
