import pandas as pd
import logging
from sklearn.ensemble import IsolationForest
from sqlalchemy.engine import Engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


def detect_isolation_forest(
    daily: pd.DataFrame,
    contamination: float = 0.05,
) -> pd.DataFrame:
    """
    Isolation Forest 기반 이상 탐지.

    Z-Score와 달리 다변수(금액/건수/평균/최대)를 동시에 고려.

    Args:
        daily:         daily_summary DataFrame
        contamination: 이상 비율 예상값 (기본 5%)

    Returns:
        이상 탐지 결과 DataFrame
    """
    logger.info(f"[IFOREST] 이상 탐지 시작 — contamination: {contamination}")

    df = daily.copy()

    # 입력 피처 4개
    features = ["total_amount", "tx_count", "avg_amount", "max_amount"]

    # 결측치 있으면 0으로 채우기
    df[features] = df[features].fillna(0)

    # Isolation Forest 학습 + 예측
    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=100,
    )
    df["anomaly_score"] = model.fit_predict(df[features])

    # fit_predict 결과: 1 = 정상, -1 = 이상
    df["is_anomaly"] = df["anomaly_score"] == -1

    # score 컬럼: decision_function 값 (낮을수록 이상)
    df["score"] = model.decision_function(df[features])
    df["method"] = "isolation_forest"

    anomaly_count = df["is_anomaly"].sum()
    total_count   = len(df)
    logger.info(f"[IFOREST] 탐지 완료 — 전체 {total_count:,}건 중 이상 {anomaly_count:,}건 ({anomaly_count/total_count*100:.2f}%)")

    return df[["account_id", "date", "total_amount", "score", "is_anomaly", "method"]]


def save_anomalies(result: pd.DataFrame, engine: Engine) -> None:
    """
    탐지 결과를 MySQL anomaly_flags 테이블에 저장.
    기존 isolation_forest 결과는 덮어씀.
    """
    # 기존 isolation_forest 결과 삭제
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM anomaly_flags WHERE method = 'isolation_forest'"))
    logger.info("[IFOREST] 기존 결과 삭제 완료")

    to_save = result[["account_id", "date", "method", "score", "is_anomaly"]].copy()
    to_save["is_anomaly"] = to_save["is_anomaly"].astype(int)

    to_save.to_sql(
        name="anomaly_flags",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=5000,
    )
    logger.info(f"[IFOREST] anomaly_flags 저장 완료 — {len(to_save):,}건")