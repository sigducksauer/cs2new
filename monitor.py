#!/usr/bin/env python3
"""
CS2 Update Monitor
Monitora atualizações oficiais do Counter-Strike 2 via Steam News API
e envia notificações formatadas para Discord Webhook.
"""

import os
import sys
import json
import re
import html
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ==================== CONFIGURAÇÕES ====================

STEAM_API_URL = "https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
APP_ID = 730
LAST_ID_FILE = "last_news_id.txt"
REQUEST_TIMEOUT = 12
USER_AGENT = "CS2-Update-Monitor/1.4 (+github-actions)"

UPDATE_KEYWORDS = [
    "update",
    "patch",
    "counter-strike 2 update",
    "release notes",
    "hotfix",
]

# ========================================================


def create_session() -> requests.Session:
    session = requests.Session()

    retries = Retry(
        total=3,
        backoff_factor=1.3,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )

    adapter = HTTPAdapter(max_retries=retries)

    session.mount("https://", adapter)

    session.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "application/json",
    })

    return session


def get_last_id() -> Optional[str]:
    try:
        if os.path.exists(LAST_ID_FILE):
            with open(LAST_ID_FILE, "r", encoding="utf-8") as f:
                value = f.read().strip()

            return value or None

    except Exception as e:
        print(f"[WARN] Erro ao ler last_id: {e}")

    return None


def save_last_id(news_id: str) -> None:
    try:
        with open(LAST_ID_FILE, "w", encoding="utf-8") as f:
            f.write(str(news_id))

    except Exception as e:
        print(f"[ERROR] Erro ao salvar last_id: {e}")


def is_relevant_update(title: str) -> bool:
    title_lower = title.lower()

    return any(
        keyword in title_lower
        for keyword in UPDATE_KEYWORDS
    )


# ==================== FORMATADOR ====================


