"""
Centrální konfigurace loggingu.

Volat jednou na startu aplikace (např. v main.py před vytvořením QApplication):

    from gui.logging_setup import setup_logging
    setup_logging()

Tímto se nastaví pouze konzolový výstup. Soubor se založí teprve když
uživatel zadá název měření — log soubor pak vznikne vedle CSV se stejným
jménem (jen příponou .log).

Jednotlivé moduly pak jen:

    import logging
    logger = logging.getLogger(__name__)
    logger.info("...")
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

_initialized = False
_measurement_handler: Optional[logging.Handler] = None
_measurement_path: Optional[str] = None


def setup_logging(
    console_level: int = logging.INFO,
) -> None:
    """
    Nakonfiguruje root logger s konzolovým handlerem.

    Souborový log se vytvoří až voláním attach_measurement_log(),
    což typicky proběhne při zadání názvu měření v GUI.

    Idempotentní — opakovaná volání nepřidávají duplicitní handlery.
    """
    global _initialized
    if _initialized:
        return

    root = logging.getLogger()
    root.setLevel(console_level)

    console = logging.StreamHandler()
    console.setLevel(console_level)
    console.setFormatter(_formatter())
    root.addHandler(console)

    _initialized = True
    root.info("Logging initialized (console only; file log starts with measurement)")


def attach_measurement_log(
    csv_path: str,
    log_dir: str = "data/logs",
    file_level: int = logging.INFO,
    max_bytes: int = 5 * 1024 * 1024,
    backup_count: int = 3,
) -> str:
    """
    Připojí souborový handler pojmenovaný podle CSV, uložený v log_dir.
    'data/gpz_foo_2025-04-29.csv' → 'data/logs/gpz_foo_2025-04-29.log'

    Pokud už existuje předchozí měřicí log (od jiného CSV), nejprve ho odpojí
    a zavře — v daný okamžik tak běží maximálně jeden měřicí log + konzole.

    Returns:
        Plná cesta k log souboru.
    """
    global _measurement_handler, _measurement_path

    # Vezmi jen jméno souboru (bez složky CSV) a přepiš příponu .csv → .log
    csv_basename = os.path.basename(csv_path)
    log_basename = os.path.splitext(csv_basename)[0] + ".log"
    log_path = os.path.join(log_dir, log_basename)

    # Idempotence: stejný soubor 2× po sobě nic nedělá
    if _measurement_handler is not None and _measurement_path == log_path:
        return log_path

    # Odpoj předchozí měřicí handler, pokud existoval
    detach_measurement_log()

    # Vytvoř adresář pro log soubor (data/logs apod.)
    dir_part = os.path.dirname(log_path)
    if dir_part:
        os.makedirs(dir_part, exist_ok=True)

    handler = RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(file_level)
    handler.setFormatter(_formatter())

    logging.getLogger().addHandler(handler)
    _measurement_handler = handler
    _measurement_path = log_path

    logging.getLogger().info("Measurement log attached → %s", log_path)
    return log_path


def detach_measurement_log() -> None:
    """
    Odpojí a zavře aktuální měřicí log handler (pokud nějaký existuje).
    Volat při změně CSV nebo na konci aplikace.
    """
    global _measurement_handler, _measurement_path

    if _measurement_handler is None:
        return

    root = logging.getLogger()
    root.info("Detaching measurement log: %s", _measurement_path)

    try:
        root.removeHandler(_measurement_handler)
        _measurement_handler.close()
    except Exception:
        # Neúspěch při zavírání nesmí shodit aplikaci
        root.exception("Failed to cleanly close measurement log handler")

    _measurement_handler = None
    _measurement_path = None


def _formatter() -> logging.Formatter:
    return logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )