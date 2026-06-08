import pandas as pd
import logging
from sqlalchemy.engine import Engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


def detect_zscore(
    daily: pd.DataFrame,
    threshold: float = 2.5,
) -> pd.DataFrame:

    logger.info(f"[ZSCORE] 이상 탐지 시작 — 임계값: {threshold}")

    df = daily.copy()

    # 변경: 변수가 아닌 컬럼으로 저장
    df["mean"] = df.groupby("account_id")["total_amount"].transform("mean")
    df["std"]  = df.groupby("account_id")["total_amount"].transform("std").fillna(0)

    df["z_score"]    = (df["total_amount"] - df["mean"]) / df["std"].replace(0, 1)
    df["is_anomaly"] = df["z_score"].abs() > threshold
    df["method"]     = "zscore"
    df["score"]      = df["z_score"]

    anomaly_count = df["is_anomaly"].sum()
    total_count   = len(df)
    logger.info(f"[ZSCORE] 탐지 완료 — 전체 {total_count:,}건 중 이상 {anomaly_count:,}건 ({anomaly_count/total_count*100:.2f}%)")

    return df[["account_id", "date", "total_amount", "mean", "std", "score", "is_anomaly", "method"]]


def save_anomalies(result: pd.DataFrame, engine: Engine) -> None:
    """
    탐지 결과를 MySQL anomaly_flags 테이블에 저장.
    이상 거래(is_anomaly=True)만 저장.
    zscore_detail 테이블에 판단 근거 저장.
    """
    # ── anomaly_flags 저장 (기존과 동일) ──
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM anomaly_flags WHERE method = 'zscore'"))
    logger.info("[ZSCORE] 기존 결과 삭제 완료")

    to_save = result[result["is_anomaly"] == True][
        ["account_id", "date", "method", "score", "is_anomaly"]
    ].copy()
    to_save["is_anomaly"] = to_save["is_anomaly"].astype(int)

    to_save.to_sql(
        name="anomaly_flags",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=5000,
    )
    logger.info(f"[ZSCORE] anomaly_flags 저장 완료 — {len(to_save):,}건")

    # ── zscore_detail 저장 (판단 근거) ──
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS zscore_detail (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                account_id  INT NOT NULL,
                date        DATE NOT NULL,
                amount      DECIMAL(12,2),
                mean        DECIMAL(12,2),
                std         DECIMAL(12,2),
                z_value     DECIMAL(8,4),
                is_anomaly  TINYINT(1)
            )
        """))
        conn.execute(text("DELETE FROM zscore_detail"))

        detail = result.copy()
        detail["z_value"]    = detail["score"].round(4)
        detail["amount"]     = detail["total_amount"]
        detail["is_anomaly"] = detail["is_anomaly"].astype(int)


    detail[["account_id", "date", "amount", "mean", "std", "z_value", "is_anomaly"]].to_sql(
        name="zscore_detail",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=5000,
    )
    logger.info(f"[ZSCORE] zscore_detail 저장 완료 — {len(detail):,}건")