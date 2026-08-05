"""Tests for boss mode — fake Docker log generator."""

from bosskey_stock.boss import BossGenerator
from bosskey_stock.i18n import lang


def test_boss_init():
    bg = BossGenerator()
    assert bg._lines is not None
    assert len(bg._lines) > 0


def test_boss_render_contains_docker():
    bg = BossGenerator()
    out = bg.render()
    assert "docker build" in out
    assert "Step" in out
    assert "Running time:" in out


def test_boss_reset():
    bg = BossGenerator()
    bg.reset()
    # Lines should be regenerated
    assert bg._lines is not None


def test_boss_render_zh():
    bg = BossGenerator()
    out = bg.render(lang("zh")["t"])
    assert "docker build" in out
    assert "运行时间" in out
    assert "Running time:" not in out
