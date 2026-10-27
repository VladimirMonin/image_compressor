---
id: ic-gui-feedback-source-deletion
title: "Явное удаление исходников: общий API и существующие потребители"
kind: plan
status: proposed
created: "2026-10-24"
updated: "2026-10-28"
areas: [command-first, data-safety, windows, compatibility]
summary: "Конечный контракт opt-in удаления через удерживаемый Windows handle после проверенной create-only публикации; отдельный исход удаления без нового сервера или recovery-системы."
owner: "Автор реализации Image Compressor"
code_verified_at: "2026-10-24"
verification_scope: "Read-only исследование общих владельцев и потребителей; один Windows/stdlib metadata probe. Конвертация, удаление, GUI и product tests NOT RUN. Параллельная appearance-дельта не квалифицировалась."
---

# 1. Решение и предел поручения

Назначенная source base: `bf9f89d8b2c877512a58f5a7ad1aea35ccf3559a`, ветка `refactor/command-first`. Исследованы scoped working files; Git provenance в этом проходе не перечитывался, параллельная appearance-дельта не замораживалась.

**Предлагаемое решение:** восстановить существующий `ConversionRequest.delete_original=True` как **безвозвратное удаление отдельного исходника после проверенного нового результата**, только через общий service/filesystem owner. По умолчанию False. Windows local fixed NTFS — единственная первоначально поддерживаемая destructive-граница. `True` не означает замену файла на месте, обход коллизий или разрешение удалять любой объект по старому имени.

Новая пользовательская задача разрешает восстановление функции и снимает прежний task-local запрет. Исторические [план](command-first-refactoring.md), [API v1](../architecture/application-api.md), [GUI REPORT](../figcraft_gui_experiment/REPORT.md) сохраняют факты своих поставок; они не доказывают постоянный пользовательский запрет и не переписываются здесь. Статус этого документа — proposed, не утверждение об уже работающем режиме/ACCEPT.

Выбрана честная **irreversible** семантика: без Корзины, app-backup/архива, скрытого копирования исходников, автоматического восстановления или повтора удаления. Shell/Recycle Bin не даёт требуемой гарантии восстановления: настройки накопителя и превышение вместимости могут привести к окончательному удалению. Настройки Корзины не меняем. Пользователь должен знать также, что output может быть lossy/resized и не сохраняет исходные метаданные. Если исходник нужен для повторной обработки/архива, флаг оставляют выключенным.

**Одно наблюдаемое завершение:** обычный собственный synthetic PNG на Windows NTFS → настоящий API/CLI/существующий GUI → читаемый проверенный новый WebP/JPEG → исходное имя действительно удалено; отказ/отмена сохраняют честный поэлементный результат и не затрагивают чужие байты. Checkbox, который продолжает всегда отказывать, не выполнение.

Сохраняется профиль A: синхронный сервис, имеющиеся DTO, token/progress и сериализация. Нет MCP, daemon, отдельного CLI-EXE, queues/jobs, БД, recovery journal, общего архитектурного рефакторинга. Новый человеческий журнал и итоговая пересборка EXE — другие уже назначенные пункты очереди, не предмет этого плана. Оформление контролов принадлежит параллельному Coder; его mutable theme/assets/style-tests здесь не читались как кандидат и не принимаются.

# 2. Найденные владельцы и обязательные изменения

**CURRENT-STATIC**, не новое выполнение:

| Owner | Существующее поведение / нужная дельта |
|---|---|
| [models.py](../../image_compressor/models.py):203–276,288–345 | Strict bool и default False уже есть; `validate_request:240–241` отвергает True. При снятии отказа **обязательно передать True в EffectiveOptions**, сейчас возвращаемый объект полагается на default False. `source_disposition` пока только retained; ItemResult/Counts frozen. |
| [service.py](../../image_compressor/service.py):137–232,235–437 | Один pipeline, источник закрывается после encode **до** публикации. `os.link` учитывается сразу, затем final verify/digest/identity; finally чистит staging. Для True нужен более долгий защищённый lifetime источника и защищённый final readback до удаления. False-путь/его отмена сохраняются. |
| [filesystem.py](../../image_compressor/filesystem.py) | `Fingerprint`, ancestor checks, no-follow guards, `open_source`, staging ownership, atomic `publish_new`. Stat/hash недостаточны для последующего path-unlink; нынешний `Staging.cleanup` не применять к source. |
| [imaging.py](../../image_compressor/imaging.py):168–260 | Encode уже принимает BinaryIO; единственный полный image verifier пока принимает Path. Разрешить verifier-у также явно переданный BinaryIO, не делать второй verifier. Source precision/alpha/metadata policy не менять. |
| [discovery.py](../../image_compressor/discovery.py):73–224 | Frozen manifest до записей, physical first-wins dedup, запрет reparse/links, output-child exclusion сохраняются. Не удалять каталоги/дубликаты отдельным проходом. |
| [cli.py](../../image_compressor/cli.py):45–66,147–188; [serialization.py](../../image_compressor/serialization.py) | Добавить один opt-in flag → то же поле запроса. Code-first serializer уже обходит fields разрешённых frozen DTO: новой схемы/serializer-ветки/DTO не нужно. |
| `gui/worker.py`:70–117; `gui/main_window.py`:172–257 (legacy PyQt6 GUI удалён из рабочей копии 2026-10-28, история в Git) | Worker уже передавал True, окно объясняло отказ. Для legacy-маршрута нужны были предупреждение до старта и реальный итог, не собственный deleter; после retirement актуален только canonical `gui_pyside6_v2/`. |
| `classes.py`:42–110 (facade удалён в legacy-retirement 2026-10-28, история в Git) | Facade никогда не имел delete-параметра и сохранял default False. С удалением facade наследование flag через его CLI forwarding больше не поставляется; актуален только прямой API/CLI. |
| [controller.py](../../gui_pyside6_v2/controller.py):28–35,125–134; [window.py](../../gui_pyside6_v2/window.py):241–247,289–325,363–398 | Options/immutable request должны переносить выбранный bool вместо hardcoded False. Нельзя оставлять безусловное «Исходники сохранены» при удалении. |
| [queue_model.py](../../gui_pyside6_v2/queue_model.py):48–57,103–117; [localization.py](../../gui_pyside6_v2/localization.py) | Item warnings и source_disposition уже доступны UI; добавить только точное состояние/пояснение удаления, не новую модель очереди. |

