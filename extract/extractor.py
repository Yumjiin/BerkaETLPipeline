import pandas as pd
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Berka CSV는 구분자 `;`, 인코딩 `latin-1` 고정
READ_OPTS = dict(sep=";", encoding="latin-1")

# 테이블별 필수 컬럼 스키마 정의
SCHEMAS: dict[str, list[str]] = {
    "account":  ["account_id", "district_id", "frequency", "date"],
    "card":     ["card_id", "disp_id", "type", "issued"],
    "client":   ["client_id", "birth_number", "district_id"],
    "disp":     ["disp_id", "client_id", "account_id", "type"],
    "district": ["A1", "A2", "A3"],
    "loan":     ["loan_id", "account_id", "date", "amount", "duration", "payments", "status"],
    "order":    ["order_id", "account_id", "bank_to", "account_to", "amount", "k_symbol"],
    "trans":    ["trans_id", "account_id", "date", "type", "operation", "amount", "balance"],
}


def load_csv(name: str, raw_dir: str | Path = "data/raw") -> pd.DataFrame:
    """
    CSV 파일 하나를 읽고 스키마 검증 후 DataFrame 반환.

    Args:
        name:    테이블 이름 (예: "trans")
        raw_dir: CSV 파일이 있는 폴더 경로

    Returns:
        검증 완료된 DataFrame
    """
    path = Path(raw_dir) / f"{name}.csv"

    if not path.exists():
        raise FileNotFoundError(f"CSV 파일을 찾을 수 없습니다: {path}")

    logger.info(f"[EXTRACT] {name} 로딩 시작 → {path}")
    df = pd.read_csv(path, **READ_OPTS)
    logger.info(f"[EXTRACT] {name} 로딩 완료 — {df.shape[0]:,}행 × {df.shape[1]}열")

    _validate_schema(name, df)
    _log_summary(name, df)

    return df


def load_all(raw_dir: str | Path = "data/raw") -> dict[str, pd.DataFrame]:
    """
    8개 테이블 전체를 읽어서 dict로 반환.

    Returns:
        {"account": df, "trans": df, ...}
    """
    tables: dict[str, pd.DataFrame] = {}
    for name in SCHEMAS:
        tables[name] = load_csv(name, raw_dir)
    logger.info(f"[EXTRACT] 전체 {len(tables)}개 테이블 로딩 완료")
    return tables


# ── 내부 함수 ──────────────────────────────────────────────────────────────

def _validate_schema(name: str, df: pd.DataFrame) -> None:
    """필수 컬럼이 모두 있는지 확인."""
    required = SCHEMAS.get(name, [])
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"[{name}] 필수 컬럼 누락: {missing}")
    logger.info(f"[EXTRACT] {name} 스키마 검증 통과")


def _log_summary(name: str, df: pd.DataFrame) -> None:
    """null 수, dtypes 간단 요약 출력."""
    null_counts = df.isnull().sum()
    null_cols = null_counts[null_counts > 0]
    if null_cols.empty:
        logger.info(f"[EXTRACT] {name} — 결측치 없음")
    else:
        logger.info(f"[EXTRACT] {name} — 결측치 있는 컬럼:\n{null_cols.to_string()}")