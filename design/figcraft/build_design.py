"""Emit official FigCraft 0.10 commands for the editable desktop design.

This is a graphics automation recipe, not a native file serializer or Qt exporter.
Run the JSON through figcraft-cli run, continuing the component-proof native file.
"""

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
COMMANDS = []


def cmd(command, **params):
    step = len(COMMANDS)
    COMMANDS.append(dict(command=command, params=params))
    return {"$step": step}


def frame(name, parent=None, width=100, height=40, **props):
    props.setdefault("fill", "#00000000")
    params = dict(type="frame", name=name, width=width, height=height, props=props)
    if parent is not None:
        params["parent"] = parent
    return cmd("node.create", **params)


def text(value, parent, name="Text", size=14, color="text/primary", **props):
    ref = cmd(
        "node.create",
        type="text",
        name=name,
        parent=parent,
        text=value,
        props=dict(
            fontFamily="Segoe UI",
            fontSize=size,
            sizingH="hug",
            sizingV="hug",
            textAutoResize="widthAndHeight",
            **props,
        ),
    )
    bind(ref, "fill", variables[color])
    return ref


def bind(node, field, variable):
    cmd("variable.bind", ids=[node], field=field, variable=variable)


def color(node, role):
    bind(node, "fill", variables[role])


def prop(master, name, layer, default):
    cmd("component.addProperty", id=master, name=name, type="text", default=default, layer=layer)


def instance(master, parent, label=None, key=None, **props):
    ref = cmd("instance.create", component=master, parent=parent)
    if label is not None:
        cmd("instance.setProperties", ids=[ref], properties={"Label": label})
    if key:
        bind(ref, "componentProperties/Label", strings[key])
    if props:
        cmd("node.set", ids=[ref], props=props)
    return ref


PALETTE = {
    "surface/window": ["#F3F6FB", "#101827"],
    "surface/panel": ["#FFFFFF", "#192537"],
    "surface/raised": ["#EAF0F8", "#243349"],
    "text/primary": ["#17263C", "#EDF3FC"],
    "text/secondary": ["#50627A", "#B5C5DB"],
    "border/default": ["#CCD7E5", "#40516B"],
    "accent/action": ["#245EDB", "#82ACFF"],
    "accent/on-action": ["#FFFFFF", "#10213F"],
    "state/success": ["#176A4C", "#79DDB1"],
    "state/warning": ["#875106", "#F6CA79"],
    "state/error": ["#AF3444", "#FFA2AC"],
    "focus/ring": ["#153F9D", "#B8D0FF"],
}
STRINGS = {
    "subtitle": [
        "Новые файлы. Исходники сохраняются.",
        "New files. Originals stay safe.",
        "Жаңа файлдар. Түпнұсқалар сақталады.",
    ],
    "add": ["Добавить файлы", "Add files", "Файлдарды қосу"],
    "folder": ["Выбрать папку", "Choose folder", "Қалтаны таңдау"],
    "queue": ["Очередь", "Queue", "Кезек"],
    "empty": ["Добавьте изображения", "Add images to begin", "Бастау үшін суреттерді қосыңыз"],
    "drop": [
        "Перетащите файлы или папку сюда",
        "Drop files or a folder here",
        "Файлдарды не қалтаны осында сүйреңіз",
    ],
    "inputs": [
        "JPEG, PNG, WebP, HEIF, AVIF · PNG только вход",
        "JPEG, PNG, WebP, HEIF, AVIF · PNG input only",
        "JPEG, PNG, WebP, HEIF, AVIF · PNG тек кіріс",
    ],
    "settings": ["Параметры", "Settings", "Параметрлер"],
    "format": ["Выходной формат", "Output format", "Шығыс пішімі"],
    "quality": ["Качество", "Quality", "Сапа"],
    "resize": ["Уменьшить размер", "Resize to fit", "Өлшемін кішірейту"],
    "width": ["Максимальная\nширина", "Maximum\nwidth", "Ең үлкен\nені"],
    "height": ["Максимальная\nвысота", "Maximum\nheight", "Ең үлкен\nбиіктігі"],
    "postfix": ["Постфикс", "Postfix", "Постфикс"],
    "postfixHelp": [
        "Для совпадающих форматов. Занятые имена не перезаписываются.",
        "For matching formats. Existing names are never overwritten.",
        "Бірдей пішімдер үшін. Бар файлдар қайта жазылмайды.",
    ],
    "recursive": ["Включая подпапки", "Include subfolders", "Ішкі қалталарды қосу"],
    "delete": [
        "Удалять оригиналы — недоступно",
        "Delete originals — unavailable",
        "Түпнұсқаларды жою — қолжетімсіз",
    ],
    "safe": [
        "Безопасный API всегда сохраняет исходники.",
        "The safe API always retains originals.",
        "Қауіпсіз API түпнұсқаларды әрқашан сақтайды.",
    ],
    "start": ["Начать", "Start", "Бастау"],
    "stop": ["Остановить", "Stop", "Тоқтату"],
    "clear": ["Очистить очередь", "Clear queue", "Кезекті тазарту"],
    "ready": ["Готово к запуску", "Ready to start", "Бастауға дайын"],
    "processing": ["Обработка · 1 / 3", "Processing · 1 / 3", "Өңделуде · 1 / 3"],
    "waiting": ["Ожидает", "Ready", "Дайын"],
    "running": ["Обработка", "Processing", "Өңделуде"],
    "done": ["Готово", "Done", "Дайын"],
    "log": ["Журнал операции", "Operation log", "Әрекет журналы"],
    "name": ["Имя файла", "File name", "Файл атауы"],
    "suffix": ["Расш.", "Suffix", "Кеңейтім"],
    "bytes": ["Размер", "Size", "Өлшем"],
    "status": ["Статус", "Status", "Күй"],
    "count": [
        "Доступно: 3 · Ошибок добавления: 0",
        "Available: 3 · Selection issues: 0",
        "Қолжетімді: 3 · Қосу қатесі: 0",
    ],
}

