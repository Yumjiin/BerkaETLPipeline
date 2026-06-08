# BerkaAnalytics

> **ETL Pipeline + WPF Dashboard + Unsupervised Anomaly Detection**  
> Real Czech banking data (Berka Dataset) — End-to-end analytics pipeline

---

## 목차

1. [Overview](#overview)
2. [Repository Structure](#repository-structure)
3. [Dataset](#dataset)
4. [System Architecture](#system-architecture)
   - [Phase 1 - ETL Pipeline](#phase-1---etl-pipeline-python)
   - [Phase 2 - WPF Dashboard](#phase-2---wpf-dashboard-c)
   - [Phase 3 - Anomaly Detection](#phase-3---anomaly-detection-python)
5. [MySQL Schema](#mysql-schema)
6. [Anomaly Detection Evaluation](#anomaly-detection-evaluation)
7. [Tech Stack](#tech-stack)

---

## Overview

체코 금융기관의 실제 공개 데이터(Berka Dataset)를 기반으로 구축한 풀 파이프라인 분석 시스템입니다.

원본 CSV 파일을 MySQL로 정규화 재설계하고, Python ETL 파이프라인으로 적재한 뒤 WPF 4분할 대시보드로 시각화합니다. 레이블이 존재하지 않는 실제 거래 데이터에 대해 3가지 독립적인 모델(Z-Score · Isolation Forest · Autoencoder)로 이상거래를 탐지합니다.

```
CSV (8개 원본 파일)
    │
    ▼
Python ETL Pipeline   ── Extract / Transform / Load
    │
    ▼
MySQL Database        ── 정규화 스키마 + 집계 테이블 + 이상 탐지 결과 + 탐지 근거
    │
    ▼
WPF Dashboard (C#)   ── 4분할 패널 시각화 + 이상 탐지 결과 상세 화면
    ▲
    │
Python Anomaly Detection  ── Z-Score / Isolation Forest / Autoencoder
```

---

## Repository Structure

이 프로젝트는 두 개의 레포지토리로 구성됩니다.

|Repository|Language|Role|
|---|---|---|
|`BerkaETLPipeline`|Python|ETL 파이프라인 + 이상 탐지 모듈|
|`BerkaAnalyticsDashboard`|C# / WPF|분석 대시보드|

---

## Dataset

**Berka Dataset** - 1999년 공개된 체코 금융기관 실제 데이터 (UCI / Kaggle)

|항목|내용|
|---|---|
|기간|1993년 ~ 1998년 (5년)|
|규모|계좌 4,500개 / 거래 약 100만 건|
|구성|테이블 8개 (account, client, disposition, card, transaction, loan, order, district)|

### 고도화 내용

|원본 상태|이 프로젝트에서 적용한 것|
|---|---|
|CSV 8개 파일로 존재|MySQL 정규화 스키마로 재설계|
|컬럼명 체코어 혼재|영문 표준화 + 타입 정의|
|이상거래 레이블 없음|비지도 학습 3개 모델로 자동 탐지|
|단순 파일 조회만 가능|ETL 파이프라인 + 대시보드 시각화|

---

## System Architecture

### Phase 1 - ETL Pipeline (Python)

```
BerkaETLPipeline/
├── extract/
│   └── extractor.py         # CSV 읽기 + 스키마 검증
├── transform/
│   ├── cleaner.py           # 결측치 처리 + 타입 변환
│   ├── aggregator.py        # 일별/업종별 집계
│   └── feature_builder.py   # 계좌 프로파일 생성
├── load/
│   └── loader.py            # MySQL 적재 (SQLAlchemy)
├── detection/
│   ├── zscore_detector.py
│   ├── isolation_forest.py
│   ├── autoencoder.py
│   └── evaluator.py
├── models/
│   ├── autoencoder.pt       # 학습된 모델
│   └── autoencoder.onnx     # ONNX 변환 모델
├── pipeline.py              # ETL 파이프라인 진입점
├── detection_pipeline.py    # 이상 탐지 진입점
├── config.py                # 환경변수 로딩
├── .env.example
├── requirements.txt
└── README.md
```

**Transform 상세**

|항목|처리 방법|
|---|---|
|날짜 포맷|`YYMMDD` → `datetime` 변환|
|체코어 컬럼값|`PRIJEM` → `credit` / `VYDAJ` → `debit` 영문 매핑|
|결측치|거래유형 결측 → `unknown` 대체|
|음수 금액|절댓값 처리|

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

### Phase 2 - WPF Dashboard (C#)

```
BerkaAnalyticsDashboard/
├── YJI.Berka.Data/
│   ├── Connection/
│   ├── Entities/
│   ├── Repositories/
│   ├── DTOs/
│   └── Features/
├── YJI.Berka.Dashboard/
│   ├── Renderers/
│   ├── ViewModels/
│   ├── Views/
│   ├── App.xaml
│   └── appsettings.json
└── README.md
```

**4분할 패널 구성**

```
┌──────────────────────┬──────────────────────┐
│  Panel 1              │  Panel 2              │
│  일별 지출 추이        │  모델별 이상 탐지 비교 │
│  ScottPlot 라인       │  ScottPlot 가로 막대  │
│  이상 날짜 수직선      │  Z-Score/IForest/AE  │
├──────────────────────┼──────────────────────┤
│  Panel 3              │  Panel 4              │
│  업종별 지출 분포      │  월별 지출 비교        │
│  ScottPlot 가로 막대  │  ScottPlot 세로 막대  │
│  지출액 오름차순 정렬  │  전월 대비 증감 색상   │
└──────────────────────┴──────────────────────┘
```

**아키텍처 레이어**

|레이어|클래스|역할|
|---|---|---|
|Repository|`AccountRepository`|daily_summary / category_summary 조회|
|Repository|`AnomalyRepository`|anomaly_flags / high_confidence_anomalies 조회|
|Feature|`SpendingTrendFeature`|daily_summary → SpendingTrendDto 변환|
|Feature|`CategoryFeature`|category_summary → CategoryDto 변환|
|Feature|`MonthlySpendingFeature`|daily_summary → MonthlySpendingDto 변환|
|Feature|`AccountSummaryFeature`|account_profiles → AccountSummaryDto 변환|
|Renderer|`SpendingTrendRender`|ScottPlot 라인 차트|
|Renderer|`AnomalyComparisonRender`|ScottPlot 가로 막대 차트|
|Renderer|`CategoryRender`|ScottPlot 가로 막대 차트|
|Renderer|`MonthlySpendingRender`|ScottPlot 세로 막대 차트|
|ViewModel|`DashboardViewModel`|계좌 목록 / 선택 계좌 / 기간 필터 상태 관리|

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

### Phase 3 - Anomaly Detection (Python)

레이블이 없는 실제 환경을 가정하여 3가지 비지도 학습 모델을 독립적으로 적용합니다. 각 모델은 동일한 데이터에 대해 독립적으로 탐지하며, 2개 이상 공통 탐지된 건을 고신뢰 이상으로 분류합니다.

|모델|방법|특징|판단 근거 저장|
|---|---|---|---|
|Z-Score|단일 변수(금액) 통계적 극단치 탐지|계좌별 개별 기준선|mean, std, z_value|
|Isolation Forest|다변수 공간에서 고립도 기반 탐지|4개 피처 동시 고려|score, tx_count, avg_amount|
|Autoencoder|정상 패턴 학습 후 재구성 오차 탐지|비선형 패턴 학습|reconstruction_error, threshold|

**Z-Score**

```python
def detect_zscore(df: pd.DataFrame, threshold: float = 2.5) -> pd.DataFrame:
    df["mean"] = df.groupby("account_id")["total_amount"].transform("mean")
    df["std"]  = df.groupby("account_id")["total_amount"].transform("std").fillna(0)
    df["z_score"]    = (df["total_amount"] - df["mean"]) / df["std"].replace(0, 1)
    df["is_anomaly"] = df["z_score"].abs() > threshold
    df["method"]     = "zscore"
    return df
```

**Isolation Forest**

```python
from sklearn.ensemble import IsolationForest

def detect_isolation_forest(df: pd.DataFrame, contamination: float = 0.05) -> pd.DataFrame:
    features = df[['total_amount', 'tx_count', 'avg_amount', 'max_amount']]
    model    = IsolationForest(contamination=contamination, random_state=42)
    df["score"]      = model.fit_predict(features)
    df["is_anomaly"] = df["score"] == -1
    df["method"]     = "isolation_forest"
    return df
```

**Autoencoder**

```python
class SpendingAutoencoder(nn.Module):
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
```

---

## MySQL Schema

```sql
-- 정제된 거래 내역
CREATE TABLE raw_transactions (
    trans_id    INT PRIMARY KEY,
    account_id  INT NOT NULL,
    date        DATE NOT NULL,
    type        VARCHAR(20),
    amount      DECIMAL(12, 2),
    k_symbol    VARCHAR(30),
    INDEX idx_account_date (account_id, date)
);

-- 계좌별 일별 집계
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

-- 계좌별 업종별 집계
CREATE TABLE category_summary (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    account_id   INT NOT NULL,
    k_symbol     VARCHAR(30),
    total_amount DECIMAL(12, 2),
    tx_count     INT
);

-- 모델별 이상 탐지 결과
CREATE TABLE anomaly_flags (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    account_id   INT NOT NULL,
    date         DATE NOT NULL,
    method       VARCHAR(20),
    score        FLOAT,
    is_anomaly   TINYINT(1)
);

-- 2개 이상 모델 공통 탐지 (고신뢰)
CREATE TABLE high_confidence_anomalies (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    account_id   INT NOT NULL,
    date         DATE NOT NULL,
    detected_by  VARCHAR(100),
    model_count  INT
);

-- 계좌 종합 프로파일
CREATE TABLE account_profiles (
    account_id          INT PRIMARY KEY,
    total_amount        DECIMAL(12, 2),
    tx_count            INT,
    zscore_anomaly_count    INT,
    iforest_anomaly_count   INT,
    ae_anomaly_count        INT,
    high_confidence_count   INT
);

-- Z-Score 탐지 판단 근거
CREATE TABLE zscore_detail (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    account_id  INT NOT NULL,
    date        DATE NOT NULL,
    amount      DECIMAL(12, 2),
    mean        DECIMAL(12, 2),
    std         DECIMAL(12, 2),
    z_value     DECIMAL(8, 4),
    is_anomaly  TINYINT(1)
);

-- Isolation Forest 탐지 판단 근거
CREATE TABLE iforest_detail (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    account_id   INT NOT NULL,
    date         DATE NOT NULL,
    amount       DECIMAL(12, 2),
    tx_count     INT,
    avg_amount   DECIMAL(12, 2),
    max_amount   DECIMAL(12, 2),
    score        DECIMAL(8, 4),
    is_anomaly   TINYINT(1)
);

-- Autoencoder 탐지 판단 근거
CREATE TABLE autoencoder_detail (
    id                   INT AUTO_INCREMENT PRIMARY KEY,
    account_id           INT NOT NULL,
    date                 DATE NOT NULL,
    amount               DECIMAL(12, 2),
    reconstruction_error DECIMAL(10, 6),
    threshold            DECIMAL(10, 6),
    is_anomaly           TINYINT(1)
);
```

**인덱스 설계**

|테이블|인덱스|이유|
|---|---|---|
|`raw_transactions`|`(account_id, date)`|계좌별 기간 조회가 가장 빈번|
|`daily_summary`|`UNIQUE (account_id, date)`|중복 적재 방지 + 조회 성능|
|`anomaly_flags`|`(account_id, date)`|이상 탐지 결과 조회용|

---

## Anomaly Detection Evaluation

레이블이 없는 비지도 학습 환경에서는 Accuracy / F1-Score 같은 지도학습 지표를 사용할 수 없습니다. 아래 방법으로 평가합니다.

### 1. Precision@K

각 모델의 이상 점수 상위 K건(K=50)을 직접 검토하여 실제 이상 여부를 판단합니다.

### 2. 모델 간 탐지 결과 겹침 분석

```python
z_flags  = set(zscore_anomalies['account_id'])
if_flags = set(iforest_anomalies['account_id'])
ae_flags = set(autoencoder_anomalies['account_id'])

# 2개 이상 모델이 공통으로 탐지 = 고신뢰 이상
high_confidence = (z_flags & if_flags) | (z_flags & ae_flags) | (if_flags & ae_flags)
```

### 탐지 결과 요약

|모델|탐지 건수|탐지율|
|---|---|---|
|Z-Score|13,795건|2.31%|
|Isolation Forest|29,852건|5.00%|
|Autoencoder|29,829건|5.00%|
|고신뢰 (2개+ 공통)|13,288건|2.23%|
|3개 모델 공통|3,571건|0.60%|

---

## Tech Stack

| 분류            | 기술                                                     |
| ------------- | ------------------------------------------------------ |
| ETL / ML      | Python 3.11, pandas, scikit-learn, PyTorch, SQLAlchemy |
| Database      | MySQL 8.0                                              |
| Dashboard     | C#, WPF, .NET 10                                       |
| Visualization | ScottPlot 5                                            |
| ORM (C#)      | Dapper                                                 |
| Container     | Docker, docker-compose                                 |
