import uvicorn

from genetic_opt.web import app as web_app

# ── main Tests ─────────────────────────────────────────────────────────


def _served_on(monkeypatch) -> list[tuple[str, int]]:
    """Where `main` serves, without starting a server or setting up logs."""
    served: list[tuple[str, int]] = []
    monkeypatch.setattr(
        uvicorn, "run", lambda app, host, port: served.append((host, port))
    )
    monkeypatch.setattr(web_app.logging, "basicConfig", lambda **kw: None)
    web_app.main()
    return served


def test_main_serves_on_the_default_port(monkeypatch):
    monkeypatch.delenv("GENETIC_OPT_WEB_PORT", raising=False)
    assert _served_on(monkeypatch) == [("127.0.0.1", web_app.DEFAULT_PORT)]


def test_main_serves_on_the_port_of_the_environment(monkeypatch):
    monkeypatch.setenv("GENETIC_OPT_WEB_PORT", "6100")
    assert _served_on(monkeypatch) == [("127.0.0.1", 6100)]