theme = cmd("variable.createCollection", name="Theme", modes=["Light", "Dark"])
variables = {
    key: cmd(
        "variable.create",
        collection=theme,
        name=key,
        type="color",
        values=dict(zip(["Light", "Dark"], values)),
    )
    for key, values in PALETTE.items()
}
locale = cmd("variable.createCollection", name="Locale", modes=["RU", "EN", "KK"])
strings = {
    key: cmd(
        "variable.create",
        collection=locale,
        name=key,
        type="string",
        values=dict(zip(["RU", "EN", "KK"], values)),
    )
    for key, values in STRINGS.items()
}
metrics = cmd("variable.createCollection", name="Metrics", modes=["Base"])
for key, value in {
    "space/1": 4,
    "space/2": 8,
    "space/3": 12,
    "space/4": 16,
    "space/6": 24,
    "radius/panel": 12,
    "radius/control": 8,
    "type/body": 14,
    "type/caption": 12,
    "type/title": 24,
}.items():
    cmd("variable.create", collection=metrics, name=key, type="number", value=value)

library = frame(
    "Component library",
    width=1120,
    height=1180,
    y=210,
    layout="vertical",
    padding=24,
    gap=12,
    clip=False,
)
color(library, "surface/window")
text("Image Compressor / editable component library", library, size=24)
masters = {}
for name, role, label in [
    ("Primary", "accent/action", "Начать"),
    ("Secondary", "surface/raised", "Добавить файлы"),
    ("Stop", "surface/panel", "Остановить"),
    ("Input", "surface/window", "_compressed"),
    ("Format", "surface/window", "WebP  ▾"),
    ("Badge", "surface/raised", "Готово к запуску"),
]:
    m = frame(
        "Button / " + name if name in ("Primary", "Secondary", "Stop") else name,
        library,
        width=184 if name != "Badge" else 220,
        height=36,
        layout="horizontal",
        padding=[8, 12, 8, 12],
        crossAlign="center",
        mainAlign="center",
        cornerRadius=8,
        sizingH="hug" if name not in ("Input", "Format") else "fixed",
    )
    color(m, role)
    if name in ("Stop", "Input", "Format"):
        bind(m, "stroke", variables["state/error" if name == "Stop" else "border/default"])
        cmd("node.set", ids=[m], props={"strokeWeight": 1})
    t = text(label, m, "Label", color="accent/on-action" if name == "Primary" else "text/primary")
    cmd("component.create", ids=[m])
    prop(m, "Label", t, label)
    masters[name] = m

