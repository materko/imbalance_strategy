"""`DrawCommand` → MultiCharts `DrwRectangle` / `DrwTrendLine` / `DrwText`.

Sink nepozná PowerLanguage — dostane „plátno" (`canvas`), ktoré tie tri objekty
vie vyrobiť. V študii je ním samotný `SignalObject`, v testoch fake. Vďaka tomu
sa dá mapovanie testovať bez MultiCharts.

Sink drží `obj_id -> natívny objekt`, takže `DrawUpdate` a `DrawDelete` z jadra
sa premietnu na ten istý objekt — rovnako ako Pine `box.set_*` / `box.delete`.

**Čo MultiCharts nevie:** priehľadnosť. Pine kreslí zóny s výplňou na 85 %
priehľadnosti; `DrwRectangle` má len plnú farbu. Alfa sa preto zahodí a použije
sa základná farba — obrázok bude sýtejší než v TradingView. Je to vedomé
zjednodušenie, nie chyba; číselná parita (`test_golden_tv_draw.py`) tým netrpí.
"""

from __future__ import annotations

from ...core.drawing import (
    DrawBg,
    DrawBox,
    DrawCommand,
    DrawDelete,
    DrawLabel,
    DrawLine,
    DrawUpdate,
)

__all__ = ["MCDrawSink", "hex_to_rgb"]


def hex_to_rgb(color: str) -> tuple[int, int, int]:
    """`#rrggbb` alebo `#rrggbbaa` → (r, g, b). Alfa sa zahadzuje — viď docstring."""
    c = color.lstrip("#")
    if len(c) not in (6, 8):
        raise ValueError(f"necakana farba: {color!r}")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


class MCDrawSink:
    """Premení príkazy jadra na natívne objekty a drží ich podľa `obj_id`."""

    __slots__ = ("canvas", "objects", "skip_backgrounds")

    def __init__(self, canvas, *, skip_backgrounds: bool = True) -> None:
        self.canvas = canvas
        self.objects: dict[str, object] = {}
        #: Pine `bgcolor()` sa v MultiCharts nedá spraviť obdĺžnikom cez celú výšku
        #: (nepozná „paper" súradnice), takže sa pozadie seansy štandardne preskakuje.
        self.skip_backgrounds = skip_backgrounds

    # ------------------------------------------------------------------ #

    def render(self, commands: list[DrawCommand]) -> None:
        for cmd in commands:
            self.apply(cmd)

    def apply(self, cmd: DrawCommand) -> None:
        if isinstance(cmd, DrawUpdate):
            self._update(cmd)
        elif isinstance(cmd, DrawDelete):
            self._delete(cmd.obj_id)
        elif isinstance(cmd, DrawBg):
            if not self.skip_backgrounds:
                self._create_box_like(cmd)
        elif isinstance(cmd, DrawBox):
            self._create_box(cmd)
        elif isinstance(cmd, DrawLine):
            self._create_line(cmd)
        elif isinstance(cmd, DrawLabel):
            self._create_text(cmd)

    # -- vytváranie ------------------------------------------------------ #

    def _create_box(self, box: DrawBox) -> None:
        obj = self.canvas.create_rectangle(
            x1_ms=box.x1_ms, y1=box.y1, x2_ms=box.x2_ms, y2=box.y2,
            border=hex_to_rgb(box.border_color),
            fill=hex_to_rgb(box.fill_color) if box.fill_color else None,
            style=box.border_style.value,
            width=box.border_width,
            extend_right=box.extend_right,
        )
        self._store(box.obj_id, obj)

    def _create_box_like(self, bg: DrawBg) -> None:
        obj = self.canvas.create_rectangle(
            x1_ms=bg.x1_ms, y1=None, x2_ms=bg.x2_ms, y2=None,
            border=hex_to_rgb(bg.color), fill=hex_to_rgb(bg.color),
            style="solid", width=0, extend_right=False,
        )
        self._store(bg.obj_id, obj)

    def _create_line(self, line: DrawLine) -> None:
        obj = self.canvas.create_trendline(
            x1_ms=line.x1_ms, y1=line.y1, x2_ms=line.x2_ms, y2=line.y2,
            color=hex_to_rgb(line.color), style=line.style.value, width=line.width,
        )
        self._store(line.obj_id, obj)

    def _create_text(self, label: DrawLabel) -> None:
        obj = self.canvas.create_text(
            x_ms=label.x_ms, y=label.y, text=label.text,
            color=hex_to_rgb(label.color), above=label.above,
        )
        self._store(label.obj_id, obj)

    def _store(self, obj_id: str, obj) -> None:
        if not obj_id:
            raise ValueError("objekt bez obj_id sa neda updatovat ani mazat")
        old = self.objects.get(obj_id)
        if old is not None:
            self.canvas.delete(old)
        self.objects[obj_id] = obj

    # -- zmeny a mazanie -------------------------------------------------- #

    #: Ktoré polia jadra vie MultiCharts na hotovom objekte zmeniť.
    _SETTERS = {
        "x2_ms": "set_end_x",
        "y2": "set_end_y",
        "x1_ms": "set_begin_x",
        "y1": "set_begin_y",
        "fill_color": "set_fill",
        "border_color": "set_border",
        "color": "set_color",
    }

    def _update(self, upd: DrawUpdate) -> None:
        obj = self.objects.get(upd.obj_id)
        if obj is None:
            return  # objekt už neexistuje - rovnako ako Pine set_* na zmazanom boxe
        setter = self._SETTERS.get(upd.field)
        if setter is None:
            return
        value = upd.value
        if upd.field.endswith("color") or upd.field == "color":
            value = hex_to_rgb(str(value))
        getattr(self.canvas, setter)(obj, value)

    def _delete(self, obj_id: str) -> None:
        obj = self.objects.pop(obj_id, None)
        if obj is not None:
            self.canvas.delete(obj)

    def clear(self) -> None:
        """Zmaže všetko — volá sa v `Destroy()` študie."""
        for obj in self.objects.values():
            self.canvas.delete(obj)
        self.objects.clear()
