# BerkaAnalytics

> **ETL Pipeline + WPF Dashboard + Unsupervised Anomaly Detection**  
> Real Czech banking data (Berka Dataset) — End-to-end analytics pipeline

---

## Overview

체코 금융기관의 실제 공개 데이터(Berka Dataset)를 기반으로 구축한 풀 파이프라인 분석 시스템입니다.

원본 CSV 파일을 MySQL로 정규화 재설계하고, Python ETL 파이프라인으로 적재한 뒤 WPF 4분할 대시보드로 시각화합니다. 레이블이 존재하지 않는 실제 거래 데이터에 대해 Z-Score → Isolation Forest → Autoencoder 3단계 비지도 학습 파이프라인으로 이상거래를 탐지합니다.

```
CSV (8개 원본 파일)
    │
    ▼
Python ETL Pipeline   ── Extract / Transform / Load
    │
    ▼
MySQL Database        ── 정규화 스키마 + 집계 테이블 + 이상 탐지 결과
    │
    ▼
WPF Dashboard (C#)   ── 4분할 패널 시각화 + 이상 구간 오버레이
    ▲
    │
Python Anomaly Detection  ── Z-Score / Isolation Forest / Autoencoder
```

---

## Repository Structure

이 프로젝트는 두 개의 레포지토리로 구성됩니다.

| Repository | Language | Role |
|---|---|---|
| `BerkaETLPipeline` | Python | ETL 파이프라인 + 이상 탐지 모듈 |
| `BerkaAnalyticsDashboard` | C# / WPF | 분석 대시보드 |

---

## Dataset

**Berka Dataset** — 1999년 공개된 체코 금융기관 실제 데이터 (UCI / Kaggle)

| 항목 | 내용 |
|---|---|
| 기간 | 1993년 ~ 1998년 (5년) |
| 규모 | 계좌 4,500개 / 거래 약 100만 건 |
| 구성 | 테이블 8개 (account, client, disposition, card, transaction, loan, order, district) |

### 고도화 내용

| 원본 상태 | 이 프로젝트에서 적용한 것 |
|---|---|
| CSV 8개 파일로 존재 | MySQL 정규화 스키마로 재설계 |
| 컬럼명 체코어 혼재 | 영문 표준화 + 타입 정의 |
| 이상거래 레이블 없음 | 비지도 학습 3단계로 자동 탐지 |
| 단순 파일 조회만 가능 | ETL 파이프라인 + 대시보드 시각화 |

---

## System Architecture

### Phase 1 — ETL Pipeline (Python)

```
BerkaETLPipeline/
├── extract/
│   └── extractor.py         # CSV 읽기 + 스키마 검증
├── transform/
│   ├── cleaner.py           # 결측치 처리 + 타입 변환
│   ├── aggregator.py        # 일별/월별/업종별 집계
│   └── feature_builder.py   # 계좌 프로파일 생성
├── load/
│   └── loader.py            # MySQL 적재 (SQLAlchemy)
├── detection/
│   ├── zscore_detector.py
│   ├── isolation_forest.py
│   ├── autoencoder.py
│   └── evaluator.py
├── pipeline.py              # 전체 파이프라인 진입점
├── config.py                # 환경변수 로딩
├── .env.example
├── requirements.txt
└── README.md
```

**Transform 상세**

| 항목 | 처리 방법 |
|---|---|
| 날짜 포맷 | `YYMMDD` → `datetime` 변환 |
| 체코어 컬럼값 | `PRIJEM` → `credit` / `VYDAJ` → `debit` 영문 매핑 |
| 결측치 | 거래유형 결측 → `unknown` 대체 |
| 음수 금액 | 절댓값 처리 |

```python
# 일별 집계 (daily_summary)
daily = transactions.groupby(['account_id', 'date']).agg(
    total_amount = ('amount', 'sum'),
    tx_count     = ('trans_id', 'count'),
    avg_amount   = ('amount', 'mean'),
    max_amount   = ('amount', 'max')
).reset_index()

# 업종별 집계 (category_summary)
category = transactions.groupby(['account_id', 'k_symbol']).agg(
    total_amount = ('amount', 'sum'),
    tx_count     = ('trans_id', 'count')
).reset_index()
```

---

### Phase 2 — WPF Dashboard (C#)

