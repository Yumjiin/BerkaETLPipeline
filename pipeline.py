import logging
import time
from config import RAW_DATA_DIR, DATABASE_URL
from extract.extractor import load_all
from transform.cleaner import clean_all
from transform.aggregator import aggregate_all
from load.loader import load_all as load_to_db
from detection.zscore_detector import detect_zscore, save_anomalies

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def run():
    logger.info("=" * 50)
    logger.info("BerkaETLPipeline 시작")
    logger.info("=" * 50)

    start = time.time()

    # ── 1. Extract ──────────────────────────────────
    logger.info("[1/3] EXTRACT 단계 시작")
    tables = load_all(RAW_DATA_DIR)

    # ── 2. Transform ────────────────────────────────
    logger.info("[2/3] TRANSFORM 단계 시작")
    cleaned    = clean_all(tables)
    aggregated = aggregate_all(cleaned["trans"])
    logger.info(f"[TRANSFORM] daily_summary    — {len(aggregated['daily_summary']):,}행")
    logger.info(f"[TRANSFORM] category_summary — {len(aggregated['category_summary']):,}행")

    # ── 3. Load ─────────────────────────────────────
    logger.info("[3/3] LOAD 단계 시작")
    load_to_db(cleaned, aggregated, DATABASE_URL)

    # ── 4. Anomaly Detection ─────────────────────────
    logger.info("[4/4] 이상 탐지 단계 시작")
    engine = get_engine(DATABASE_URL)

    # Z-Score
    zscore_result = detect_zscore(aggregated["daily_summary"], threshold=ZSCORE_THRESHOLD)
    save_anomalies(zscore_result, engine)
 
    # Isolation Forest (다음 단계)
    logger.info("[DETECTION] Isolation Forest — 미구현 (다음 단계)")
 
    # Autoencoder (다음 단계)
    logger.info("[DETECTION] Autoencoder — 미구현 (다음 단계)")
    
    elapsed = time.time() - start
    logger.info(f"파이프라인 완료 — 소요 시간: {elapsed:.1f}초")


if __name__ == "__main__":
    run()