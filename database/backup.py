import shutil
from datetime import datetime
from pathlib import Path

_DB = Path("drip.db")
_BACKUP_DIR = Path("backups")
_MAX_BACKUPS = 7


def backup_db() -> None:
    if not _DB.exists():
        return
    _BACKUP_DIR.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    shutil.copy2(_DB, _BACKUP_DIR / f"drip_{stamp}.db")
    backups = sorted(_BACKUP_DIR.glob("drip_*.db"))
    for old in backups[:-_MAX_BACKUPS]:
        old.unlink()