Для пересекающихся `gui_pyside6_v2/widgets.py` и существующих UI-tests implementation начинается **после release appearance-среза тем же Coder**, поверх его сохранённых изменений. Исторические deletion hooks этого файла известны из завершённого исследования: checkbox default False/disabled, `options()`, `set_busy()`. Не откатывать стиль ради старых line numbers.

# 3. Публичный контракт — минимальная дельта

## Запрос, поддержка, совместимость

- Сигнатуры `convert(request, *, cancellation=None, on_progress=None)`, `discover_inputs`, `get_capabilities` и имя `delete_original` сохраняются. Strict bool, default False; int/string не становятся согласием.
- Прямой API/CLI принимает True/flag как явное намерение вызывающего. Никаких `input()`, Qt, диалогов, новых authority tokens или prompt в core. Это не выдача прав ОС; действуют права процесса.
- На не-Windows/при отсутствии необходимой native API границы: `rejected`, существующий `DESTRUCTIVE_MODE_UNSUPPORTED`, до discovery/эффектов. Изменить его fixed message на актуальное ограничение, не «удаление вообще никогда не поддерживается». False не загружает WinDLL и не становится Windows-only.
- Поддержку конкретных source/output FS, namespace, permissions, locks проверять поэлементно **до staging**. Обычные ошибки одного элемента не отменяют независимые элементы. Отказ True не подменять молчаливым False.
- JSON `schema_version=1` остаётся: additive `counts.deleted` сериализуется всегда (при False — 0); новые значения существующего source_disposition появляются лишь в новом явном режиме. Старые default-False исходы/поля не меняют смысла. Consumers должны терпеть новые поля, неизвестное disposition никогда не трактовать как deleted. Новый постоянный JSON Schema не вводится.

## Результат и ошибки

Расширить **существующий** `ItemResult.source_disposition` до `Literal["retained", "deleted", "unknown"]`, default retained. Нового публичного DeletionResult/Job/Event не нужно. Добавить в конец существующего `Counts` одно поле `deleted: int = 0` — число **подтверждённо удалённых исходников**, не число публикаций/запросов.

| Ситуация | Контракт |
|---|---|
| False | retained; deletion warnings отсутствуют; deleted=0. «Не запрошено» определяется `options.delete_original=False`, не новым состоянием. |
| True, отказ до native disposition | retained: приложение не удаляло источник. При чужой подмене это не обещает сохранность версии стороннего процесса. Причина в item.error до успешной conversion, в item.warnings после неё. |
| True, удаление сознательно пропущено/отложено из-за cleanup или отмены | retained + warning `SOURCE_DELETION_SKIPPED` либо `CANCELLED` на stage `source_deletion`. **Отложено означает не выполнено, а не поставлено в очередь**; автоматического следующего удаления нет. |
| Native удаление и post-close readback подтверждены | deleted; увеличить Counts.deleted. Сам output не удаляется. |
| Native disposition принят, но завершение нельзя доказать | unknown + `SOURCE_DELETION_UNCONFIRMED`; deleted не увеличивать. Нельзя назвать это ни «сохранён», ни «удалён». ОС могла отложить освобождение до закрытия иных handles; приложение не ждёт бесконечно и не повторяет удаление. |

Добавить `Stage="source_deletion"` и только три необходимых ErrorCode: `SOURCE_DELETION_FAILED`, `SOURCE_DELETION_SKIPPED`, `SOURCE_DELETION_UNCONFIRMED`. Для source identity/content mismatch переиспользовать `SOURCE_CHANGED`; для неподдерживаемой FS/многоссылочного источника — `DESTRUCTIVE_MODE_UNSUPPORTED`; для reparse/namespace — `UNSAFE_PATH`. Fixed safe messages, без OS exception/path/native handle values.

**Смысл ItemResult.status и Counts.succeeded остаётся конверсионным:** если проверенный artifact готов, ошибка удаления не превращает его в failed/unverified. Она отражается warning + retained/unknown, а batch становится **partial** (так же, как сейчас cleanup warning). `total=succeeded+failed+cancelled`; `published` пересекается с ними; `deleted <= succeeded <= total`. При изменившемся/непроверенном output artifact остаётся unverified, deletion не начинается, как и сейчас.

