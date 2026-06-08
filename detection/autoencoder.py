import pandas as pd
import numpy as np
import logging
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sqlalchemy.engine import Engine
from sqlalchemy import text
from pathlib import Path

logger = logging.getLogger(__name__)

MODEL_PATH = Path("models/autoencoder.pt")


# ── 모델 정의 ────────────────────────────────────────────
class SpendingAutoencoder(nn.Module):
    """
    지출 패턴 Autoencoder.

    입력 → 압축(Encoder) → 복원(Decoder) → 재구성 오차 계산
    정상 데이터로 학습 후, 오차가 크면 이상으로 판단.
    """
    def __init__(self, input_dim: int = 4):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, 16), nn.ReLU(),
            nn.Linear(16, 8),         nn.ReLU(),
        )
        self.decoder = nn.Sequential(
            nn.Linear(8, 16),         nn.ReLU(),
            nn.Linear(16, input_dim),
        )

    def forward(self, x):
        return self.decoder(self.encoder(x))


# ── 탐지 함수 ────────────────────────────────────────────
def detect_autoencoder(
    daily: pd.DataFrame,
    epochs: int = 30,
    batch_size: int = 256,
    threshold_percentile: float = 95.0,
    force_retrain: bool = False,
) -> pd.DataFrame:
    """
    Autoencoder 기반 이상 탐지.

    저장된 모델이 있으면 불러오고, 없으면 새로 학습 후 저장.

    Args:
        daily:                daily_summary DataFrame
        epochs:               학습 반복 횟수
        batch_size:           배치 크기
        threshold_percentile: 이상 판단 임계값 백분위수 (기본 상위 5%)
        force_retrain:        True면 저장된 모델 무시하고 재학습
    """
    logger.info(f"[AE] Autoencoder 이상 탐지 시작 — epochs: {epochs}")

    df = daily.copy()
    features = ["total_amount", "tx_count", "avg_amount", "max_amount"]
    df[features] = df[features].fillna(0)

    # 1. 정규화
    scaler = StandardScaler()
    X = scaler.fit_transform(df[features].values).astype(np.float32)
    tensor_X = torch.tensor(X)

    # 2. 모델 준비 (저장된 모델 있으면 불러오기)
    model = SpendingAutoencoder(input_dim=len(features))

    if MODEL_PATH.exists() and not force_retrain:
        logger.info(f"[AE] 저장된 모델 불러오기 → {MODEL_PATH}")
        model.load_state_dict(torch.load(MODEL_PATH, weights_only=True))
    else:
        # 3. 새로 학습
        logger.info("[AE] 모델 학습 시작")
        dataset   = TensorDataset(tensor_X)
        loader    = DataLoader(dataset, batch_size=batch_size, shuffle=True)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
        criterion = nn.MSELoss()

        model.train()
        for epoch in range(epochs):
            total_loss = 0.0
            for (batch,) in loader:
                optimizer.zero_grad()
                output = model(batch)
                loss   = criterion(output, batch)
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

            if (epoch + 1) % 10 == 0:
                avg_loss = total_loss / len(loader)
                logger.info(f"[AE] Epoch {epoch+1}/{epochs} — loss: {avg_loss:.6f}")

        # 4. 모델 저장
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), MODEL_PATH)
        logger.info(f"[AE] 모델 저장 완료 → {MODEL_PATH}")

    # 5. 재구성 오차 계산
    model.eval()
    with torch.no_grad():
        reconstructed = model(tensor_X).numpy()

    errors = np.mean((X - reconstructed) ** 2, axis=1)

    # 6. 임계값 설정 (상위 5% = 이상)
    threshold = np.percentile(errors, threshold_percentile)
    logger.info(f"[AE] 재구성 오차 임계값: {threshold:.6f} (상위 {100-threshold_percentile:.0f}%)")

    df["score"]      = errors
    df["is_anomaly"] = errors > threshold
    df["method"]     = "autoencoder"

    anomaly_count = df["is_anomaly"].sum()
    total_count   = len(df)
    logger.info(f"[AE] 탐지 완료 — 전체 {total_count:,}건 중 이상 {anomaly_count:,}건 ({anomaly_count/total_count*100:.2f}%)")

    df["threshold"] = float(threshold)
    return df[["account_id", "date", "total_amount", "score", "is_anomaly", "method", "threshold"]]


# ── 저장 함수 ────────────────────────────────────────────
def save_anomalies(result: pd.DataFrame, engine: Engine, threshold: float = None) -> None:
    """
    탐지 결과를 MySQL anomaly_flags 테이블에 저장.
    autoencoder_detail 테이블에 판단 근거 저장.
    """
    # ── anomaly_flags 저장 (기존과 동일) ──
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM anomaly_flags WHERE method = 'autoencoder'"))
    logger.info("[AE] 기존 결과 삭제 완료")

    to_save = result[["account_id", "date", "method", "score", "is_anomaly"]].copy()
    to_save["is_anomaly"] = to_save["is_anomaly"].astype(int)

    to_save.to_sql(
        name="anomaly_flags",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=5000,
    )
    logger.info(f"[AE] anomaly_flags 저장 완료 — {len(to_save):,}건")

    # ── autoencoder_detail 저장 (판단 근거) ──
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS autoencoder_detail (
                id                   INT AUTO_INCREMENT PRIMARY KEY,
                account_id           INT NOT NULL,
                date                 DATE NOT NULL,
                amount               DECIMAL(12,2),
                reconstruction_error DECIMAL(10,6),
                threshold            DECIMAL(10,6),
                is_anomaly           TINYINT(1)
            )
        """))
        conn.execute(text("DELETE FROM autoencoder_detail"))

    detail = result.copy()
    detail["is_anomaly"]           = detail["is_anomaly"].astype(int)
    detail["amount"]               = detail["total_amount"]
    detail["reconstruction_error"] = detail["score"].round(6)

    # threshold가 전달되지 않으면 score 95 percentile로 계산
    if threshold is None:
        threshold = float(result["score"].quantile(0.95))
    detail["threshold"] = result["threshold"].round(6)

    detail[["account_id", "date", "amount",
            "reconstruction_error", "threshold", "is_anomaly"]].to_sql(
        name="autoencoder_detail",
        con=engine,
        if_exists="append",
        index=False,
        chunksize=5000,
    )
    logger.info(f"[AE] autoencoder_detail 저장 완료 — {len(detail):,}건")