```
BerkaAnalyticsDashboard/
├── Models/
├── Features/
├── Renderers/
├── Services/
├── ViewModels/
├── Views/
├── Repositories/
├── App.xaml
├── MainWindow.xaml
└── README.md
```

**4분할 패널 구성**

```
┌──────────────────────┬──────────────────────┐
│  Panel 1              │  Panel 2              │
│  일별 지출 추이        │  시간×요일 히트맵      │
│  ScottPlot Line       │  SkiaSharp Heatmap    │
│  이상 구간 오버레이    │  결제 집중 시간대      │
├──────────────────────┼──────────────────────┤
│  Panel 3              │  Panel 4              │
│  업종별 지출 분포      │  월별 지출 비교        │
│  ScottPlot Bar        │  ScottPlot Bar        │
│  이상 업종 강조 표시   │  전월 대비 증감        │
└──────────────────────┴──────────────────────┘
```

**아키텍처 레이어**

| 레이어 | 클래스 | 역할 |
|---|---|---|
| Feature | `SpendingTrendFeature` | MySQL `daily_summary` 조회 → 모델 변환 |
| Feature | `CategoryFeature` | MySQL `category_summary` 조회 |
| Feature | `AmountDistFeature` | 금액 분포 집계 |
| Feature | `BehaviorHeatmapFeature` | 시간×요일 행렬 |
| Renderer | `SpendingTrendRender` | ScottPlot 라인 차트 |
| Renderer | `CategoryRender` | ScottPlot 막대 차트 |
| Renderer | `AmountDistRender` | ScottPlot 히스토그램 |
| Renderer | `BehaviorHeatmapRender` | SkiaSharp 히트맵 |
| Service | `CursorSyncService` | 패널 간 커서 동기화 |
| Repository | `AnomalyRepository` | 이상 구간 조회 + 오버레이 |

**DB 연동 예시**

```csharp
var data = await connection.QueryAsync<DailySummary>(@"
    SELECT date, total_amount, tx_count
    FROM   daily_summary
    WHERE  account_id = @accountId
    AND    date BETWEEN @start AND @end
    ORDER  BY date",
    new { accountId, start, end }
);
```

---

### Phase 3 — Anomaly Detection (Python)

레이블이 없는 실제 환경을 가정하여 비지도 학습 방법 3가지를 단계적으로 적용합니다.

| 단계 | 방법 | 특징 |
|---|---|---|
| 1 | Z-Score | 단일 변수(금액) 기반 통계적 극단치 탐지 |
| 2 | Isolation Forest | 다변수 공간에서 고립도 기반 탐지 |
| 3 | Autoencoder | 정상 패턴 학습 후 재구성 오차 기반 탐지 |

**Z-Score**

```python
def detect_zscore(df: pd.DataFrame, threshold: float = 2.5) -> pd.DataFrame:
    mean = df['total_amount'].mean()
    std  = df['total_amount'].std()
    df['z_score']    = (df['total_amount'] - mean) / std
    df['is_anomaly'] = df['z_score'].abs() > threshold
    df['method']     = 'zscore'
    return df
```

**Isolation Forest**

```python
from sklearn.ensemble import IsolationForest

def detect_isolation_forest(df: pd.DataFrame, contamination: float = 0.05) -> pd.DataFrame:
    features = df[['total_amount', 'tx_count', 'max_amount', 'avg_amount']]
    model    = IsolationForest(contamination=contamination, random_state=42)
    df['anomaly_score'] = model.fit_predict(features)
    df['is_anomaly']    = df['anomaly_score'] == -1
    df['method']        = 'isolation_forest'
    return df
```

**Autoencoder**

```python
class SpendingAutoencoder(nn.Module):
    def __init__(self, input_dim: int = 30):
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
```

---

## MySQL Schema

