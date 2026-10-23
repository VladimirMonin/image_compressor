---
id: ic-docs-index
title: "Image Compressor — документация"
kind: navigation
status: accepted
created: "2026-10-23"
updated: "2026-10-23"
areas: [engineering, architecture]
summary: "Вход в проектные правила, принятый прикладной API и историю независимой проверки command-first-среза."
---

# Документация Image Compressor

Начало работы агента — [AGENTS.md](../AGENTS.md). Основа подготовлена по полной локальной редакции [Project Foundation Kit 0.3.0](../tools/project-foundation/README.md); исходный пакет сохранён со своими лицензиями и происхождением. Проектные решения ниже адаптированы, не являются шаблонами пакета.

## Почему и как работаем

- [Философия проекта](foundation/project-philosophy.md): ценность, приоритеты и граница задачи.
- [Архитектурные принципы](foundation/architecture-principles.md): command-first, владельцы, адаптеры и сохранность.
- [Стратегия тестирования](foundation/testing-strategy.md): какие наблюдения подтверждают результат.
- [Политика наблюдаемости](foundation/observability-policy.md): полезные события, приватность и каналы.
- [Разработка и передача](instructions/development.md): роли, ветки, Git и завершение.
- [Тестирование](instructions/testing.md): изоляция, фактические команды и ограничения.
- [Логирование](instructions/logging.md): практические правила добавления диагностики.

## Планирование и фактическая готовность

- [План Oracle](plans/command-first-refactoring.md): исходная/целевая архитектура, четыре связных среза и критерии. План не служит каноном уже реализованного поведения.
- [Прикладной контракт v1 и карта owners](architecture/application-api.md): принятые API/CLI, create-only publication, image policy, совместимость и пределы.
- [Verification и независимый ACCEPT](verification/command-first-refactoring.md): авторская история, R1/R2 и их закрытие, отдельные Reviewer executions и точные NOT RUN. Проверка closeout документации/упаковки отмечается отдельно от независимого решения.

Технический command-first-срез принят после ремонта обоих findings; действующий порядок docs → selective commit → branch-only push у accepting Reviewer — в [development](instructions/development.md). Статусы документов отражают их собственное назначение, не заменяют runtime evidence и не утверждают весь vendored справочник как архитектуру продукта. Локальное состояние/сырые сессии не публикуются; краткая история — в [LOG.md](../LOG.md).

## Исходная граница

База подготовки — `develop`, commit `7707849`. Исторически в ней правила были распределены между `classes.py`, `gui/worker.py` и `gui/utils.py`; автоматизированного набора не было, `test_gui.py` — ручной устаревший запуск. В принятой реализации owner — `image_compressor/`, suite — `tests/`; история не подменяет фактическую проверку. Актуальные пользовательские команды отражены в [README](../README.md), UV_GUIDE и QUICK_GUIDE; старые release/status/build материалы остаются историей, не evidence нового API.

Исторический command-first-срез не включал новый дизайн. Новая отдельная задача явно разрешает [FigCraft → PySide6 эксперимент](figcraft_gui_experiment/02-implementation-plan.md), с [картой реальных функций](figcraft_gui_experiment/01-current-functionality.md), [native-дизайном и mapping](figcraft_gui_experiment/03-design-spec.md), [инструкцией запуска](figcraft_gui_experiment/RUNNING.md) и [отчётом](figcraft_gui_experiment/REPORT.md). Эксперимент получил отдельный технический и визуальный **ACCEPT**: независимые suites 47/170 без skips, native FigCraft tree/reopen/export, Windows Qt/installed readbacks. Команды, источники доказательств и NOT RUN — в его отчёте; это не EXE-релиз и не квалификация всех платформ/DPI или физического OS-dialog/drop. Прежний ACCEPT и source-only область Oracle-документов сохраняются; MCP-сервер продукта не заказан.

Отдельный [standalone Windows EXE follow-up](figcraft_gui_experiment/04-windows-exe-plan.md) завершён: **независимый exact-byte технический и визуальный ACCEPT**. [Инструкция запуска/сборки](figcraft_gui_experiment/WINDOWS_EXE.md) и [EXE artifact/SHA/verification](figcraft_gui_experiment/05-windows-exe-verification.md) различают авторские и новые независимые проверки, reduced-rights standalone-host и непроверенную чистую машину/другой аккаунт. Прежние source/wheel ACCEPT и Oracle discovery не переписаны. Build venv/recipe/output изолированы; binary publication не разрешена.
