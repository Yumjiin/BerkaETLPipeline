import logging
import time
import pandas as pd
from config import DATABASE_URL, ZSCORE_THRESHOLD, ISOLATION_CONTAMINATION
from load.loader import get_engine
from detection.zscore_detector import detect_zscore, save_anomalies as save_zscore
from detection.isolation_forest import detect_isolation_forest, save_anomalies as save_iforest
from detection.autoencoder import detect_autoencoder, save_anomalies as save_autoencoder
from detection.evaluator import evaluate, save_high_confidence, precision_at_k
from transform.feature_builder import build_account_profile, save_account_profile

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
    logger.info("[1/6] MySQL에서 daily_summary 로딩")
    daily = pd.read_sql(
        "SELECT account_id, date, total_amount, tx_count, avg_amount, max_amount FROM daily_summary",
        engine
    )
    logger.info(f"[1/6] 로딩 완료 — {len(daily):,}행")

    # ── Z-Score ─────────────────────────────────────
    logger.info("[2/6] Z-Score 이상 탐지")
    zscore_result = detect_zscore(daily, threshold=ZSCORE_THRESHOLD)
    save_zscore(zscore_result, engine)

    # ── Isolation Forest ─────────────────────────────
    logger.info("[3/6] Isolation Forest 이상 탐지")
    iforest_result = detect_isolation_forest(daily, contamination=ISOLATION_CONTAMINATION)
    save_iforest(iforest_result, engine)

    # ── Autoencoder ──────────────────────────────────
    logger.info("[4/6] Autoencoder 이상 탐지")
    ae_result = detect_autoencoder(daily)
    save_autoencoder(ae_result, engine)

    # ── 평가 ────────────────────────────────────────
    logger.info("[5/6] 모델 간 결과 비교 및 평가")
    high_confidence = evaluate(engine)
    save_high_confidence(high_confidence, engine)
    precision_at_k(engine, k=50)

    # ── 계좌 프로파일 ────────────────────────────────
    logger.info("[6/6] 계좌 프로파일 생성")
    profile = build_account_profile(engine)
    save_account_profile(profile, engine)

    elapsed = time.time() - start
    logger.info(f"이상 탐지 완료 — 소요 시간: {elapsed:.1f}초")


if __name__ == "__main__":
    run()