Batch cancelled при реально наблюдённой отмене дальнейшего преобразования **или удаления**. Поэтому возможен `status=cancelled`, `counts.succeeded=1`, `counts.cancelled=0`, published=1, deleted=0: конверсия уже завершилась, остановлено только удаление; item warning объясняет это. `ProgressEvent.processed` и прежние counts не переопределять. `_counts` считает deleted по окончательным dispositions; прогресс item_finished отправляется после разрешения source outcome и закрытия своих handles, не до него.

Все warnings остаются в DTO и JSON. В существующие безопасные item_finished/conversion_finished diagnostic projections добавить disposition/deleted и соответствующий safe reason при deletion warning; никаких новых event bus/постоянных журналов, имён файлов, input digest или ctypes repr в диагностике. Ошибка наблюдателя/formatter не повторяет delete/convert.

# 4. Windows-протокол: объект под защитой, не `hash → unlink(path)`

## 4.1 Конкретные примитивы и граница

Один небольшой внутренний модуль **`image_compressor/_windows_deletion.py`**: ctypes + stdlib, private native handles/guards. Его вызывают filesystem/service; adapters его не импортируют. Никакого install pywin32/send2trash и cross-platform backend framework.

Использовать документированные `CreateFileW`, `GetFileInformationByHandleEx`, `GetFileType`, `GetVolumeInformationByHandleW`, `GetDriveTypeW`, `DuplicateHandle`, `SetFileInformationByHandle`, `FlushFileBuffers`, `CloseHandle`. У ctypes явные pointer-sized HANDLE/argtypes/restype/use_last_error; INVALID_HANDLE_VALUE не путать с NULL. Никакого truncate/create/open-always или `FILE_FLAG_DELETE_ON_CLOSE` при приобретении источника.

Первоначальная область: Windows 10/11 APIs, квалификация именно текущего Windows11/local fixed NTFS; source и target могут быть на разных **локальных fixed NTFS volumes**, staging всегда на volume target. Admit обычные absolute drive-letter paths; reject UNC/network, device namespaces, alternate data streams и reparse ancestors/leaf. Внутренний long-path prefix допустим после lexical validation; не использовать `resolve()` для скрытия symlink/junction. FAT/exFAT/ReFS/removable/cloud-reparse и ненадёжные/нулевые identities — отказ True, не unsafe fallback. Default False имеет прежние platform/FS пределы.

Авторитетный source snapshot создаётся общим manifest в начале `convert`, не из давней GUI-preview: согласие фиксирует выбранные пути/параметры, но не обещает заморозить байты с момента добавления в очередь. Подмена после этого manifest обязана быть обнаружена или заблокирована.

Native identity: `FileIdInfo` (class18: VolumeSerialNumber + 128-bit FileId), `FileStandardInfo` (class1: EOF/NumberOfLinks/DeletePending/Directory), `FileAttributeTagInfo` (class9), `FileBasicInfo` (class0: timestamps/attributes). Сверять с manifest path/descriptor fingerprints в правильных clock domains; CPython Windows path ctime и fstat ctime нельзя снова приравнять. Native initial/final basic snapshots сравнивать между собой, исключая LastAccessTime. Недоступная проверка — отказ, не удалённый guard.

## 4.2 Порядок на один элемент True

