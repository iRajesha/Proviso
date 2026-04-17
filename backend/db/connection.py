import oracledb
from backend.config import settings

# Thread-safe connection pool
_pool: oracledb.ConnectionPool | None = None


def init_pool() -> None:
    global _pool
    _pool = oracledb.create_pool(
        user=settings.adb_user,
        password=settings.adb_password,
        dsn=settings.adb_dsn,
        config_dir=settings.adb_wallet_dir,
        wallet_location=settings.adb_wallet_dir,
        wallet_password=settings.adb_password,
        min=1,
        max=5,
        increment=1,
    )


def get_connection() -> oracledb.Connection:
    if _pool is None:
        init_pool()
    return _pool.acquire()
