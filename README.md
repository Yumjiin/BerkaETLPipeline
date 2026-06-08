# BerkaETLPipeline

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-ML-F7931E?logo=scikitlearn&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-DL-EE4C2C?logo=pytorch&logoColor=white)

실제 체코 은행 공개 데이터(Berka Dataset)를 MySQL로 적재하는 ETL 파이프라인과  
Z-Score · Isolation Forest · Autoencoder 3가지 방법으로 이상 거래를 탐지하는
비지도 학습 기반 이상 탐지 모듈입니다.

> **연관 레포**: [BerkaAnalyticsDashboard](https://github.com/Yumjiin/BerkaAnalyticsDashboard)
> — ETL로 적재된 MySQL 데이터를 시각화하는 WPF 4분할 분석 대시보드

---

## 파이프라인 흐름

```
Berka CSV (8개)
    ↓
Extract        (extract/extractor.py)          CSV 읽기 + 스키마 검증
    ↓
Transform      (transform/cleaner.py)          결측치 처리 + 타입 변환
               (transform/aggregator.py)       일별/업종별 집계
               (transform/feature_builder.py)  계좌 프로파일 생성
    ↓
Load           (load/loader.py)                MySQL 적재
    ↓
Detection      (detection/zscore_detector.py)      Z-Score 통계 기반
               (detection/isolation_forest.py)     Isolation Forest ML 기반
               (detection/autoencoder.py)           Autoencoder 딥러닝
               (detection/evaluator.py)             앙상블 + Precision@K 평가
    ↓
Detail 저장    zscore_detail / iforest_detail / autoencoder_detail
               탐지 판단 근거 (z_value, score, reconstruction_error 등)
```

---

## 기술 스택

| 분류 | 기술 |
|------|------|
| 언어 | Python 3.11 |
| ETL | pandas, SQLAlchemy, pymysql |
| 이상 탐지 | scikit-learn, PyTorch |
| DB | MySQL 8.0 |
| 컨테이너 | Docker, docker-compose |

---

## 프로젝트 구조

```
BerkaETLPipeline/
├── extract/
│   └── extractor.py           CSV 읽기 + 스키마 검증
├── transform/
│   ├── cleaner.py             결측치 처리 + 타입 변환
│   ├── aggregator.py          일별/업종별 집계
│   └── feature_builder.py    계좌 프로파일 생성
├── load/
│   └── loader.py              MySQL 적재
├── detection/
│   ├── zscore_detector.py     Z-Score 통계 기반
│   ├── isolation_forest.py    Isolation Forest ML 기반
│   ├── autoencoder.py         Autoencoder 딥러닝
│   └── evaluator.py           Precision@K 평가
├── models/
│   ├── autoencoder.pt         학습된 Autoencoder 모델
│   └── autoencoder.onnx       ONNX 변환 모델
├── data/
│   └── raw/                   Berka CSV 원본 (gitignore)
├── pipeline.py                ETL 파이프라인 진입점
├── detection_pipeline.py      이상 탐지 진입점
├── config.py                  환경변수 로딩
├── .env.example               환경변수 템플릿
├── docker-compose.yml
└── requirements.txt
```

---

## 실행 방법

### 방법 1 - Docker (권장)

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env 파일에 DB 정보 입력

# 2. ETL 실행
docker compose run --rm etl

# 3. 이상 탐지 실행
docker compose run --rm detection
```

### 방법 2 - 직접 실행

```bash
# 1. 가상환경 생성
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 2. 라이브러리 설치
pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env

# 4. 실행
python pipeline.py
python detection_pipeline.py
```

---

## 환경변수 설정

`.env.example`을 복사해 `.env`를 만들고 값을 채워주세요.

```env
DB_USER=berka_user        # 원하는 MySQL 유저명
DB_PASSWORD=your_password # 원하는 MySQL 비밀번호
DB_NAME=berka             # 원하는 데이터베이스 이름
```

> DB_HOST는 docker-compose가 자동으로 설정합니다. 직접 실행 시 DB_HOST=localhost를 추가하세요.

### 직접 실행의 경우 - MySQL 사전 설정 필요

Docker 없이 직접 실행할 경우, 로컬 MySQL에서 아래 명령어로 DB와 유저를 먼저 생성해야 합니다.

```sql
CREATE DATABASE berka;
CREATE USER 'berka_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON berka.* TO 'berka_user'@'localhost';
```

그 후 `.env`에 동일한 값을 입력하고, `DB_HOST=localhost`도 추가하세요.

```env
DB_HOST=localhost
DB_USER=berka_user
DB_PASSWORD=your_password
DB_NAME=berka
```

---

## 적재 결과 

MySQL 테이블


| 테이블                    | 설명                    | 행 수       |
| ------------------------- | ----------------------  | ----------  |
| raw_transactions          | 정제된 거래 내역         | 1,056,320행 |
| daily_summary             | 계좌별 일별 지출 집계     | 597,080행   |
| category_summary          | 계좌별 업종별 지출 집계   | 13,649행    |
| account_profiles          | 계좌별 종합 프로파일      | 4,500행     |
| anomaly_flags             | 모델별 이상 탐지 결과     | 73,476행    |
| high_confidence_anomalies | 2개 이상 모델 공통 탐지    | 13,288행    |
| zscore_detail             | Z-Score 판단 근거          | 597,080행   |
| iforest_detail            | Isolation Forest 판단 근거 | 597,080행   |
| autoencoder_detail        | Autoencoder 판단 근거      | 597,080행   |


이상 탐지 결과 


| 모델               | 탐지 건수   | 탐지율   | 판단 근거 저장          |
| ---------------- | ------- | ----- | -------------------------------  |
| Z-Score          | 13,795건 | 2.31% | mean, std, z_value              |
| Isolation Forest | 29,852건 | 5.00% | score, tx_count, avg_amount     |
| Autoencoder      | 29,829건 | 5.00% | reconstruction_error, threshold |
| 고신뢰 (2개+ 공통)     | 13,288건 | 2.23% | detected_by, model_count   |
| 3개 모델 공통         | 3,571건  | 0.60% | —                           |

모두 비지도 학습 방식으로 레이블 없이 작동합니다.

---

## 데이터셋

[Berka Dataset](https://www.kaggle.com/datasets/marceloventura/the-berka-dataset) — 1993~1998년 체코 은행 실제 거래 데이터

| 항목 | 내용 |
|------|------|
| 계좌 | 4,500개 |
| 거래 | 약 1,000,000건 |
| 테이블 | 8개 (account / client / transaction / loan 등) |

> 데이터는 저작권 문제로 포함하지 않습니다.  
> 위 링크에서 직접 다운로드 후 `data/raw/` 에 넣으세요.

---

## 설계 문서

- [프로젝트 설계서](./docs/BerkaAnalytics_설계서.md)
- [기획서 + IA](./docs/BerkaAnalytics_기획서_IA.md)
- [Figma 와이어프레임](https://www.figma.com/design/apK5GQdChjRr2nldRsveic/BerkaAnalytics-%E2%80%94-Wireframe?node-id=0-1&p=f&t=fTBbadj3a5oA2nDS-0)