1. **Общий preflight без изменений:** полный manifest, dedup, source/destination/групповые коллизии, отсутствие назначения. Same-format продолжает создавать имя с postfix, **никогда** не конвертирует поверх source даже при True.
2. **Закрепить namespace.** Открыть существующие ancestor directories обоих путей от корня к листу, дедуплицировать общие: `FILE_READ_ATTRIBUTES`, share `FILE_SHARE_READ | FILE_SHARE_WRITE` **без FILE_SHARE_DELETE**, `OPEN_EXISTING`, `FILE_FLAG_BACKUP_SEMANTICS | FILE_FLAG_OPEN_REPARSE_POINT`. Сразу проверить directory/not-reparse/identity против снимков. Удерживать их до terminal disposition; повторить chain checks после acquire. Это препятствует обычному rename/delete ancestors. Не закреплять собственный staging dir так, чтобы запретить его последующую очистку.
3. **Закрепить source до чтения.** `CreateFileW(source, GENERIC_READ | DELETE, share=0, …, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, …)`. Это намеренно строгий режим: файл, уже открытый другим data-reader/writer, может отказать; не ослаблять share ради удобства. Проверить disk file, regular/not-reparse/not-directory/not-delete-pending, native identity/fingerprint, **NumberOfLinks==1**, отсутствие READONLY. Source guard не освобождается до удаления/отказа. Acquire failure закрывает уже приобретённые handles, не создаёт staging.
4. **Читать тот же объект.** Raw native handle принадлежит guard. Для Pillow/хеша дать owned duplicate через `DuplicateHandle` → `msvcrt.open_osfhandle` → binary file object; ownership CRT переносится ровно один раз. Эти stream handles — дубликаты уже захваченного объекта, не новые `Path.open()` (CRT sharing с DELETE несовместим). Закрытие Pillow/stream не должно закрыть единственный guard. Зафиксировать initial SHA-256 source из этого stream, reset seek; encode вызывается на том же locked объекте. Source hashes наружу/в log не выводить.
5. **Обычное prepare/publish.** Реальные encode, staging full verify, size/SHA, source/chain/staging checks, существующий pre-link token checkpoint; тот же atomic `os.link`. Сразу сохранить unverified artifact. Нет os.replace, source unlink, overwrite либо fallback при неподдерживаемом link.
6. **Освободить staging до final lock.** В True-пути выполнить свою учтённую `Staging.cleanup()` после link, прежде чем открыть deny-delete final guard: staging и final — hardlinks одного файла, поэтому final deny-delete handle иначе заблокирует удаление payload. Сохранить ожидаемую file identity/digest до cleanup. Cleanup failure даёт прежний warning; всё равно проверить опубликованный artifact, **но источник не удалять**, добавить SOURCE_DELETION_SKIPPED. Не повторять cleanup по чужим/подменённым данным. False-путь и его прежний порядок не менять ради этого.
7. **Закрепить и проверить новый artifact.** `CreateFileW(destination, GENERIC_READ | GENERIC_WRITE, FILE_SHARE_READ, …, OPEN_EXISTING, FILE_FLAG_OPEN_REPARSE_POINT, …)`: WRITE нужен только для `FlushFileBuffers`, не для изменения байтов. Guard запрещает обычную внешнюю запись/rename/delete, в том числе через hardlink. Проверить actual native identity против запомненного staging identity, отличие от source, regular/no-reparse. Полное `imaging.verify_image()` + size/SHA из duplicate stream **этого guard**, с reset seek, сравнение с prepared. Не ограничиваться path-based чтением до захвата. Только после этого artifact verified. Неуспех acquisition/identity/readback → PUBLISHED_UNVERIFIED, исходник сохранён, final не откатывается.
8. **Перед опасным действием:** успешный `FlushFileBuffers` на удерживаемом final handle; повторные source native fingerprint/link-count/readonly/chain checks и SHA из source guard должны совпасть с initial. Flush failure или source mismatch → verified output остаётся, source retained, warning; никаких дальнейших попыток удаления этого элемента. Flush не равен транзакционной crash durability каталога/накопителя. Закрыть **все собственные source stream duplicates**; raw source guard пока жив. Проверить token ещё раз непосредственно перед native disposition. Наблюдённая отмена оставляет оба файла и отражается как cancelled deletion stage.
9. **Единственная destructive-точка:** `SetFileInformationByHandle(source_handle, FileDispositionInfo /*4*/, FILE_DISPOSITION_INFO{DeleteFile=TRUE}, sizeof(...))`, где DeleteFile — native BOOLEAN, не произвольный Python pointer/строка. Это удаление открытого объекта; **никакого `DeleteFileW(path)` / `Path.unlink()` после проверок**. При явном FALSE: retained + SOURCE_DELETION_FAILED. При TRUE сразу фиксировать outcome как ещё **unknown**, не оставлять default retained на случай последующего исключения; затем закрыть raw source handle, пока artifact и directories ещё удерживаются. Cancellation после этой точки уже не откатывает удаление. Не применять FileDispositionInfoEx/POSIX/ignore-readonly как необъявленный fallback.
10. **Подтверждение после close без второго удаления.** При удерживаемом parent проверить исходное имя native metadata-open (READ_ATTRIBUTES, share all, OPEN_REPARSE_POINT), не `exists()` с подавлением ошибок. ERROR_FILE_NOT_FOUND подтверждает отсутствие; если имя занял **иной file identity**, исходный объект удалён с выбранного имени, новый чужой объект не трогать. Same identity либо неопределённый access/query result → unknown + SOURCE_DELETION_UNCONFIRMED; нельзя считать AccessDenied доказательством отсутствия. ERROR_PATH_NOT_FOUND при закреплённом parent — неопределённость, не успех. Никакого polling/retry/удаления нового имени. После результата закрыть final guard, затем directory guards в обратном порядке.

На любом частичном acquire/исключении — закрытие только своих ресурсов с момента приобретения. Guard имеет явный owned/closed state; не закрывать native handle ещё раз после передачи CRT и не терять known artifact/disposition в общем exception mapper. Неожиданная ошибка нового native lifetime/close → INTERNAL_ERROR с известными эффектами, прекращение запуска следующих элементов. Сначала сохранить текущий ItemResult/known artifact/disposition; при уже verified output оставить conversion succeeded и warning, а INTERNAL_ERROR также положить в BatchResult.errors, чтобы существующий CLI вернул 5. Недоделанные элементы получают прежний orchestration-failure результат, не фиктивный success. Не терять текущий item при пробросе исключения и не менять ради этого прежнюю обработку False. Для обычных поэлементных delete failures с корректно закрытыми handles независимый пакет продолжается.

## 4.3 Что именно гарантируется и чего нет

Handle identity + deny-share защищают от **обычной конкурентной записи, удаления и замены пути**, а закреплённые родители — от обычного ancestor rename. Если подмена случилась до захвата, manifest/native mismatch отвергается; после захвата обычная OS-операция должна получить sharing violation. SHA — дополнительная проверка содержимого, **не замена удерживаемым handles**.

