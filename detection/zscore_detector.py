import pandas as pd
import logging
from sqlalchemy.engine import Engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


def detect_zscore(
    daily: pd.DataFrame,
    threshold: float = 2.5,
) -> pd.DataFrame:
    """
    일별 지출 데이터에서 Z-Score 기반 이상 거래 탐지.

    Args:
        daily:     daily_summary DataFrame
        threshold: 이상 판단 기준 Z-Score (기본 2.5)

    Returns:
        이상 탐지 결과 DataFrame
    """
    logger.info(f"[ZSCORE] 이상 탐지 시작 — 임계값: {threshold}")

    df = daily.copy()

    # 계좌별로 Z-Score 계산 (transform 방식 — 인덱스 문제 없음)
    mean = df.groupby("account_id")["total_amount"].transform("mean")
    std  = df.groupby("account_id")["total_amount"].transform("std").fillna(0)

    df["z_score"] = (df["total_amount"] - mean) / std.replace(0, 1)
    df["is_anomaly"] = df["z_score"].abs() > threshold
    df["method"]     = "zscore"
    df["score"]      = df["z_score"]

    anomaly_count = df["is_anomaly"].sum()
    total_count   = len(df)
    logger.info(f"[ZSCORE] 탐지 완료 — 전체 {total_count:,}건 중 이상 {anomaly_count:,}건 ({anomaly_count/total_count*100:.2f}%)")

    return df[["account_id", "date", "total_amount", "score", "is_anomaly", "method"]]


def save_anomalies(result: pd.DataFrame, engine: Engine) -> None:
    """
    탐지 결과를 MySQL anomaly_flags 테이블에 저장.
    이상 거래(is_anomaly=True)만 저장.
    """
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM anomaly_flags WHERE method = 'zscore'"))
    logger.info("[ZSCORE] 기존 결과 삭제 완료")

    to_save = result[result["is_anomaly"] == True][["account_id", "date", "method", "score", "is_anomaly"]].copy()
    to_save["is_anomaly"] = to_save["is_anomaly"].astype(int)

    to_save.to_sql(
        name="anomaly_flags",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=5000,
    )
    logger.info(f"[ZSCORE] anomaly_flags 저장 완료 — {len(to_save):,}건 (이상 거래만)")