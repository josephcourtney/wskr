from wskr.render.matplotlib.kitty import _BackendKittyAgg


def test_kitty_backend_draw_if_interactive(monkeypatch):
    monkeypatch.setattr("matplotlib.is_interactive", lambda: True)

    class DummyFigure:
        def get_axes(self):
            return [1]

    class DummyCanvas:
        figure = DummyFigure()

    class DummyManager:
        canvas = DummyCanvas()

    monkeypatch.setattr(
        "wskr.mpl.base.Gcf.get_active",
        lambda: type(
            "Manager",
            (),
            {
                "canvas": type(
                    "Canvas", (), {"figure": type("Figure", (), {"get_axes": lambda self: [1]})()}
                )(),
                "show": lambda *a, **kw: None,
            },
        ),
    )
    _BackendKittyAgg.draw_if_interactive()


def test_kitty_backend_show(monkeypatch):
    called = {}

    def fake_show(*args, **kwargs):
        called["ok"] = True

    monkeypatch.setattr("wskr.mpl.base.Gcf.get_active", lambda: type("Manager", (), {"show": fake_show}))
    _BackendKittyAgg.show()
    assert called.get("ok")