Это trusted local namespace, не sandbox против администратора/kernel/raw-volume вмешательства. Важно явно не обещать, что Windows sharing предотвращает запись через **ранее созданное writable memory mapping с уже закрытым исходным handle**: share modes такой изоляции не дают. Активное внепротокольное изменение через mappings/драйверы/remote storage вне destructive-контракта; известный mapping/необычный source использовать только с False. Initial/final hashes обнаруживают наблюдаемое изменение, но не доказывают невозможность всех таких вмешательств. Не приписывать этому плану adversarial compare-and-delete гарантию.

Классическая Windows disposition может быть отложена ОС из-за остаточных compatible/metadata/mapped handles. Это причина проверять имя после закрытия и возвращать unknown, а не утверждать освобождение места по одному успешному BOOL. Строгий share=0 устраняет обычных data-readers из штатного положительного пути. Освобождение всех физических blocks не обещается даже при deleted; обещается удаление выбранного исходного имени/объекта, не secure erase.

Crash/power loss: до disposition могут остаться оба файла; после принятия disposition ОС может завершить удаление при закрытии handles процесса, даже если отчёт не доставлен. `FlushFileBuffers` улучшает границу записи output, но нет atomic двухфайловой транзакции, fsync/recovery journal или гарантии аппаратной сохранности. Возврат `deleted` не обещает возможность Undo/Корзины. Повторный convert — новое действие: существующий output даёт OUTPUT_EXISTS и **не становится основанием удалить source**. После неопределённого исхода пользователь сначала проверяет файлы; отдельная команда «дочистить источник» здесь не добавляется.

# 5. Конечные решения для отказов и отмены

| Условие | Решение True |
|---|---|
| Directory input | Только manifest обычных файлов; сама папка не удаляется. Links/reparse не обходятся. |
| Physical duplicate/hardlink | Dedup остаётся first-wins. При native source nlink!=1 — отказ удаления/элемента до staging с DESTRUCTIVE_MODE_UNSUPPORTED; не угадывать, какой alias удалить, все aliases сохранить. |
| Source=destination / target equals другой input / существующий foreign / group collision | Прежние INPUT_OUTPUT_CONFLICT/OUTPUT_EXISTS/TARGET_CONFLICT; ноль удалений, независимые элементы продолжаются. |
| Поздний foreign target | Реальный os.link отказывает; foreign/source bytes сохраняются. |
| Source stale до guard / между discovery и start | SOURCE_CHANGED, без staging/output/delete. Нет «перепривязки» к новому объекту. |
| Source busy/readonly/нет DELETE или directory-lock rights | SOURCE_DELETION_FAILED до staging; без privilege escalation/снятия readonly/ACL. False может продолжать работать как прежде. |
| Native source final checks mismatch после verified output | retained + SOURCE_CHANGED на deletion stage; partial, output остаётся verified. |
| Encode/staging verify/link failure | Старый отказ; source retained, disposition не вызывается. |
| Final artifact неподтверждён/заменён | PUBLISHED_UNVERIFIED, partial/published по прежнему контракту; источник не удаляется. |
| Final flush failure / native disposition FALSE | Полезный verified output остаётся, retained + SOURCE_DELETION_FAILED, batch partial. |
| Staging cleanup failure | Прежний TEMP_CLEANUP_FAILED + SOURCE_DELETION_SKIPPED; полезный output отдельно проверяется; source retained. |
| Cancel до publish | Прежний контракт: нет нового final/deletion, своя staging очистка. |
| Cancel после publish, до disposition | Завершить verification, не удалять source; item conversion succeeded при verified output, warning CANCELLED/deletion, batch cancelled. |
| Cancel после последнего deletion checkpoint / после disposition | Текущий source может быть удалён; закончить close/readback, следующие items не стартуют после наблюдения token. После последнего полностью завершённого item поздний token не превращает success в отмену. |
| Disposition TRUE, completion неизвестен | unknown + SOURCE_DELETION_UNCONFIRMED; partial, без retry и утверждения retained/deleted. |

# 6. CLI и оба GUI — только адаптеры

## CLI

Добавить ровно **`--delete-original`** к существующему `convert`, `action="store_true"`, default False; передать в ConversionRequest. Help прямо говорит: permanently delete after verified new output; **not Recycle Bin / no automatic recovery; guarded Windows local NTFS only**. Не добавлять overwrite/force/implicit yes или ещё один executable. `capabilities` остаётся query кодеков, не становится проверкой возможности удалить произвольный будущий путь.

Иллюстративная целевая команда, **NOT RUN Oracle**: `python -m image_compressor convert <owned-synthetic.png> --format WEBP --output <new-result.webp> --delete-original`. Existing console script и `classes.py` forwarding получают тот же parser.

Exit mapping сохраняется: 0 только полный batch success; 2 global rejected/usage; 3 partial, включая verified output + deletion failure/unknown; 4 ни полезной publication/success; 130 применённая cooperative cancellation; 5 unexpected INTERNAL_ERROR/delivery. Машинный caller читает **artifact.publication, source_disposition, warnings, options.delete_original, counts.deleted**, а не только counts.succeeded. stdout один JSON, safe stderr отдельно. Потерянный stdout не отменяет известные/возможные эффекты.