def clean_steam_content(content: str) -> str:
    """
    Converte o BBCode usado pela Steam em Markdown compatível
    com Discord.
    """

    if not content:
        return "Sem detalhes adicionais."

    text = content

    # Decodifica entidades HTML
    text = html.unescape(text)

    # Normaliza quebras de linha
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # ----------------------------------------------------
    # LINKS
    # [url="LINK"]Texto[/url]
    # ----------------------------------------------------

    text = re.sub(
        r'\[url="([^"]+)"\](.*?)\[/url\]',
        r'[\2](\1)',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    text = re.sub(
        r'\[url\](.*?)\[/url\]',
        r'\1',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # ----------------------------------------------------
    # CABEÇALHOS / SEÇÕES
    # ----------------------------------------------------

    # [p][ GAMEPLAY ][/p]
    text = re.sub(
        r'\[p\]\s*\[\s*([A-Z0-9][A-Z0-9 _-]*)\s*\]\s*\[/p\]',
        lambda m: f"\n\n**{m.group(1).strip()}**\n",
        text,
        flags=re.IGNORECASE,
    )

    # [p]Cache[/p]
    text = re.sub(
        r'\[p\]\s*([A-Za-z0-9][^[]{0,100}?)\s*\[/p\]',
        lambda m: (
            f"\n**{m.group(1).strip()}**\n"
            if len(m.group(1).strip()) < 60
            else f"\n{m.group(1).strip()}\n"
        ),
        text,
        flags=re.IGNORECASE,
    )

    # ----------------------------------------------------
    # PARÁGRAFOS
    # ----------------------------------------------------

    text = re.sub(
        r'\[/?p\]',
        '\n',
        text,
        flags=re.IGNORECASE,
    )

    # ----------------------------------------------------
    # LISTAS
    # ----------------------------------------------------

    text = re.sub(
        r'\[list\]',
        '\n',
        text,
        flags=re.IGNORECASE,
    )

    text = re.sub(
        r'\[/list\]',
        '\n',
        text,
        flags=re.IGNORECASE,
    )

    # Steam normalmente usa [] como item de lista
    text = re.sub(
        r'\[\]',
        '\n- ',
        text,
    )

    # ----------------------------------------------------
    # TAGS DE FORMATAÇÃO
    # ----------------------------------------------------

    replacements = {
        "[b]": "**",
        "[/b]": "**",
        "[i]": "*",
        "[/i]": "*",
        "[u]": "__",
        "[/u]": "__",
        "[code]": "`",
        "[/code]": "`",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # ----------------------------------------------------
    # REMOVE TAGS RESTANTES
    # ----------------------------------------------------

    text = re.sub(
        r'\[[^\]]+\]',
        '',
        text,
    )

    # ----------------------------------------------------
    # LIMPEZA
    # ----------------------------------------------------

    # Remove espaços antes/depois das linhas
    lines = []

    for line in text.splitlines():
        line = line.strip()

        if line:
            lines.append(line)

    text = "\n".join(lines)

    # Evita excesso de linhas vazias
    text = re.sub(r'\n{3,}', '\n\n', text)

    # Corrige bullets duplicados
    text = re.sub(
        r'-\s*- ',
        '- ',
        text,
    )

    return text.strip()


# ========================================================


def fetch_steam_news(
    session: requests.Session,
) -> List[Dict[str, Any]]:

    params = {
        "appid": APP_ID,
        "count": 10,
        "maxlength": 0,
        "feeds": "steam_community_announcements",
    }

    try:
        response = session.get(
            STEAM_API_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        return data.get(
            "appnews",
            {},
        ).get(
            "newsitems",
            [],
        )

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Falha na Steam API: {e}")
        return []

    except json.JSONDecodeError:
        print("[ERROR] JSON inválido da Steam API")
        return []


def send_discord_notification(
    webhook_url: str,
    title: str,
    url: str,
    contents: str,
    timestamp: int,
) -> bool:

    # Limpa o conteúdo da Steam
    description = clean_steam_content(contents)

    # Discord Embed possui limite de 4096 caracteres
    if len(description) > 3900:
        description = description[:3900] + "\n\n**...continua na notícia original.**"

    date_str = datetime.fromtimestamp(
        timestamp,
        tz=timezone.utc,
    ).strftime("%d/%m/%Y %H:%M UTC")

    embed = {
        "title": title,
        "url": url,
        "description": description,
        "color": 0x66C0F4,
        "footer": {
            "text": f"Counter-Strike 2 • {date_str}"
        },
        "author": {
            "name": "CS2 Update Monitor"
        },
    }

    payload = {
        "username": "CS2 Updates",
        "embeds": [embed],
        "allowed_mentions": {
            "parse": []
        },
    }

    try:
        response = requests.post(
            webhook_url,
            json=payload,
            timeout=10,
            headers={
                "User-Agent": USER_AGENT
            },
        )

        if response.status_code in (200, 204):
            print(
                f"[OK] Notificação enviada → {title}"
            )
            return True

        print(
            f"[ERROR] Discord {response.status_code}: "
            f"{response.text[:150]}"
        )

        return False

    except Exception as e:
        print(
            f"[ERROR] Falha ao enviar para Discord: {e}"
        )

        return False


# ==================== MAIN ====================


def main() -> int:

    webhook = os.getenv("DISCORD_WEBHOOK")

    if not webhook:
        print(
            "[CRITICAL] Secret DISCORD_WEBHOOK "
            "não configurado."
        )
        return 1

    print(
        f"[{datetime.now(timezone.utc).isoformat()}] "
        "Verificando atualizações..."
    )

    session = create_session()

    news_items = fetch_steam_news(session)

    if not news_items:
        print(
            "[INFO] Nenhuma notícia retornada."
        )
        return 0

    last_id = get_last_id()

    latest = news_items[0]

    current_id = str(
        latest.get("gid", "")
    )

    if not current_id:
        print(
            "[WARN] Notícia sem GID."
        )
        return 0

    if current_id == last_id:
        print(
            "[INFO] Nenhuma atualização nova."
        )
        return 0

    title = latest.get(
        "title",
        "Sem título",
    )

    url = latest.get(
        "url",
        "",
    )

    contents = latest.get(
        "contents",
        "",
    )

    timestamp = latest.get(
        "date",
        0,
    )

    print(
        f"[INFO] Nova notícia: {title}"
    )

    if is_relevant_update(title):

        success = send_discord_notification(
            webhook,
            title,
            url,
            contents,
            timestamp,
        )

        if success:
            save_last_id(current_id)

        else:
            print(
                "[WARN] Envio falhou. "
                "ID não salvo para nova tentativa."
            )

            return 1

    else:

        print(
            f"[INFO] Ignorada (não é update): {title}"
        )

        save_last_id(current_id)

    return 0


if __name__ == "__main__":
    sys.exit(main())
