from dotenv import load_dotenv
import os

load_dotenv()

# 환경 변수에 정의된 DATABASE_URL 가 없을 경우, .env 에서 읽은 개별 변수들로 조합
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:{os.getenv('DB_PASSWORD', 'password')}@"
    f"{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '3306')}/{os.getenv('DB_NAME', 'berka')}"
)

RAW_DATA_DIR: str = os.getenv("RAW_DATA_DIR", "data/raw")
