import pandas as pd
import logging
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def detect_zscore(
    daily: pd.DataFrame,
    threshold: float = 2.5,
) -> pd.DataFrame:
    """
    일별 지출 데이터에서 Z-Score 기반 이상 거래 탐지.

    Args:
        daily:     daily_summary DataFrame (account_id, date, total_amount 포함)
        threshold: 이상 판단 기준 Z-Score (기본 2.5)

    Returns:
        이상 탐지 결과 DataFrame
        컬럼: account_id, date, total_amount, z_score, is_anomaly, method
    """
    logger.info(f"[ZSCORE] 이상 탐지 시작 — 임계값: {threshold}")

    df = daily.copy()

    # 계좌별로 Z-Score 계산 — transform 사용으로 인덱스 보존
    grouped = df.groupby('account_id')['total_amount']
    means = grouped.transform('mean')
    stds  = grouped.transform('std')
    # 표준편차가 0인 경우 z_score를 0으로 설정
    df['z_score'] = (df['total_amount'] - means) / stds
    df['z_score'] = df['z_score'].fillna(0.0)

    # 이상 여부 판단
    df["is_anomaly"] = df["z_score"].abs() > threshold
    df["method"]     = "zscore"
    df["score"]      = df["z_score"]          # anomaly_flags 테이블 score 컬럼용

    anomaly_count = df["is_anomaly"].sum()
    total_count   = len(df)
    logger.info(f"[ZSCORE] 탐지 완료 — 전체 {total_count:,}건 중 이상 {anomaly_count:,}건 ({anomaly_count/total_count*100:.2f}%)")

    # Debugging: log index and columns to diagnose missing account_id
    logger.info(f"[ZSCORE] df.columns before return: {list(df.columns)}")
    try:
        logger.info(f"[ZSCORE] df.index.names: {df.index.names}")
    except Exception:
        logger.info("[ZSCORE] df.index.names: (failed to get)")

    # groupby.apply may put the grouping key into the index; ensure account_id is a column
    if "account_id" not in df.columns:
        df = df.reset_index()
        logger.info(f"[ZSCORE] Reset index; new columns: {list(df.columns)}")

    return df[["account_id", "date", "total_amount", "z_score", "score", "is_anomaly", "method"]]


def save_anomalies(result: pd.DataFrame, engine: Engine) -> None:
    """
    탐지 결과를 MySQL anomaly_flags 테이블에 저장.

    Args:
        result: detect_zscore() 반환값
        engine: SQLAlchemy 엔진
    """
    # anomaly_flags 테이블 컬럼에 맞게 정리
    to_save = result[["account_id", "date", "method", "score", "is_anomaly"]].copy()
    to_save["is_anomaly"] = to_save["is_anomaly"].astype(int)  # bool → 0/1

    to_save.to_sql(
        name="anomaly_flags",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=5000,
    )
    logger.info(f"[ZSCORE] anomaly_flags 저장 완료 — {len(to_save):,}건")