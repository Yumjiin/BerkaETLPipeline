import pandas as pd
import logging

logger = logging.getLogger(__name__)


def aggregate_daily(trans: pd.DataFrame) -> pd.DataFrame:
    """
    일별 집계 → daily_summary 테이블.

    account_id + date 기준으로 집계:
    - total_amount : 하루 총 지출액
    - tx_count     : 거래 건수
    - avg_amount   : 평균 거래액
    - max_amount   : 최대 거래액
    """
    logger.info("[AGG] daily_summary 집계 시작")

    daily = (
        trans[trans["type"] == "debit"]          # 지출 거래만
        .groupby(["account_id", "date"])
        .agg(
            total_amount=("amount", "sum"),
            tx_count    =("trans_id", "count"),
            avg_amount  =("amount", "mean"),
            max_amount  =("amount", "max"),
        )
        .reset_index()
    )

    logger.info(f"[AGG] daily_summary 완료 — {len(daily):,}행")
    return daily


def aggregate_category(trans: pd.DataFrame) -> pd.DataFrame:
    """
    업종별 집계 → category_summary 테이블.

    account_id + k_symbol 기준으로 집계:
    - total_amount : 업종별 총 지출액
    - tx_count     : 업종별 거래 건수
    """
    logger.info("[AGG] category_summary 집계 시작")

    category = (
        trans[trans["type"] == "debit"]
        .groupby(["account_id", "k_symbol"])
        .agg(
            total_amount=("amount", "sum"),
            tx_count    =("trans_id", "count"),
        )
        .reset_index()
    )

    logger.info(f"[AGG] category_summary 완료 — {len(category):,}행")
    return category


def aggregate_all(trans: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """
    전체 집계 실행.
    pipeline.py 에서 호출하는 메인 함수.

    Returns:
        {"daily_summary": df, "category_summary": df}
    """
    return {
        "daily_summary":    aggregate_daily(trans),
        "category_summary": aggregate_category(trans),
    }