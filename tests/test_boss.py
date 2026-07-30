"""Tests for boss mode — fake Docker log generator."""

from bosskey_stock.boss import BossGenerator


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
    old_lines = bg._lines
    bg.reset()
    # Lines should be regenerated
    assert bg._lines is not None
