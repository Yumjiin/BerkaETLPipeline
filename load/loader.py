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
    """
    MySQL 테이블 생성 (없으면 생성, 있으면 스킵).
    설계서 스키마 기준.
    """
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
    if_exists: str = "append",
) -> None:
    """
    DataFrame을 MySQL 테이블에 적재.

    Args:
        df:         적재할 DataFrame
        table_name: MySQL 테이블 이름
        engine:     SQLAlchemy 엔진
        chunksize:  한 번에 insert할 행 수 (기본 5000)
        if_exists:  테이블 존재 시 처리 방법 (append / replace)
    """
    logger.info(f"[LOAD] {table_name} 적재 시작 — {len(df):,}행")
    df.to_sql(
        name=table_name,
        con=engine,
        if_exists=if_exists,
        index=False,
        chunksize=chunksize,
    )
    logger.info(f"[LOAD] {table_name} 적재 완료")


def load_all(
    cleaned: dict[str, pd.DataFrame],
    aggregated: dict[str, pd.DataFrame],
    database_url: str,
) -> None:
    """
    전체 적재 실행.
    pipeline.py 에서 호출하는 메인 함수.

    Args:
        cleaned:      clean_all() 결과 (정제된 테이블들)
        aggregated:   aggregate_all() 결과 (집계 테이블들)
        database_url: MySQL 접속 URL
    """
    engine = get_engine(database_url)

    # 테이블 생성
    create_tables(engine)

    # raw_transactions 적재 (100만 건 → chunksize로 나눠서)
    load_table(cleaned["trans"], "raw_transactions", engine, chunksize=5000)

    # daily_summary 적재
    load_table(aggregated["daily_summary"], "daily_summary", engine)

    # category_summary 적재
    load_table(aggregated["category_summary"], "category_summary", engine)

    logger.info("[LOAD] 전체 적재 완료")