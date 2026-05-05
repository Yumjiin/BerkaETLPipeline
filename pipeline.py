import logging
import time
from config import RAW_DATA_DIR
from extract.extractor import load_all

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

    # ── 2. Transform (Week 2에서 구현) ──────────────
    logger.info("[2/3] TRANSFORM 단계 — 미구현 (Week 2)")

    # ── 3. Load (Week 2에서 구현) ────────────────────
    logger.info("[3/3] LOAD 단계 — 미구현 (Week 2)")

    elapsed = time.time() - start
    logger.info(f"파이프라인 완료 — 소요 시간: {elapsed:.1f}초")


if __name__ == "__main__":
    run()