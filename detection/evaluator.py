import pandas as pd
import logging
from sqlalchemy.engine import Engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


def evaluate(engine: Engine) -> pd.DataFrame:
    """
    anomaly_flags 테이블에서 3가지 모델 결과를 읽어
    고신뢰 이상 거래를 찾는다.

    고신뢰 이상 = 2개 이상 모델이 공통으로 탐지한 거래
    """
    logger.info("[EVAL] 모델 간 탐지 결과 비교 시작")

    query = """
        SELECT account_id, date, method
        FROM   anomaly_flags
        WHERE  is_anomaly = 1
    """
    flags = pd.read_sql(query, engine)
    logger.info(f"[EVAL] 전체 이상 플래그 — {len(flags):,}건")

    for method, group in flags.groupby("method"):
        logger.info(f"[EVAL]   {method}: {len(group):,}건")

    grouped = (
        flags.groupby(["account_id", "date"])
        .agg(
            detected_by=("method", lambda x: ", ".join(sorted(x))),
            model_count =("method", "count"),
        )
        .reset_index()
    )

    high_confidence = grouped[grouped["model_count"] >= 2].copy()
    high_confidence = high_confidence.sort_values("model_count", ascending=False)

    logger.info(f"[EVAL] 고신뢰 이상 거래 (2개 이상 모델 공통) — {len(high_confidence):,}건")
    logger.info(f"[EVAL] 3개 모델 모두 탐지 — {len(high_confidence[high_confidence['model_count'] == 3]):,}건")
    logger.info(f"[EVAL] 2개 모델 탐지      — {len(high_confidence[high_confidence['model_count'] == 2]):,}건")

    return high_confidence


def precision_at_k(engine: Engine, k: int = 50) -> None:
    """
    Precision@K 평가 — 중복 제거 후 상위 K건 출력.
    """
    logger.info(f"[EVAL] Precision@{k} 평가")

    # account_id + date 기준 중복 제거, 최고 score 기준으로 대표값 선택
    query = f"""
        SELECT   account_id, date,
                 GROUP_CONCAT(method ORDER BY method) AS methods,
                 MAX(score) AS max_score
        FROM     anomaly_flags
        WHERE    is_anomaly = 1
        GROUP BY account_id, date
        ORDER BY max_score DESC
        LIMIT    {k}
    """
    top_k = pd.read_sql(query, engine)

    logger.info(f"[EVAL] 상위 {k}건 이상 거래 (중복 제거):")
    logger.info(f"\n{top_k.to_string(index=False)}")


def save_high_confidence(result: pd.DataFrame, engine: Engine) -> None:
    """고신뢰 이상 거래를 MySQL high_confidence_anomalies 테이블에 저장."""
    create_sql = """
    CREATE TABLE IF NOT EXISTS high_confidence_anomalies (
        id          INT AUTO_INCREMENT PRIMARY KEY,
        account_id  INT NOT NULL,
        date        DATE NOT NULL,
        detected_by VARCHAR(100),
        model_count INT,
        created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_account_date (account_id, date)
    );
    """
    with engine.begin() as conn:
        conn.execute(text(create_sql))
        conn.execute(text("TRUNCATE TABLE high_confidence_anomalies"))

    result.to_sql(
        name="high_confidence_anomalies",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=5000,
    )
    logger.info(f"[EVAL] high_confidence_anomalies 저장 완료 — {len(result):,}건")