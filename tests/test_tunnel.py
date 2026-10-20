# Ceopardy
# https://github.com/obilodeau/ceopardy/
#
# Olivier Bilodeau <olivier@bottomlesspit.org>
# Copyright (C) 2026 Olivier Bilodeau
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
"""Tests for tunnel.py. No network: the ngrok module is stubbed."""

import sys
import types

import pytest

from ceopardy import tunnel


def test_env_token_wins(tmp_path):
    conf = tmp_path / "ngrok.yml"
    conf.write_text("authtoken: from-file\n")
    assert tunnel.find_authtoken({"NGROK_AUTHTOKEN": "from-env"}, [str(conf)]) == "from-env"


@pytest.mark.parametrize(
    "content",
    [
        "authtoken: tok_123\n",  # v2
        'version: "3"\nagent:\n    authtoken: tok_123\n',  # v3
        "version: 2\nauthtoken: 'tok_123'  # mine\nregion: eu\n",
    ],
)
def test_token_from_agent_config(tmp_path, content):
    conf = tmp_path / "ngrok.yml"
    conf.write_text(content)
    assert tunnel.find_authtoken({}, [str(conf)]) == "tok_123"


def test_missing_or_unreadable_config_is_skipped(tmp_path):
    good = tmp_path / "good.yml"
    good.write_text("authtoken: tok_2\n")
    paths = [str(tmp_path / "missing.yml"), str(tmp_path), str(good)]
    assert tunnel.find_authtoken({}, paths) == "tok_2"
    assert tunnel.find_authtoken({}, paths[:2]) is None


def test_config_paths_honour_xdg():
    paths = tunnel.ngrok_config_paths({"XDG_CONFIG_HOME": "/x"}, "/home/me")
    assert paths[0] == "/x/ngrok/ngrok.yml"
    assert "/home/me/Library/Application Support/ngrok/ngrok.yml" in paths


@pytest.mark.parametrize("port", [5001, 6001, "5002"])
def test_forward_addr_is_always_local_buzzer_port(port):
    assert tunnel.forward_addr(port) == "127.0.0.1:{}".format(port)


@pytest.mark.parametrize(
    "buzzer_url,no_tunnel,token,expected",
    [
        ("https://x.trycloudflare.com", False, "tok", "manual"),
        ("https://x.trycloudflare.com", True, None, "manual"),
        ("", True, "tok", "none"),
        ("", False, "tok", "ngrok"),
        ("", False, None, "no-token"),
    ],
)
def test_choose(buzzer_url, no_tunnel, token, expected):
    assert tunnel.choose(buzzer_url, no_tunnel, token) == expected


@pytest.fixture
def fake_ngrok(monkeypatch):
    calls = []

    class Listener:
        def url(self) -> str:
            return "https://quiet-owl.ngrok-free.app"

    def forward(addr, **options):
        calls.append((addr, options))
        if options.get("authtoken") == "bad":
            raise ValueError("failed to connect session", "Your authtoken: bad\n", "ERR_NGROK_4018")
        return Listener()

    monkeypatch.setitem(sys.modules, "ngrok", types.SimpleNamespace(forward=forward))
    return calls


def config_for(port: int = 5001, public_url: str = "") -> dict:
    return {"BUZZER_PORT": port, "BUZZER_PUBLIC_URL": public_url, "BUZZER_TUNNEL": "none"}


def test_setup_opens_the_tunnel_to_the_buzzer_port(fake_ngrok, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    config = config_for(port=6001)
    status = tunnel.setup(
        config, no_tunnel=False, domain="owl.ngrok.app", env={"NGROK_AUTHTOKEN": "t"}
    )
    assert fake_ngrok == [("127.0.0.1:6001", {"authtoken": "t", "domain": "owl.ngrok.app"})]
    assert config["BUZZER_PUBLIC_URL"] == "https://quiet-owl.ngrok-free.app"
    assert config["BUZZER_TUNNEL"] == "ngrok"
    assert "t" not in status.split()


def test_setup_survives_an_ngrok_failure(fake_ngrok, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    config = config_for()
    status = tunnel.setup(config, no_tunnel=False, domain="", env={"NGROK_AUTHTOKEN": "bad"})
    assert config["BUZZER_PUBLIC_URL"] == ""
    assert config["BUZZER_TUNNEL"] == "none"
    assert "ERR_NGROK_4018" in status
    assert "bad" not in status
    assert "\n" not in status


def test_setup_without_token_explains(fake_ngrok, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    config = config_for()
    status = tunnel.setup(config, no_tunnel=False, domain="", env={})
    assert fake_ngrok == []
    assert tunnel.TOKEN_PAGE in status


def test_setup_with_a_manual_url_opens_nothing(fake_ngrok, monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    config = config_for(public_url="https://x.trycloudflare.com")
    tunnel.setup(config, no_tunnel=False, domain="", env={"NGROK_AUTHTOKEN": "t"})
    assert fake_ngrok == []
    assert config["BUZZER_TUNNEL"] == "manual"
