import logging
import time
import pandas as pd
from config import DATABASE_URL, ZSCORE_THRESHOLD
from load.loader import get_engine
from detection.zscore_detector import detect_zscore, save_anomalies

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
    daily = pd.read_sql("SELECT account_id, date, total_amount FROM daily_summary", engine)
    logger.info(f"[1/3] 로딩 완료 — {len(daily):,}행")
    logger.info(f"[LOAD] daily_summary columns: {list(daily.columns)}")
    try:
        logger.info(f"[LOAD] daily_summary sample: {daily.head(3).to_dict(orient='list')}")
    except Exception:
        logger.info("[LOAD] daily_summary sample: (failed to serialize)")

    # ── Z-Score 이상 탐지 ───────────────────────────
    logger.info("[2/3] Z-Score 이상 탐지 시작")
    zscore_result = detect_zscore(daily, threshold=ZSCORE_THRESHOLD)

    # ── anomaly_flags 저장 ──────────────────────────
    logger.info("[3/3] 결과 저장 시작")
    save_anomalies(zscore_result, engine)

    elapsed = time.time() - start
    logger.info(f"이상 탐지 완료 — 소요 시간: {elapsed:.1f}초")


if __name__ == "__main__":
    run()