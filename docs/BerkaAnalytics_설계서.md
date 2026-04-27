# BerkaAnalytics — 프로젝트 설계서

> v1.1 | ETL 파이프라인 + WPF 대시보드 + 비지도 이상 탐지

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [Berka Dataset](#2-berka-dataset)
3. [전체 시스템 아키텍처](#3-전체-시스템-아키텍처)
4. [Phase 1 — ETL 파이프라인](#4-phase-1--etl-파이프라인)
5. [Phase 2 — WPF 분석 대시보드](#5-phase-2--wpf-분석-대시보드)
6. [Phase 3 — 이상 탐지 모듈](#6-phase-3--이상-탐지-모듈)
7. [MySQL 스키마 설계](#7-mysql-스키마-설계)
8. [이상 탐지 성능 평가 방법론](#8-이상-탐지-성능-평가-방법론)
9. [EventViewer와의 연속성](#9-eventviewer와의-연속성)
10. [개발 일정](#10-개발-일정-9주)
11. [레포지토리 구조](#11-레포지토리-구조)

---

## 1. 프로젝트 개요

### 1.1 한 줄 정의

```
실제 체코 은행 공개 데이터(Berka Dataset)를 MySQL로 재설계하고,
pandas ETL 파이프라인으로 적재한 뒤 WPF 4분할 대시보드로 시각화.
원본에 없던 이상거래 탐지 기능을 Z-Score → Isolation Forest → Autoencoder
3단계 비지도 학습 파이프라인으로 고도화한 풀 파이프라인 프로젝트.
```

### 1.2 포지셔닝

| 구분 | 내용 |
|------|------|
| **타겟 직무** | 은행권 데이터 엔지니어 / 분석 시스템 개발자 |
| **핵심 강점** | 파이프라인 설계 + 시각화 시스템 구현 |
| **인턴 연속성** | EventViewer 5계층 아키텍처 → DB 연동 버전으로 심화 |
| **고도화 근거** | 원본 CSV → MySQL 정규화 재설계 + 이상 탐지 모듈 추가 |

### 1.3 레포지토리 구성

```
BerkaAnalyticsDashboard  (C#/WPF)  — 분석 대시보드
BerkaETLPipeline         (Python)  — ETL + 이상 탐지
```

---

## 2. Berka Dataset

### 2.1 데이터셋 소개

- **출처**: 1999년 체코 금융기관 실제 데이터 (UCI / Kaggle 공개)
- **기간**: 1993년 ~ 1998년 (5년치)
- **규모**: 계좌 4,500개 / 거래 약 1,000,000건
- **특징**: 실제 은행 DB 구조 그대로 — 테이블 8개로 구성

### 2.2 원본 테이블 구조

```
account.csv       계좌 정보      (account_id, district_id, date, frequency)
client.csv        고객 정보      (client_id, birth_number, district_id)
disposition.csv   계좌-고객 관계  (disp_id, client_id, account_id, type)
card.csv          카드 정보      (card_id, disp_id, type, issued)
transaction.csv   거래 내역      (trans_id, account_id, date, type, amount ...)
loan.csv          대출 정보      (loan_id, account_id, date, amount, status)
order.csv         자동이체 정보   (order_id, account_id, amount, k_symbol)
district.csv      지역 정보      (district_id, name, region, population ...)
```

### 2.3 고도화 포인트

| 원본 상태 | 이 프로젝트에서 한 것 |
|----------|-------------------|
| CSV 8개 파일로 존재 | MySQL 정규화 스키마로 재설계 |
| 컬럼명 체코어 혼재 | 영문 표준화 + 타입 정의 |
| 이상거래 레이블 없음 | Z-Score 기반 자동 탐지 후 레이블 생성 |
| 단순 파일 조회만 가능 | ETL 파이프라인 + 대시보드 시각화 |

---

## 3. 전체 시스템 아키텍처

### 3.1 데이터 흐름

```
[원천 데이터]
 Berka Dataset CSV 8개
        │
        ▼
[Phase 1: ETL 파이프라인 — Python]
 ┌─────────────────────────────────┐
 │  Extract   CSV → pandas         │
 │  Transform 전처리 + 집계         │
 │  Load      → MySQL 적재         │
 └─────────────────────────────────┘
        │
        ▼
[MySQL DB]
 ┌─────────────────────────────────┐
 │  raw_transactions               │
 │  daily_summary                  │
 │  category_summary               │
 │  account_profile                │
 │  anomaly_flags     ◀────────────┼── Phase 3 결과 적재
 └─────────────────────────────────┘
        │
        ▼
[Phase 2: WPF 대시보드 — C#]
 ┌─────────────────────────────────┐
 │  Feature 레이어  DB 쿼리 → 모델  │
 │  Render 레이어   ScottPlot/Skia  │
 │  4분할 패널 시각화               │
 │  이상 구간 오버레이 표시          │
 └─────────────────────────────────┘
        │
        ▼
[Phase 3: 이상 탐지 — Python]
 ┌─────────────────────────────────┐
 │  Z-Score         통계 기반 탐지  │
 │  Isolation Forest ML 기반 탐지  │
 │  Autoencoder     딥러닝 기반 탐지│
 └─────────────────────────────────┘
```

---

## 4. Phase 1 — ETL 파이프라인

### 4.1 파이프라인 구조

```
BerkaETLPipeline/
├── extract/
│   └── extractor.py        CSV 읽기 + 스키마 검증
├── transform/
│   ├── cleaner.py          결측치 처리 + 타입 변환
│   ├── aggregator.py       일별/월별/업종별 집계
│   └── feature_builder.py  계좌 프로파일 생성
├── load/
│   └── loader.py           MySQL 적재 (SQLAlchemy)
├── pipeline.py             전체 파이프라인 실행 진입점
├── config.py               .env 로딩 (DB 자격증명 직접 기재 금지)
├── .env.example            환경변수 템플릿 (GitHub 공개용)
├── .env                    실제 자격증명 (gitignore 처리)
└── .gitignore
```

### 4.2 Transform 단계 상세

**cleaner.py — 전처리 항목**

| 항목 | 처리 방법 |
|------|----------|
| 날짜 포맷 통일 | `YYMMDD` → `datetime` 변환 |
| 체코어 컬럼값 | `PRIJEM`→`credit`, `VYDAJ`→`debit` 영문 매핑 |
| 결측치 | 거래유형 결측 → `unknown` 대체 |
| 금액 이상값 | 음수 금액 → 절댓값 처리 |

**aggregator.py — 집계 테이블 생성**

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

### 4.3 Load 단계 — MySQL 적재

**config.py — 환경변수 분리 (보안)**

```python
from dotenv import load_dotenv
import os

load_dotenv()
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = os.getenv("DB_PORT", "3306")
DB_USER     = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME     = os.getenv("DB_NAME", "berka")
```

**.env.example (GitHub 공개 — 실제 값 없음)**

```bash
DB_HOST=localhost
DB_PORT=3306
DB_USER=your_username
DB_PASSWORD=your_password
DB_NAME=berka
```

**.gitignore 필수 항목**

```bash
.env
data/raw/
*.pyc
__pycache__/
```

**loader.py — MySQL 적재**

```python
engine = create_engine('mysql+pymysql://user:pw@localhost/berka')

daily.to_sql('daily_summary', engine,
             if_exists='replace',
             index=False,
             chunksize=1000)
```

---

## 5. Phase 2 — WPF 분석 대시보드

### 5.1 EventViewer → BerkaAnalytics 구조 매핑

| EventViewer | BerkaAnalytics | 변경점 |
|-------------|----------------|--------|
| `EventFiles.cs` | `AccountLoader.cs` | 파일 I/O → DB 쿼리 |
| `NoiseLevelFeature` | `SpendingTrendFeature` | MySQL `daily_summary` 조회 |
| `OctaveBandFeature` | `CategoryFeature` | MySQL `category_summary` 조회 |
| `WaveformFeature` | `AmountDistFeature` | 금액 분포 집계 |
| `MelSpectrogramFeature` | `BehaviorHeatmapFeature` | 시간×요일 행렬 |
| `IPlotRenderer` | `IPlotRenderer` | **그대로 유지** |
| `NoiseLevelRender` | `SpendingTrendRender` | ScottPlot 라인 |
| `OctaveBandRender` | `CategoryRender` | ScottPlot 막대 |
| `WaveformRender` | `AmountDistRender` | ScottPlot 히스토그램 |
| `MelSpectrogramRender` | `BehaviorHeatmapRender` | SkiaSharp 히트맵 |
| `CursorSyncService` | `CursorSyncService` | **그대로 유지** |
| `ClipLabelRepository` | `AnomalyRepository` | 이상 구간 조회 |

> **핵심**: 파일 I/O가 DB 쿼리로 바뀐 것 외에 5계층 구조 동일

### 5.2 4분할 패널 설계

```
┌──────────────────────┬──────────────────────┐
│  패널 1               │  패널 2               │
│  일별 지출 추이        │  시간×요일 히트맵      │
│  ScottPlot 라인       │  SkiaSharp            │
│  이상 구간 빨간 오버레이│  결제 집중 시간대      │
├──────────────────────┼──────────────────────┤
│  패널 3               │  패널 4               │
│  업종별 지출 분포      │  월별 지출 비교        │
│  ScottPlot 막대       │  ScottPlot 막대       │
│  이상 업종 강조 표시   │  전월 대비 증감        │
└──────────────────────┴──────────────────────┘
```

### 5.3 DB 연동 방식

```csharp
// EventViewer: 파일 읽기
var raw = JsonSerializer.Deserialize<NseData>(File.ReadAllText(path));

// BerkaAnalytics: DB 쿼리
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

## 6. Phase 3 — 이상 탐지 모듈

### 6.1 3단계 탐지 구조 — 전부 비지도 학습

| 단계 | 방법 | 특징 |
|------|------|------|
| 1단계 | Z-Score | 단일 변수(금액) 극단치 탐지 |
| 2단계 | Isolation Forest | 다변수 데이터 공간 고립도 측정 |
| 3단계 | Autoencoder | 비선형 정상 패턴 학습 후 재구성 오차 탐지 |

> XGBoost를 제외한 이유: Z-Score 레이블로 XGBoost를 학습시키면 Z-Score 임계치를 모방하는 룰 기반 분류기가 됩니다. 비지도 방식 3가지로 통일하면 "레이블 없는 환경에서의 이상 탐지" 논리가 일관됩니다.

### 6.2 Z-Score

```python
def detect_zscore(df: pd.DataFrame, threshold: float = 2.5) -> pd.DataFrame:
    mean = df['total_amount'].mean()
    std  = df['total_amount'].std()
    df['z_score']    = (df['total_amount'] - mean) / std
    df['is_anomaly'] = df['z_score'].abs() > threshold
    df['method']     = 'zscore'
    return df
```

### 6.3 Isolation Forest

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

### 6.4 Autoencoder

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

### 6.5 탐지 결과 → MySQL 적재

```python
for result_df in [zscore_result, iforest_result, autoencoder_result]:
    result_df.to_sql('anomaly_flags', engine,
                     if_exists='append',
                     index=False)
```

---

## 7. MySQL 스키마 설계

### 7.1 테이블 구조

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

### 7.2 인덱스 설계 기준

| 테이블 | 인덱스 | 이유 |
|--------|--------|------|
| `raw_transactions` | `(account_id, date)` | 계좌별 기간 조회가 가장 빈번 |
| `daily_summary` | `UNIQUE (account_id, date)` | 중복 적재 방지 + 조회 성능 |
| `anomaly_flags` | `(account_id, date)` | 대시보드 오버레이 조회용 |

---

## 8. 이상 탐지 성능 평가 방법론

레이블이 없는 비지도 학습 환경에서는 Accuracy/F1-Score 같은 지도학습 지표를 사용할 수 없습니다. 3가지 방법으로 대체합니다.

### 8.1 Precision@K — 3개 모델 비교

각 모델의 이상 점수 상위 K건(K=50, 100)을 직접 확인하여 "실제로 이상해 보이는가?" 판단 후 비율을 계산합니다.

### 8.2 재구성 오차 분포 시각화 (Autoencoder 전용)

```python
normal_errors  = errors[~is_anomaly]
anomaly_errors = errors[is_anomaly]

plt.hist(normal_errors,  bins=50, alpha=0.6, label='Normal')
plt.hist(anomaly_errors, bins=50, alpha=0.6, label='Anomaly')
plt.xlabel('Reconstruction Error (MSE)')
plt.title('Normal vs Anomaly Error Distribution')
```

두 분포가 명확히 분리되면 Autoencoder가 정상/이상 패턴을 구별하고 있다는 증거입니다.

### 8.3 3개 모델 탐지 결과 겹침 분석

```python
z_flags  = set(zscore_anomalies['trans_id'])
if_flags = set(iforest_anomalies['trans_id'])
ae_flags = set(autoencoder_anomalies['trans_id'])

# 2개 이상 모델이 탐지한 거래 = 고신뢰 이상
high_confidence = z_flags & if_flags | z_flags & ae_flags | if_flags & ae_flags
```

---

## 9. 개발 일정 (9주)

| 주차 | 작업 내용 | 산출물 | 완료 기준 |
|------|----------|--------|----------|
| **Week 1** | Berka 데이터 탐색 + MySQL 스키마 설계 | ERD + DDL SQL | 테이블 4개 생성 완료 |
| **Week 2** | ETL Extract + Load 구현 | `extractor.py` `loader.py` | CSV → MySQL 적재 완료 |
| **Week 3** | ETL Transform 구현 | `cleaner.py` `aggregator.py` | 집계 테이블 3개 완성 |
| **Week 4** | WPF 뼈대 + MySQL 연동 | DB 연결 + AccountLoader | 계좌 데이터 C#에서 조회 |
| **Week 5** | Feature 레이어 4개 | `*Feature.cs` 4개 | 데이터 모델 변환 완료 |
| **Week 6** | Render 레이어 4개 | `*Render.cs` 4개 | 4분할 패널 시각화 완성 |
| **Week 7** | MVVM + 서비스 + 필터 | `DashboardViewModel` | 계좌 선택 → 대시보드 갱신 |
| **Week 8** | 이상 탐지 모듈 3단계 | `zscore_detector.py` `isolation_forest.py` `autoencoder.py` | anomaly_flags 적재 + 오버레이 |
| **Week 9** | README + 데모 GIF + 정리 | GitHub 완성본 | 데모 GIF 포함 |

---

## 10. 레포지토리 구조

### BerkaETLPipeline (Python)

```
BerkaETLPipeline/
├── data/raw/               Berka CSV 원본 (gitignore)
├── extract/extractor.py
├── transform/
│   ├── cleaner.py
│   ├── aggregator.py
│   └── feature_builder.py
├── load/loader.py
├── detection/
│   ├── zscore_detector.py
│   ├── isolation_forest.py
│   ├── autoencoder.py
│   └── evaluator.py
├── pipeline.py
├── config.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

### BerkaAnalyticsDashboard (C#/WPF)

```
BerkaAnalyticsDashboard/
├── App.xaml / MainWindow.xaml
├── Models/
├── Features/
├── Renderers/
├── Services/
├── ViewModels/
├── Views/
├── Repositories/
└── README.md
```