checkbox = frame(
    "Checkbox / default",
    library,
    width=280,
    height=24,
    layout="horizontal",
    gap=8,
    crossAlign="center",
    sizingH="hug",
)
box = frame("Indicator", checkbox, width=16, height=16, cornerRadius=4)
color(box, "accent/action")
tick = cmd(
    "node.create",
    type="vector",
    name="Check vector",
    parent=box,
    width=16,
    height=16,
    path="M4 8 L7 11 L12 5",
    props={"fill": "#00000000", "stroke": "#FFFFFF", "strokeWeight": 2},
)
t = text("Включая подпапки", checkbox, "Label")
cmd("component.create", ids=[checkbox])
prop(checkbox, "Label", t, "Включая подпапки")
masters["Checkbox"] = checkbox

row = frame(
    "Queue / row",
    library,
    width=620,
    height=48,
    layout="horizontal",
    padding=[8, 12, 8, 12],
    gap=12,
    crossAlign="center",
    cornerRadius=4,
)
color(row, "surface/panel")
for key, value, w in [
    ("Name", "sample_landscape.png", 260),
    ("Suffix", "PNG", 52),
    ("Bytes", "1.8 MiB", 72),
    ("Status", "Ожидает", 104),
]:
    t = text(value, row, key, size=13, color="text/primary" if key == "Name" else "text/secondary")
    cmd(
        "node.set",
        ids=[t],
        props={
            "width": w,
            "height": 20,
            "sizingH": "fill" if key == "Name" else "fixed",
            "sizingV": "fixed",
            "textAutoResize": "truncate",
            "maxLines": 1,
        },
    )
cmd("component.create", ids=[row])
# Find the text references from the just-emitted create steps (no invented native IDs).
for command in list(COMMANDS):
    p = command["params"]
    if command["command"] == "node.create" and p.get("parent") == row and p["type"] == "text":
        ref = {"$step": COMMANDS.index(command)}
        prop(row, p["name"], ref, p["text"])
masters["Row"] = row
panel = frame(
    "Section / panel",
    library,
    width=500,
    height=72,
    layout="vertical",
    gap=6,
    padding=12,
    cornerRadius=12,
)
color(panel, "surface/panel")
t = text("Журнал операции", panel, "Label", size=13)
body = text("event=ready count=3", panel, "Body", size=12, color="text/secondary")
cmd("component.create", ids=[panel])
prop(panel, "Label", t, "Журнал операции")
prop(panel, "Body", body, "event=ready count=3")
masters["Panel"] = panel
# Real disabled and focus specimens, not a promise of runtime behavior.
focus = instance(masters["Primary"], library, label="Focus / keyboard")
bind(focus, "stroke", variables["focus/ring"])
cmd("node.set", ids=[focus], props={"strokeWeight": 3})
disabled = instance(masters["Secondary"], library, label="Disabled / unavailable", opacity=0.5)
icon = frame("Icon-Add", library, width=24, height=24)
cmd(
    "node.create",
    type="vector",
    name="Add vector",
    parent=icon,
    width=24,
    height=24,
    path="M12 4 L12 20 M4 12 L20 12",
    props={"fill": "#00000000", "stroke": "#245EDB", "strokeWeight": 2, "strokeCap": "round"},
)
cmd("node.set", ids=[icon], props={"exports": [{"format": "svg", "scale": 1}]})

