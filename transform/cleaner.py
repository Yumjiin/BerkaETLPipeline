import pandas as pd
import logging

logger = logging.getLogger(__name__)

# 체코어 → 영어 매핑
TYPE_MAP = {"PRIJEM": "credit", "VYDAJ": "debit"}
OPERATION_MAP = {
    "VYBER KARTOU":      "card_withdrawal",
    "VKLAD":             "deposit",
    "PREVOD Z UCTU":     "transfer_in",
    "VYBER":             "withdrawal",
    "PREVOD NA UCET":    "transfer_out",
}
KSYMBOL_MAP = {
    "POJISTNE":    "insurance",
    "SLUZBY":      "services",
    "UROK":        "interest",
    "SANKC. UROK": "penalty_interest",
    "SIPO":        "household",
    "DUCHOD":      "pension",
    "UVER":        "loan_payment",
    "":            "unknown",
}


def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """
    trans 테이블 정제.
    - 날짜 변환 / 체코어 영문화 / 결측치 처리 / 음수 금액 처리
    """
    logger.info("[CLEAN] transactions 정제 시작")
    df = df.copy()

    # 1. 날짜 변환 (YYYYMMDD 정수 → datetime)
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%y%m%d", errors="coerce")

    # 2. 체코어 → 영어 매핑
    df["type"]      = df["type"].map(TYPE_MAP).fillna("unknown")
    df["operation"] = df["operation"].map(OPERATION_MAP).fillna("unknown")
    df["k_symbol"]  = df["k_symbol"].astype(str).str.strip().map(KSYMBOL_MAP).fillna("unknown")

    # 3. 결측치 처리
    df["amount"]  = df["amount"].fillna(0)
    df["balance"] = df["balance"].fillna(0)

    # 4. 음수 금액 → 절댓값
    df["amount"]  = df["amount"].abs()
    df["balance"] = df["balance"].abs()

    # 5. 타입 통일 (DtypeWarning 해결)
    df["amount"]  = df["amount"].astype(float)
    df["balance"] = df["balance"].astype(float)

    logger.info(f"[CLEAN] transactions 정제 완료 — {len(df):,}행")
    return df


def clean_accounts(df: pd.DataFrame) -> pd.DataFrame:
    """account 테이블 정제."""
    logger.info("[CLEAN] accounts 정제 시작")
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"].astype(str), format="%y%m%d", errors="coerce")
    logger.info(f"[CLEAN] accounts 정제 완료 — {len(df):,}행")
    return df


def clean_loans(df: pd.DataFrame) -> pd.DataFrame:
    """loan 테이블 정제."""
    logger.info("[CLEAN] loans 정제 시작")
    df = df.copy()
    df["date"]     = pd.to_datetime(df["date"].astype(str), format="%y%m%d", errors="coerce")
    df["payments"] = df["payments"].fillna(0)
    logger.info(f"[CLEAN] loans 정제 완료 — {len(df):,}행")
    return df


def clean_cards(df: pd.DataFrame) -> pd.DataFrame:
    """card 테이블 정제."""
    logger.info("[CLEAN] cards 정제 시작")
    df = df.copy()
    df["issued"] = pd.to_datetime(df["issued"].astype(str), format="%y%m%d", errors="coerce")
    logger.info(f"[CLEAN] cards 정제 완료 — {len(df):,}행")
    return df


def clean_all(tables: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """
    전체 테이블 정제.
    pipeline.py 에서 호출하는 메인 함수.
    """
    cleaned = tables.copy()
    cleaned["trans"]   = clean_transactions(tables["trans"])
    cleaned["account"] = clean_accounts(tables["account"])
    cleaned["loan"]    = clean_loans(tables["loan"])
    cleaned["card"]    = clean_cards(tables["card"])
    # client / disp / district / order 는 정제 불필요
    logger.info("[CLEAN] 전체 정제 완료")
    return cleaned