## Новый PySide GUI

- После освобождения appearance-файла тем же автором: checkbox обычный, unchecked при запуске, доступен в idle; никакого сохранённого auto-enable preference. `Options` получает bool в конце с False; request передаёт точное значение. Busy gating и настоящий QThread.finished сохраняются.
- **Каждый Start с True** требует локализованного подтверждения с default **«Нет»/Cancel**, количеством выбранных входов и параметрами, однозначно привязанными к видимой очереди и её snapshot (без вывода тысяч имён в modal). Сообщение: исходники будут безвозвратно удалены после проверенного нового результата; Корзины/автовосстановления нет; преобразование может уменьшать качество/размер и удаляет metadata; ошибки могут оставить часть оригиналов. Отмена подтверждения не запускает worker и не создаёт файлов.
- До modal зафиксировать tuple paths/options/generation; после Yes проверить неизменность этой тройки и idle. Если во время вложенного event loop изменился состав/запрос — не запускать старое согласие. Не вводить отдельную persisted confirmation-систему; прямой Controller/API-вызов с True — явный программный запрос, не скрытая GUI-авторизация.
- Заменить только ложные безусловные подписи: subtitle «Исходники сохраняются по умолчанию»; safety label/warning; footer/detail/tooltip с фактическим disposition/deleted. Не перепроектировать журнал в этом срезе.
- Verified output + delete failure: **«Новый файл готов. Оригинал не удалён: …»**, amber partial, путь результата доступен локально. Unknown: **«Новый файл готов; завершение удаления не подтверждено. Проверьте исходник и результат; автоматического повтора нет»**. Не зелёное «всё успешно/все исходники сохранены».
- Для mixed batch показывать отдельно converted/published и deleted; исход каждого файла доступен в имеющихся details/tooltips. Queue row с deletion warning не окрашивать как безусловный полный success; image conversion и source outcome не смешивать. RU/EN/KK, Light/Dark и layout сохраняются.

## Старый PyQt/compatibility

Старый checkbox уже False по умолчанию. Уточнить его label/tooltip о безвозвратности; `start_compression` даёт такое же per-start подтверждение до создания worker. `CompressionWorker` продолжает один API-вызов, передаёт True без подмены; убирается старое обязательное «Снимите флажок» для поддерживаемого случая. `DESTRUCTIVE_MODE_UNSUPPORTED` остаётся корректным сообщением для реальной неподдерживаемой среды.

`result_ready` — полный канон. В legacy `finished_processing(successful, errors)` successful остаётся conversions; errors включает failed/global errors и по одному item с deletion failure/unknown (без двойного счёта error+warning). Cancelled/skipped-by-cancel не считать успешным удалением или fake conversion error. Финальное окно различает partial/deleted/retained/unknown. Signals ровно один раз, stop не wait/terminate, next worker только после finished. Facade `ImageCompressor` без нового параметра сохраняет прежнее API/default-False поведение; Python callers для opt-in уже имеют ConversionRequest.

# 7. Передача SAME Coder: два связных слоя

До работы повторить только discovery конкретных символов/потребителей и проверить актуальный owner файлов. Использовать доступные codebase-memory/Serena/ast-grep по пользе; в этом Oracle наборе они отсутствуют, использованы read/grep. Не устанавливать optional tooling. Читателям/исполнителям передавать точную границу: **только данный проект/перечисленные source owners и свои synthetic fixtures; без personal files, secrets, peer raw sessions и глобальных изменений**.

### A. Общий Windows FS/API/CLI — законченный проверяемый кандидат

Изменяемые существующие пути: `image_compressor/models.py`, `service.py`, `filesystem.py`, `imaging.py`, `cli.py`, `diagnostics.py`; единственный новый product module `image_compressor/_windows_deletion.py`.

Тесты: новые `tests/test_source_deletion.py`, `tests/test_windows_deletion.py`; при необходимости **один** небольшой `tests/deletion_race_harness.py` для реальных own-process races. Точечные изменения `tests/test_api.py`, `test_cli.py`, `test_cancellation.py`, `test_filesystem.py`, `test_gui_adapter.py`, `test_privacy.py`, `test_packaging.py` только по этим invariants. `test_discovery.py`/`test_compatibility.py` — выбранные regression checks; менять только если реальное изменение общего поля требует assertion.

`discovery.py`, `serialization.py`, `__init__.py`, `__main__.py`, `classes.py` — прочитанные consumers, **по плану no-change**: DTO переиспользованы, generic dataclass JSON уже достаточен, facade default сохранён. Pyproject/dependencies/requirements не требуют новой библиотеки; package копируется целиком существующей wheel fixture. Не добавлять общий backend интерфейс, универсальный disposer или тестовый framework.

### B. Минимальное GUI-подключение, после release appearance

Точные owners: `gui/main_window.py`, `gui/worker.py`, **только deletion label/tooltip в `gui/widgets.py`**; `gui_pyside6_v2/controller.py`, `window.py`, `queue_model.py`, `localization.py`, **только deletion wiring/options/busy в `gui_pyside6_v2/widgets.py`**. Новый focused `tests_pyside6_v2/test_source_deletion.py`. Не менять `gui_pyside6_v2/workers.py`, если transport действительно не требует дельты.

