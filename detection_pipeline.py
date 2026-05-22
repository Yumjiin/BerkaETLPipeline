import logging
import time
import pandas as pd
from config import DATABASE_URL, ZSCORE_THRESHOLD, ISOLATION_CONTAMINATION
from load.loader import get_engine
from detection.zscore_detector import detect_zscore, save_anomalies as save_zscore
from detection.isolation_forest import detect_isolation_forest, save_anomalies as save_iforest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run():
    logger.info("=" * 50)
    logger.info("이상 탐지 파이프라인 시작")
    logger.info("=" * 50)

    start = time.time()
    engine = get_engine(DATABASE_URL)

    # ── MySQL에서 daily_summary 읽기 ────────────────
    logger.info("[1/3] MySQL에서 daily_summary 로딩")
    daily = pd.read_sql(
        "SELECT account_id, date, total_amount, tx_count, avg_amount, max_amount FROM daily_summary",
        engine
    )
    logger.info(f"[1/3] 로딩 완료 — {len(daily):,}행")

    # ── Z-Score 이상 탐지 ───────────────────────────
    logger.info("[2/3] Z-Score 이상 탐지")
    zscore_result = detect_zscore(daily, threshold=ZSCORE_THRESHOLD)
    save_zscore(zscore_result, engine)

    # ── Isolation Forest 이상 탐지 ──────────────────
    logger.info("[3/3] Isolation Forest 이상 탐지")
    iforest_result = detect_isolation_forest(daily, contamination=ISOLATION_CONTAMINATION)
    save_iforest(iforest_result, engine)

    # Autoencoder (다음 단계)
    logger.info("[DETECTION] Autoencoder — 미구현 (다음 단계)")

    elapsed = time.time() - start
    logger.info(f"이상 탐지 완료 — 소요 시간: {elapsed:.1f}초")


if __name__ == "__main__":
    run()