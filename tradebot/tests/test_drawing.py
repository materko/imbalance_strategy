"""Kreslenie: identita objektov a prehratie `set_*` zmien.

Pine kreslí objekt raz a potom ho mení (`box.set_right` na každom bare,
`set_bgcolor` pri zmene stavu). Snapshot z okamihu vzniku by teda ukázal niečo
iné než to, čo je na grafe nakoniec vidieť — preto majú objekty `obj_id`
a `DrawRegistry` prehráva `DrawUpdate`.
"""

from __future__ import annotations

import pytest

from tradebot.core import (
    DrawBox,
    DrawDelete,
    DrawKind,
    DrawRegistry,
    DrawUpdate,
    LineStyle,
)


def _box(obj_id: str = "z0.post", **kw) -> DrawBox:
    args = dict(
        kind=DrawKind.SD_ZONE_POST, x1_ms=0, y1=110.0, x2_ms=1000, y2=100.0,
        border_color="#fff", obj_id=obj_id,
    )
    args.update(kw)
    return DrawBox(**args)


def test_box_nesmie_koncit_pred_zaciatkom():
    with pytest.raises(ValueError):
        _box(x1_ms=500, x2_ms=100)


def test_registry_prehra_update():
    r = DrawRegistry()
    r.apply(_box())
    r.apply(DrawUpdate("z0.post", "x2_ms", 5000))
    assert r.objects()[0].x2_ms == 5000


def test_registry_prehra_delete():
    r = DrawRegistry()
    r.apply(_box())
    r.apply(DrawDelete("z0.post"))
    assert len(r) == 0


def test_update_na_zmazany_objekt_je_ticho():
    """Pine `box.set_*` na zmazanom boxe tiež nespadne — len sa nič nestane."""
    r = DrawRegistry()
    r.apply(_box())
    r.apply(DrawDelete("z0.post"))
    r.apply(DrawUpdate("z0.post", "x2_ms", 5000))
    assert len(r) == 0


def test_objekt_bez_id_sa_neda_ulozit():
    r = DrawRegistry()
    with pytest.raises(ValueError):
        r.apply(_box(obj_id=""))


def test_neskorsi_objekt_prepise_rovnake_id():
    r = DrawRegistry()
    r.apply(_box())
    r.apply(_box(y1=999.0))
    assert len(r) == 1 and r.objects()[0].y1 == 999.0


def test_filtrovanie_podla_druhu():
    r = DrawRegistry()
    r.apply(_box("a"))
    r.apply(_box("b", kind=DrawKind.SD_ZONE_PRE, border_style=LineStyle.DOTTED))
    assert [o.obj_id for o in r.objects(DrawKind.SD_ZONE_PRE)] == ["b"]


# --------------------------------------------------------------------------- #
# Zóna: boxy majú stabilné id a menia sa presne ako v Pine
# --------------------------------------------------------------------------- #


def _zone():
    from tradebot.core import Direction
    from tradebot.core.zones import Zone

    return Zone(
        uid=7, direction=Direction.LONG, top=110.0, bot=100.0,
        created_ms=0, confirmed_ms=600_000, expires_ms=3_600_000,
    )


def test_zona_ma_stabilne_id_boxov():
    z = _zone()
    ids = [b.obj_id for b in z.boxes(180_000)]
    assert ids == ["z7.pre", "z7.post"] == [z.pre_box_id, z.post_box_id]


def test_invalidacia_utne_oba_boxy():
    """Pine `resizeZoneOnInvalidation` — inak box visí v pôvodnej šírke až po expT."""
    z = _zone()
    r = DrawRegistry()
    r.extend(z.boxes(180_000))
    r.extend(z.resize_on_invalidation(1_200_000))
    assert [o.x2_ms for o in r.objects()] == [1_200_000, 1_200_000]


def test_prefarbenie_meni_obrys_oboch_a_vypln_post():
    z = _zone()
    r = DrawRegistry()
    r.extend(z.boxes(180_000))
    r.extend(z.recolor("#10b981"))
    pre, post = r.objects()
    assert pre.border_color == post.border_color == "#10b981d9"
    assert post.fill_color == "#10b98126"
    assert pre.fill_color is None  # pre box je bez výplne aj po prefarbení
