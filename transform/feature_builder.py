import pandas as pd
import logging
from sqlalchemy.engine import Engine
from sqlalchemy import text

logger = logging.getLogger(__name__)


def build_account_profile(engine: Engine) -> pd.DataFrame:
    """
    계좌별 거래 프로파일 생성.

    MySQL의 daily_summary, category_summary, anomaly_flags 를 읽어서
    계좌별 특징을 숫자로 요약한 테이블을 만든다.

    Returns:
        계좌 프로파일 DataFrame
    """
    logger.info("[FEATURE] 계좌 프로파일 생성 시작")

    # 1. 일별 집계 기반 피처
    daily_query = """
        SELECT
            account_id,
            COUNT(*)                    AS total_days,
            SUM(total_amount)           AS total_spent,
            AVG(total_amount)           AS avg_daily_spent,
            MAX(total_amount)           AS max_daily_spent,
            MIN(total_amount)           AS min_daily_spent,
            STDDEV(total_amount)        AS std_daily_spent,
            AVG(tx_count)               AS avg_daily_tx_count,
            MAX(tx_count)               AS max_daily_tx_count,
            MIN(date)                   AS first_tx_date,
            MAX(date)                   AS last_tx_date,
            DATEDIFF(MAX(date), MIN(date)) AS active_days
        FROM daily_summary
        GROUP BY account_id
    """
    daily_features = pd.read_sql(daily_query, engine)
    logger.info(f"[FEATURE] 일별 피처 완료 — {len(daily_features):,}개 계좌")

    # 2. 업종별 집계 기반 피처 (주요 업종)
    category_query = """
        SELECT
            account_id,
            k_symbol AS top_category,
            total_amount
        FROM category_summary c1
        WHERE total_amount = (
            SELECT MAX(total_amount)
            FROM category_summary c2
            WHERE c2.account_id = c1.account_id
        )
    """
    category_features = pd.read_sql(category_query, engine)
    # 동점 시 첫 번째만
    category_features = category_features.groupby("account_id").first().reset_index()
    category_features = category_features[["account_id", "top_category"]]
    logger.info(f"[FEATURE] 업종 피처 완료 — {len(category_features):,}개 계좌")

    # 3. 이상 탐지 기반 피처
    anomaly_query = """
        SELECT
            account_id,
            COUNT(*)                        AS total_anomaly_flags,
            SUM(CASE WHEN method = 'zscore'           AND is_anomaly = 1 THEN 1 ELSE 0 END) AS zscore_anomaly_count,
            SUM(CASE WHEN method = 'isolation_forest' AND is_anomaly = 1 THEN 1 ELSE 0 END) AS iforest_anomaly_count,
            SUM(CASE WHEN method = 'autoencoder'      AND is_anomaly = 1 THEN 1 ELSE 0 END) AS ae_anomaly_count
        FROM anomaly_flags
        WHERE is_anomaly = 1
        GROUP BY account_id
    """
    anomaly_features = pd.read_sql(anomaly_query, engine)
    logger.info(f"[FEATURE] 이상 탐지 피처 완료 — {len(anomaly_features):,}개 계좌")

    # 4. 전체 합치기
    profile = daily_features.merge(category_features, on="account_id", how="left")
    profile = profile.merge(anomaly_features, on="account_id", how="left")

    # 결측치 처리 (이상 없는 계좌는 0)
    anomaly_cols = ["total_anomaly_flags", "zscore_anomaly_count", "iforest_anomaly_count", "ae_anomaly_count"]
    profile[anomaly_cols] = profile[anomaly_cols].fillna(0).astype(int)
    profile["top_category"] = profile["top_category"].fillna("unknown")

    # 5. 이상 비율 계산
    profile["anomaly_rate"] = (profile["zscore_anomaly_count"] / profile["total_days"]).round(4)

    logger.info(f"[FEATURE] 계좌 프로파일 완성 — {len(profile):,}개 계좌 × {len(profile.columns)}개 피처")
    return profile


def save_account_profile(profile: pd.DataFrame, engine: Engine) -> None:
    """계좌 프로파일을 MySQL account_profiles 테이블에 저장."""
    create_sql = """
    CREATE TABLE IF NOT EXISTS account_profiles (
        account_id          INT PRIMARY KEY,
        total_days          INT,
        total_spent         DECIMAL(15, 2),
        avg_daily_spent     DECIMAL(12, 2),
        max_daily_spent     DECIMAL(12, 2),
        min_daily_spent     DECIMAL(12, 2),
        std_daily_spent     DECIMAL(12, 2),
        avg_daily_tx_count  DECIMAL(8, 2),
        max_daily_tx_count  INT,
        first_tx_date       DATE,
        last_tx_date        DATE,
        active_days         INT,
        top_category        VARCHAR(30),
        total_anomaly_flags INT,
        zscore_anomaly_count  INT,
        iforest_anomaly_count INT,
        ae_anomaly_count      INT,
        anomaly_rate        DECIMAL(8, 4),
        updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """
    with engine.begin() as conn:
        conn.execute(text(create_sql))
        conn.execute(text("TRUNCATE TABLE account_profiles"))

    profile.to_sql(
        name="account_profiles",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=1000,
    )
    logger.info(f"[FEATURE] account_profiles 저장 완료 — {len(profile):,}건")