```sql
CREATE TABLE raw_transactions (
    trans_id    INT PRIMARY KEY,
    account_id  INT NOT NULL,
    date        DATE NOT NULL,
    type        VARCHAR(10),
    amount      DECIMAL(12, 2),
    k_symbol    VARCHAR(20),
    INDEX idx_account_date (account_id, date)
);

CREATE TABLE daily_summary (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    account_id   INT NOT NULL,
    date         DATE NOT NULL,
    total_amount DECIMAL(12, 2),
    tx_count     INT,
    avg_amount   DECIMAL(12, 2),
    max_amount   DECIMAL(12, 2),
    UNIQUE KEY uq_account_date (account_id, date)
);

CREATE TABLE category_summary (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    account_id   INT NOT NULL,
    k_symbol     VARCHAR(20),
    total_amount DECIMAL(12, 2),
    tx_count     INT
);

CREATE TABLE anomaly_flags (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    account_id   INT NOT NULL,
    date         DATE NOT NULL,
    method       VARCHAR(20),
    score        FLOAT,
    is_anomaly   TINYINT(1),
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

**인덱스 설계**

| 테이블 | 인덱스 | 이유 |
|---|---|---|
| `raw_transactions` | `(account_id, date)` | 계좌별 기간 조회가 가장 빈번 |
| `daily_summary` | `UNIQUE (account_id, date)` | 중복 적재 방지 + 조회 성능 |
| `anomaly_flags` | `(account_id, date)` | 대시보드 오버레이 조회용 |

---

## Anomaly Detection Evaluation

레이블이 없는 비지도 학습 환경에서는 Accuracy / F1-Score 같은 지도학습 지표를 사용할 수 없습니다. 아래 3가지 방법으로 평가합니다.

### 1. Precision@K

각 모델의 이상 점수 상위 K건(K=50, 100)을 직접 검토하여 실제 이상 여부를 판단하고 비율을 계산합니다.

### 2. 재구성 오차 분포 시각화 (Autoencoder)

```python
plt.hist(normal_errors,  bins=50, alpha=0.6, label='Normal')
plt.hist(anomaly_errors, bins=50, alpha=0.6, label='Anomaly')
plt.xlabel('Reconstruction Error (MSE)')
plt.title('Normal vs Anomaly Error Distribution')
```

두 분포가 명확히 분리되면 모델이 정상/이상 패턴을 구별하고 있다는 근거가 됩니다.

### 3. 모델 간 탐지 결과 겹침 분석

```python
z_flags  = set(zscore_anomalies['trans_id'])
if_flags = set(iforest_anomalies['trans_id'])
ae_flags = set(autoencoder_anomalies['trans_id'])

# 2개 이상 모델이 공통으로 탐지한 거래 = 고신뢰 이상
high_confidence = (z_flags & if_flags) | (z_flags & ae_flags) | (if_flags & ae_flags)
```

---

## Development Roadmap

| 주차 | 내용 | 산출물 |
|---|---|---|
| Week 1 | Berka 데이터 탐색 + MySQL 스키마 설계 | ERD + DDL SQL |
| Week 2 | ETL Extract + Load 구현 | `extractor.py` / `loader.py` |
| Week 3 | ETL Transform 구현 | `cleaner.py` / `aggregator.py` |
| Week 4 | WPF 뼈대 + MySQL 연동 | DB 연결 + AccountLoader |
| Week 5 | Feature 레이어 4개 구현 | `*Feature.cs` |
| Week 6 | Renderer 레이어 4개 구현 | `*Render.cs` / 4분할 패널 |
| Week 7 | MVVM + 서비스 + 필터 | `DashboardViewModel` |
| Week 8 | 이상 탐지 모듈 3단계 | anomaly_flags 적재 + 오버레이 |
| Week 9 | 문서화 + 데모 | README / 데모 GIF |

---

## Getting Started

### Prerequisites

- Python 3.10+
- .NET 8.0
- MySQL 8.0+

### Environment Setup

`.env` 파일을 생성하여 DB 자격증명을 설정합니다. (`.env.example` 참고)

```bash
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=berka
```

> `.env` 파일은 `.gitignore`에 포함되어 있으며 절대 커밋하지 않습니다.

### Run ETL Pipeline

```bash
cd BerkaETLPipeline
pip install -r requirements.txt
python pipeline.py
```

### Run Anomaly Detection

```bash
python -m detection.zscore_detector
python -m detection.isolation_forest
python -m detection.autoencoder
```

### Run Dashboard

```bash
cd BerkaAnalyticsDashboard
dotnet run
```

---

## Tech Stack

| 분류 | 기술 |
|---|---|
| ETL / ML | Python, pandas, scikit-learn, PyTorch, SQLAlchemy |
| Database | MySQL 8.0 |
| Dashboard | C#, WPF, .NET 8 |
| Visualization | ScottPlot, SkiaSharp |
| ORM (C#) | Dapper |

---

## License

MIT