Existing `tests_pyside6_v2/test_window.py`/`test_controller.py` могут содержать прежние disabled/False assertions: SAME Coder после appearance release находит и обновляет **только** изменившийся контракт, сохраняя свои style assertions. Эти mutable файлы **не часть Oracle-кандидата/квалификации**, их байты не фиксируются этим планом. Tests/style helper/assets/theme.py/tokens.json — вне deletion edit scope.

### Знания и защищённое

С реализацией обновить current `docs/architecture/application-api.md`, README/UV_GUIDE/QUICK_GUIDE/UPDATE_FEATURES current warning, соответствующие current AGENTS/foundation architecture/project-philosophy и инструкции testing/logging в узкой затронутой части; `docs/figcraft_gui_experiment/RUNNING.md` — текущую семантику запуска из source. Новый компактный verification допустим в `docs/verification/gui-feedback-source-deletion.md`. Это работа Coder/accepting Reviewer по обычному workflow, **не записи Oracle сейчас**. Ранее принятые verification/REPORT/планы/EXE receipts не переписывать как будто новая функция там уже была.

Защищены: `design/`, PFK snapshot, чужие/прежние `.agent-work` roots, принятый EXE и все прежние dist/build outputs, legacy bat/spec, глобальные настройки, index/coordinator. Windows packaging recipe/driver/tests и EXE guide меняются лишь последующим выделенным integration/frozen срезом; старый SHA не заменять. Сейчас Oracle пишет только этот план, свой handoff и factual append LOG.

# 8. TDD и достаточные native/connected проверки

**Всё ниже — назначенные проверки, не выполненные Oracle.** Сначала добавить public positive test True→verified output+actual source absence+deleted=1 и default-False control. На старом owner ожидается **содержательный RED**: DESTRUCTIVE_MODE_UNSUPPORTED вместо результата. Missing module/import/collection failure не выдавать за этот RED. Затем реализовать настоящий narrow native path и выполнить тот же positive/control до расширения матрицы.

| Проверка / controlled schedule | Обязательное различающее наблюдение |
|---|---|
| Native positive через direct API, WEBP/JPEG; source/output в Unicode/space paths | Настоящие codecs и disposition, final open/load/expected pixels/dimensions/SHA/size, исходник отсутствует **после всех собственных closes**, deleted=1, source_disposition=deleted. Никакого mocked native success. |
| Без flag / False / bool validation | Исходные bytes неизменны; deleted=0, retained; int/string отказ до эффектов. EffectiveOptionsTrue реально сериализуется у positive. |
| Path replacement **до** acquire | В barrier после manifest переименовать synthetic source, на его место положить иной synthetic файл. SOURCE_CHANGED; replacement/moved-original bytes целы, no output/delete. |
| Source write/rename и ancestor rename **после** native acquire | Свой отдельный процесс пытается настоящий write-open/rename; получен sharing refusal, не успешная подмена. Основной convert завершается; никто не удаляет foreign bytes. Проверить и source parent, и distinct target parent. |
| Source изменённый контент / final guard mismatch | Before-acquire изменение ловит fingerprint; controlled late native metadata/hash mismatch не допускает disposition. Защита не сводится к exists/hash перед path-delete. |
| Artifact replacement/изменение между link и final guard | Реальный publish, затем controlled rename/foreign replacement; guarded identity/readback refuses, source сохранён, foreign final не тронут, artifact unverified/published. |
| Artifact writer/rename после final guard | Реальный own child получает refusal до disposition. Verifier и digest читают один удерживаемый объект. Вызов source disposition раньше successful full verify+flush запрещён assertion-ом schedule. |
| Existing/group/same-path/hardlink conflict, empty postfix, directory discovery/dedup | Прежние specific errors/порядок/counts/foreign bytes; hardlinked source nlink>1 даёт поддерживаемый отказ True, оба aliases остаются. Positive directory: удалены лишь успешно обработанные regular files, каталоги остаются. |
| Reparse/junction/ADS/UNC/unsupported volume; readonly/busy source | Реальный local NTFS positive обязателен; опасные namespace/refusal ветки без traversal/delete. Синтетический readonly/открытый reader отказ до staging, False control полезен. Не ходить на настоящую сеть ради negative. |
| Encode/staging verify/link/final verify failure | Ни одного source disposition; существующие rejection/source preservation assertions не ослаблены. Final readback fault после настоящего link сохраняет published-unverified. |
| Flush fail / native disposition FALSE после настоящей conversion | Подменён только соответствующий native edge; full output readback настоящий, item succeeded+verified, retained+warning, batch partial/CLI3. Нельзя замокать весь convert готовым DTO. |
| Cleanup failure/foreign staging | Реальный owned cleanup отказ; foreign bytes целы, verified output при возможности, source retained, TEMP_CLEANUP_FAILED+SKIPPED; ни одного source-delete вызова. |
| Disposition accepted, post-close confirmation недоступно | Настоящий native effect, подменена только metadata confirmation: unknown/UNCONFIRMED, deleted=0, не retained, не повтор. При воспроизводимом native pending через свой compatible metadata handle дополнительно доказать отсутствие ложного deleted; отсутствие такой репродукции не называть native pending PASS. |
| Cancel перед encode/link, после link, перед disposition, после допуска disposition | Точные outputs/source absence/retention/counts согласно §5; cancel не Undo. Неизменённый False late-publication test по-прежнему succeeded. Новый True late-delete test может deleted=1; следующий item stopped. |
| Partial batch + повтор | Первый verified/deleted, второй corrupt retained, третий delete failure retained: общий partial, отдельные accurate dispositions/deleted. Повтор не «дочищает» source при существующем output. |
| Resource lifetime | После success/каждого acquire/fault/cancel reopening синтетических оставшихся объектов и переименование owned parents возможно; own children/threads завершены. Следующая независимая операция работает. Частичный acquisition не теряет handle. |
| API headless, source CLI, установленная консоль | Hook запрещает Qt/gui/argparse/input/print для direct API; actual native positive остаётся рабочим. CLI stdout единственный JSON, stderr safe; installed no-Qt wheel вне source cwd/PYTHONPATH содержит новый module и выполняет deletion positive + False + refusal. |
| Оба GUI | Реальные controller/worker/API, default unchecked, confirmation No→ноль эффектов, Yes→native positive/readback, mutation during confirmation→нет запуска; failure/unknown/partial не обещают удаления/сохранности. Qt bindings строго в разных процессах. RU/EN/KK имеют предупреждение и исход. |
| Privacy/observer | Actual FileHandler/CLI stderr/GUI buffer непустые: disposition/deleted/reason есть, synthetic private path/postfix/raw exception/source digest отсутствуют. Observer/delivery failure не повторяет удаление. |

