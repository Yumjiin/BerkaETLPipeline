# BerkaETLPipeline

실제 체코 은행 공개 데이터(Berka Dataset)를 MySQL로 적재하는 ETL 파이프라인과
Z-Score / Isolation Forest / Autoencoder 3단계 이상 탐지 모듈입니다.

> **연관 레포**: [BerkaAnalyticsDashboard](https://github.com/{Yumjiin}/BerkaAnalyticsDashboard) — WPF 분석 대시보드

---

## 파이프라인 흐름

```
Berka CSV (8개)
    → Extract  (extractor.py)
    → Transform (cleaner.py + aggregator.py)
    → Load      (loader.py → MySQL)
    → Detection (Z-Score / Isolation Forest / Autoencoder)
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
│   └── extractor.py         CSV 읽기 + 스키마 검증
├── transform/
│   ├── cleaner.py           결측치 처리 + 타입 변환
│   ├── aggregator.py        일별/월별/업종별 집계
│   └── feature_builder.py  계좌 프로파일 생성
├── load/
│   └── loader.py            MySQL 적재
├── detection/
│   ├── zscore_detector.py   Z-Score 통계 기반
│   ├── isolation_forest.py  Isolation Forest ML 기반
│   ├── autoencoder.py       Autoencoder 딥러닝
│   └── evaluator.py         Precision@K 평가
├── data/
│   └── raw/                 Berka CSV 원본 (gitignore)
├── pipeline.py              전체 파이프라인 실행 진입점
├── config.py                환경변수 로딩
├── .env.example             환경변수 템플릿
├── docker-compose.yml       컨테이너 실행
├── Dockerfile
└── requirements.txt
```

---

## 실행 방법

### 방법 1 — Docker (권장)

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env 파일 열어서 DB 정보 입력

# 2. 실행
docker-compose up
```

### 방법 2 — 직접 실행

```bash
# 1. 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. 라이브러리 설치
pip install -r requirements.txt

# 3. 환경변수 설정
cp .env.example .env
# .env 파일 열어서 DB 정보 입력

# 4. 실행
python pipeline.py
```

---

## 데이터셋

[Berka Dataset]([https://sorry.vse.cz/~berka/challenge/pkdd1999/](https://www.kaggle.com/datasets/marceloventura/the-berka-dataset)) — 1993~1998년 체코 은행 실제 거래 데이터

- 계좌: 4,500개
- 거래: 약 1,000,000건
- 테이블: 8개 (account / client / transaction / loan 등)

데이터는 저작권 문제로 포함하지 않습니다. 위 링크에서 직접 다운로드 후 `data/raw/` 에 넣으세요.

---

## 이상 탐지 3단계

| 단계 | 방법 | 특징 |
|------|------|------|
| 1단계 | Z-Score | 단일 변수(금액) 극단치 탐지 |
| 2단계 | Isolation Forest | 다변수 고립도 기반 탐지 |
| 3단계 | Autoencoder | 정상 패턴 학습 후 재구성 오차 탐지 |

모두 **비지도 학습** 방식으로 레이블 없이 작동합니다.

---

## 설계 문서

- [프로젝트 설계서](./docs/BerkaAnalytics_설계서.md)
- [기획서 + IA](./docs/BerkaAnalytics_기획서_IA.md)
- [Figma 와이어프레임](https://figma.com/{[your-figma-link](https://www.figma.com/design/apK5GQdChjRr2nldRsveic/BerkaAnalytics-%E2%80%94-Wireframe?node-id=0-1&p=f&t=fTBbadj3a5oA2nDS-0)})
