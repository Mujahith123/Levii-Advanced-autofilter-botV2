"""
levii_credits.py — Attribution & Integrity module for Levii Bot
================================================================
Author  : @muja_tg18  (Telegram)
Project : Levii — Auto-Filter Bot
Purpose : Embeds author credit, verifies project identity at startup,
          and warns / disables non-critical features when the credit
          or project name has been tampered with.

NOTE: This is not a hard DRM lock — determined users can edit source.
      This module is designed to make casual removal highly visible
      and inconvenient, and to leave a consistent paper-trail in logs.
"""

import logging
import os
import sys

log = logging.getLogger(__name__)

# ── Canonical values ─────────────────────────────────────────────────
AUTHOR_HANDLE   = "@muja_tg18"
AUTHOR_TELEGRAM = "https://t.me/muja_tg18"
PROJECT_NAME    = "Levii"
CREDIT_LINE     = f"This repo fully created by Telegram {AUTHOR_HANDLE}"

# Features that are softly disabled when integrity fails
# (add feature flags here as the bot grows)
_INTEGRITY_OK   = True
_INTEGRITY_WARN_SENT = False

# ── ASCII banner printed to stdout / log at startup ──────────────────
CREDIT_BANNER = f"""
╔══════════════════════════════════════════════════════════════╗
║                    {PROJECT_NAME} — Levii Bot                         ║
║                                                              ║
║   Built entirely by  {AUTHOR_HANDLE}                       ║
║   Telegram           {AUTHOR_TELEGRAM}  ║
║                                                              ║
║   Removing or altering this credit is prohibited.           ║
╚══════════════════════════════════════════════════════════════╝
"""


def _check_file_credit(filepath: str, markers: list[str]) -> bool:
    """Return True if *all* markers are present in the file."""
    try:
        text = open(filepath, encoding="utf-8", errors="replace").read()
        return all(m in text for m in markers)
    except Exception:
        return False


def verify_integrity() -> bool:
    """
    Run integrity checks.  Returns True if everything looks fine,
    False if tampering is detected (also sets _INTEGRITY_OK = False).
    """
    global _INTEGRITY_OK

    failures: list[str] = []

    
    if not _check_file_credit(__file__, [AUTHOR_HANDLE, PROJECT_NAME]):
        failures.append("levii_credits.py is missing the author credit")

    
    script_path = os.path.join(os.path.dirname(__file__), "Script.py")
    if not _check_file_credit(script_path, ["muja_tg18"]):
        failures.append("Script.py is missing the author credit (@muja_tg18)")

    
    bot_path = os.path.join(os.path.dirname(__file__), "bot.py")
    if not _check_file_credit(bot_path, ["levii_credits"]):
        failures.append("bot.py no longer imports levii_credits — credit check bypassed")

    
    info_path = os.path.join(os.path.dirname(__file__), "info.py")
    if not _check_file_credit(info_path, ["Levii"]):
        failures.append("info.py: project name 'Levii' has been removed")

    if failures:
        _INTEGRITY_OK = False
        log.warning("=" * 60)
        log.warning("⚠️  LEVII INTEGRITY CHECK FAILED")
        log.warning(f"    Author: {AUTHOR_HANDLE}")
        log.warning("    The following attribution violations were detected:")
        for f in failures:
            log.warning(f"      • {f}")
        log.warning("    Non-critical features have been disabled.")
        log.warning("    Please restore the original credit to re-enable them.")
        log.warning("=" * 60)
        return False

    log.info(f"✅ Levii integrity OK — built by {AUTHOR_HANDLE}")
    return True


def is_feature_enabled(feature_name: str = "generic") -> bool:
    """
    Call this guard before running any non-critical feature.
    Returns False (with a log warning) when integrity has failed.
    """
    if not _INTEGRITY_OK:
        global _INTEGRITY_WARN_SENT
        if not _INTEGRITY_WARN_SENT:
            log.warning(
                f"🚫 Feature '{feature_name}' disabled — Levii attribution has been "
                f"tampered with. Restore credit to {AUTHOR_HANDLE} to re-enable."
            )
            _INTEGRITY_WARN_SENT = True
        return False
    return True


def print_banner():
    """Print the credit banner to stdout (visible in Koyeb / Heroku logs)."""
    print(CREDIT_BANNER, flush=True)


def startup_check():
    """
    Master function — call once from bot.py at the very start.
    Prints the banner, runs integrity checks, logs results.
    """
    print_banner()
    ok = verify_integrity()
    if not ok:
        # Non-fatal: bot continues, but degraded
        log.warning(
            "Bot starting in DEGRADED mode due to attribution tampering. "
            f"Original author: {AUTHOR_HANDLE}"
        )
    return ok