Старые намеренные refusal assertions меняются **только по новой власти/контракту**: `tests/test_api.py:52` (True rejected), `tests/test_cli.py` case `--delete-original`→CLI_USAGE, `tests/test_gui_adapter.py:56–79,275–294` (refusal и «Снимите флажок»), прежние disabled/hardcoded-False GUI assertions. Вместо blanket refusal — Windows positive + explicit unsupported/refusal controls. `--overwrite`, malformed bool, missing verification, collisions, source stale, metadata/alpha/PNG16 guards сохраняются. Исторические RED/170/47/22 PASS не переименовываются в новые результаты.

Проверки только synthetic в **новом собственном** project-local root, pre-collection TEMP/TMP/TMPDIR/cache isolation, existing interpreters; никаких новых инструментальных установок/extra worktrees. Сначала `tests/test_source_deletion.py`/`test_windows_deletion.py`, затем адресные API/CLI/cancellation/filesystem/privacy/legacy/packaging selectors и отдельный `tests_pyside6_v2/test_source_deletion.py`. Не общий `pytest .` и не полный исторический suite ради новой даты. Каждый batch запуска ограничить ~120 s, каждый own child 30 s/barrier deadline 10 s, guaranteed own cleanup. Не убивать процессы по имени. Native deletion positive на целевом Windows **не skip**; вне Windows проверить refusal, не заявлять поддержку. Lint/typing только изменённые owners, core и PySide проверять в своих прежних средах.

# 9. Done, передача и фактические действия Oracle

Кодер передаёт законченный source+tests+evidence кандидат по A/B, не ещё один research-plan: реальные positive/negative outputs, точные commands/raw exits/NOT RUN, изменённые paths и freeze. Затем SAME независимый Reviewer оценивает **новую** safety boundary, не опирается на прежнее отсутствие удаления. Невозможность выполнить positive/native lock/identity invariants — narrow blocker тому же Oracle; не заменить гарантию архивом, shell deletion, path-unlink, молчаливым False или снятием теста. Дополнительного пользовательского решения для выбранной явно предупреждаемой irreversible семантики здесь не требуется.

После достаточной реализации/проверки этого среза — остановка и release. Human journal может использовать finalized fields; позднейшая EXE qualification должна включить новый default-preserve и opt-in source outcome на **новом** artifact, не считается выполненной этим планом. Git/commit/push Oracle/Coder не разрешены; независимая приёмка/доставка — по [development](../instructions/development.md).

Oracle переиспользовал завершённый GUI-разбор, прочитал текущие owners/guards/tests/потребителей, [pf-plan](../../tools/project-foundation/skills/pf-plan/SKILL.md), [pf-command-first](../../tools/project-foundation/skills/pf-command-first/SKILL.md), lifecycle/metadata/quality/contract-evolution и relevant PFK converter §§16–17. Материалы учебного конвертера не перенесены как Job/DB/recovery framework.

Единственный native probe был **read-only metadata** одного project source file: CPython3.14.2, Windows10.0.26200, fixed NTFS; FileIdInfo совпал с path st_dev/st_ino, single-link/not-reparse/not-pending, нужные exports найдены; raw exit0. Body файла/личные данные не читались этим probe, `SetFileInformationByHandle`/flush/delete не вызывались. Это подтверждает доступность metadata route, **не проверяет destructive/share/close semantics** — их доказывает Coder новым synthetic positive и races. Product imports/conversion/tests/GUI/build/Git Oracle не запускал. Прежние отчёты/артефакты и параллельные appearance bytes неизменны со стороны Oracle.
