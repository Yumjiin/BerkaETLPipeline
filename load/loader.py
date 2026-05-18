import pandas as pd
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def get_engine(database_url: str) -> Engine:
    """SQLAlchemy 엔진 생성."""
    engine = create_engine(database_url)
    logger.info("[LOAD] DB 연결 성공")
    return engine


def create_tables(engine: Engine) -> None:
    """MySQL 테이블 생성 (없으면 생성, 있으면 스킵)."""
    sql = """
    CREATE TABLE IF NOT EXISTS raw_transactions (
        trans_id   INT PRIMARY KEY,
        account_id INT NOT NULL,
        date       DATE,
        type       VARCHAR(20),
        operation  VARCHAR(50),
        amount     DECIMAL(12, 2),
        balance    DECIMAL(12, 2),
        k_symbol   VARCHAR(30),
        bank       VARCHAR(10),
        account    VARCHAR(20),
        INDEX idx_account_date (account_id, date)
    );

    CREATE TABLE IF NOT EXISTS daily_summary (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        account_id   INT NOT NULL,
        date         DATE NOT NULL,
        total_amount DECIMAL(12, 2),
        tx_count     INT,
        avg_amount   DECIMAL(12, 2),
        max_amount   DECIMAL(12, 2),
        UNIQUE KEY uq_account_date (account_id, date)
    );

    CREATE TABLE IF NOT EXISTS category_summary (
        id           INT AUTO_INCREMENT PRIMARY KEY,
        account_id   INT NOT NULL,
        k_symbol     VARCHAR(30),
        total_amount DECIMAL(12, 2),
        tx_count     INT
    );

    CREATE TABLE IF NOT EXISTS anomaly_flags (
        id         INT AUTO_INCREMENT PRIMARY KEY,
        account_id INT NOT NULL,
        date       DATE,
        method     VARCHAR(30),
        score      FLOAT,
        is_anomaly TINYINT(1),
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_account_date (account_id, date)
    );
    """
    with engine.connect() as conn:
        for statement in sql.strip().split(";"):
            statement = statement.strip()
            if statement:
                conn.execute(text(statement))
        conn.commit()
    logger.info("[LOAD] 테이블 생성 완료")


def load_table(
    df: pd.DataFrame,
    table_name: str,
    engine: Engine,
    chunksize: int = 5000,
) -> None:
    """
    DataFrame을 MySQL 테이블에 적재.
    중복 데이터는 INSERT IGNORE로 무시.
    """
    logger.info(f"[LOAD] {table_name} 적재 시작 — {len(df):,}행")

    cols = ", ".join(df.columns)
    placeholders = ", ".join([f":{c}" for c in df.columns])
    sql = f"INSERT IGNORE INTO {table_name} ({cols}) VALUES ({placeholders})"

    with engine.begin() as conn:
        for i in range(0, len(df), chunksize):
            chunk = df.iloc[i:i + chunksize]
            conn.execute(text(sql), chunk.to_dict(orient="records"))

    logger.info(f"[LOAD] {table_name} 적재 완료")


def load_all(
    cleaned: dict[str, pd.DataFrame],
    aggregated: dict[str, pd.DataFrame],
    database_url: str,
) -> None:
    """전체 적재 실행. pipeline.py 에서 호출."""
    engine = get_engine(database_url)
    create_tables(engine)

    load_table(cleaned["trans"], "raw_transactions", engine, chunksize=5000)
    load_table(aggregated["daily_summary"], "daily_summary", engine)
    load_table(aggregated["category_summary"], "category_summary", engine)

    logger.info("[LOAD] 전체 적재 완료")