screens_page = cmd("page.add", name="01 · Desktop screens")
screens = []
for state in ["Empty", "Queue", "Processing"]:
    root = frame(
        "RU-Light-" + state,
        width=1120,
        height=760,
        x=0,
        y=len(screens) * 860,
        layout="vertical",
        padding=20,
        gap=12,
    )
    color(root, "surface/window")
    cmd("variable.setMode", ids=[root], collection=theme, mode="Light")
    cmd("variable.setMode", ids=[root], collection=locale, mode="RU")
    screens.append(root)
    header = frame(
        "Header",
        root,
        width=1080,
        height=60,
        layout="horizontal",
        gap=16,
        crossAlign="center",
        sizingH="fill",
    )
    title = frame(
        "Identity", header, width=660, height=56, layout="vertical", gap=3, sizingH="fill"
    )
    text("Image Compressor", title, size=24, fontStyle="Semibold")
    sub = text(STRINGS["subtitle"][0], title, size=13, color="text/secondary")
    bind(sub, "characters", strings["subtitle"])
    instance(masters["Secondary"], header, label="Light / Dark", height=34)
    instance(masters["Format"], header, label="Русский  ▾", width=126, height=34)
    body = frame(
        "Body / flexible queue + fixed settings",
        root,
        width=1080,
        height=556,
        layout="horizontal",
        gap=16,
        sizingH="fill",
        sizingV="fill",
    )
    left = frame(
        "Queue area",
        body,
        width=744,
        height=556,
        layout="vertical",
        gap=12,
        sizingH="fill",
        sizingV="fill",
    )
    addbar = frame(
        "Add actions", left, width=744, height=36, layout="horizontal", gap=8, sizingH="fill"
    )
    instance(masters["Secondary"], addbar, key="add")
    instance(masters["Secondary"], addbar, key="folder")
    queue = frame(
        "Queue card",
        left,
        width=744,
        height=366,
        layout="vertical",
        gap=8,
        padding=16,
        sizingH="fill",
        sizingV="fill",
        cornerRadius=12,
    )
    color(queue, "surface/panel")
    if state == "Empty":
        spacer = frame("Breathing room", queue, width=20, height=24, sizingV="fill")
        for key, size in [("empty", 20), ("drop", 14), ("inputs", 12)]:
            t = text(
                STRINGS[key][0],
                queue,
                size=size,
                color="text/primary" if key == "empty" else "text/secondary",
            )
            bind(t, "characters", strings[key])
            cmd(
                "node.set",
                ids=[t],
                props={"sizingH": "fill", "textAlign": "center", "textAutoResize": "height"},
            )
        frame("Breathing room below", queue, width=20, height=24, sizingV="fill")
    else:
        t = text(STRINGS["queue"][0], queue, size=18, fontStyle="Semibold")
        bind(t, "characters", strings["queue"])
        t = text(STRINGS["drop"][0], queue, size=12, color="text/secondary")
        bind(t, "characters", strings["drop"])
        tableheader = instance(masters["Row"], queue, width=680, height=32, sizingH="fill")
        cmd(
            "instance.setProperties",
            ids=[tableheader],
            properties={
                k: STRINGS[v][0]
                for k, v in [
                    ("Name", "name"),
                    ("Suffix", "suffix"),
                    ("Bytes", "bytes"),
                    ("Status", "status"),
                ]
            },
        )
        for k, v in [
            ("Name", "name"),
            ("Suffix", "suffix"),
            ("Bytes", "bytes"),
            ("Status", "status"),
        ]:
            bind(tableheader, "componentProperties/" + k, strings[v])
        for i, (name, suffix, size) in enumerate(
            [
                ("landscape_synthetic.png", "PNG", "1.8 MiB"),
                ("portrait_ӘҒҚҢӨҰҮҺІ.jpg", "JPG", "640 KiB"),
                ("long_synthetic_filename_for_elision.webp", "WEBP", "215 KiB"),
            ]
        ):
            r = instance(masters["Row"], queue, width=680, height=48, sizingH="fill")
            cmd(
                "instance.setProperties",
                ids=[r],
                properties={"Name": name, "Suffix": suffix, "Bytes": size},
            )
            key = (
                "done"
                if state == "Processing" and i == 0
                else "running"
                if state == "Processing" and i == 1
                else "waiting"
            )
            bind(r, "componentProperties/Status", strings[key])
        frame("Table viewport", queue, width=20, height=10, sizingV="fill")
        t = text(STRINGS["count"][0], queue, size=12, color="text/secondary")
        bind(t, "characters", strings["count"])
    log = instance(masters["Panel"], left, key="log", width=700, height=100, sizingH="fill")
    cmd(
        "instance.setProperties",
        ids=[log],
        properties={
            "Body": "event=conversion_started total=3\nevent=item_finished succeeded=1 failed=0"
            if state == "Processing"
            else "event=selection_finished available=3 issues=0"
            if state == "Queue"
            else "event=ready"
        },
    )
    right = frame(
        "Settings panel",
        body,
        width=320,
        height=556,
        layout="vertical",
        gap=8,
        padding=16,
        cornerRadius=12,
        sizingV="fill",
    )
    color(right, "surface/panel")
    t = text(STRINGS["settings"][0], right, size=18, fontStyle="Semibold")
    bind(t, "characters", strings["settings"])
    viewport = frame(
        "Scrollable settings viewport",
        right,
        width=288,
        height=400,
        layout="vertical",
        gap=6,
        sizingH="fill",
        sizingV="fill",
        clip=True,
    )
    form = frame(
        "Settings scroll content",
        viewport,
        width=288,
        height=408,
        layout="vertical",
        gap=6,
        sizingH="fill",
        sizingV="hug",
    )

    def label(key, parent=form, size=13):
        t = text(STRINGS[key][0], parent, size=size, color="text/secondary")
        bind(t, "characters", strings[key])
        return t

    label("format")
    instance(masters["Format"], form, label="WebP  ▾", width=288, sizingH="fill")
    quality = frame(
        "Quality row", form, width=288, height=24, layout="horizontal", gap=8, sizingH="fill"
    )
    label("quality", quality)
    frame("Flexible gap", quality, width=20, height=16, sizingH="fill")
    text("80 / 100", quality, size=13)
    track = frame("Quality slider", form, width=288, height=6, cornerRadius=3, sizingH="fill")
    color(track, "surface/raised")
    fill = frame("Quality value", track, width=218, height=6, cornerRadius=3)
    color(fill, "accent/action")
    instance(masters["Checkbox"], form, key="resize", opacity=0.65 if state != "Processing" else 1)
    dims = frame(
        "Dimension labels", form, width=288, height=36, layout="horizontal", gap=8, sizingH="fill"
    )
    for key in ["width", "height"]:
        t = label(key, dims, size=12)
        cmd(
            "node.set",
            ids=[t],
            props={"width": 140, "height": 34, "sizingH": "fill", "textAutoResize": "height"},
        )
    fields = frame(
        "Dimension fields", form, width=288, height=34, layout="horizontal", gap=8, sizingH="fill"
    )
    for value in ["1920", "1080"]:
        instance(masters["Input"], fields, label=value, width=140, height=34, sizingH="fill")
    label("postfix")
    instance(masters["Input"], form, label="_compressed", width=288, height=34, sizingH="fill")
    t = label("postfixHelp", size=12)
    cmd("node.set", ids=[t], props={"width": 288, "sizingH": "fill", "textAutoResize": "height"})
    instance(masters["Checkbox"], form, key="recursive")
    safety = frame(
        "Originals safety / always visible",
        right,
        width=288,
        height=94,
        layout="vertical",
        gap=6,
        padding=8,
        cornerRadius=8,
        sizingH="fill",
    )
    color(safety, "surface/raised")
    delete = text(STRINGS["delete"][0], safety, size=12, color="text/secondary")
    bind(delete, "characters", strings["delete"])
    cmd("node.set", ids=[delete], props={"sizingH": "fill", "textAutoResize": "height"})
    t = label("safe", safety, size=12)
    cmd("node.set", ids=[t], props={"sizingH": "fill", "textAutoResize": "height"})
    footer = frame(
        "Pinned footer",
        root,
        width=1080,
        height=80,
        layout="vertical",
        gap=8,
        padding=12,
        cornerRadius=12,
        sizingH="fill",
    )
    color(footer, "surface/panel")
    actions = frame(
        "Status and controls",
        footer,
        width=1056,
        height=36,
        layout="horizontal",
        gap=8,
        crossAlign="center",
        sizingH="fill",
    )
    badge = instance(
        masters["Badge"],
        actions,
        key="processing" if state == "Processing" else "ready",
        sizingH="fill",
    )
    instance(
        masters["Secondary"], actions, key="clear", opacity=0.5 if state == "Processing" else 1
    )
    instance(masters["Stop"], actions, key="stop", opacity=1 if state == "Processing" else 0.5)
    instance(masters["Primary"], actions, key="start", opacity=1 if state == "Queue" else 0.5)
    progress = frame("Progress track", footer, width=1056, height=6, sizingH="fill", cornerRadius=3)
    color(progress, "surface/raised")
    if state == "Processing":
        p = frame("1 of 3 completed", progress, width=340, height=6, cornerRadius=3)
        color(p, "accent/action")

# Root copies are a separate engine step after readback provides their real IDs.
cmd("variable.export", path="C:/PY/image_compressor/design/figcraft/variables.raw.json")
cmd("component.list")
(HERE / "commands" / "02-desktop-design.json").write_text(
    json.dumps({"commands": COMMANDS}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
(HERE / "palette.json").write_text(json.dumps(PALETTE, indent=2) + "\n", encoding="utf-8")
(HERE / "language-fit.json").write_text(
    json.dumps(STRINGS, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(f"Wrote {len(COMMANDS)} official design commands (not a native document).")
