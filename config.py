from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://root:password@localhost:3306/berka"
)

RAW_DATA_DIR: str = os.getenv("RAW_DATA_DIR", "data/raw")

ZSCORE_THRESHOLD: float = float(os.getenv("ZSCORE_THRESHOLD", "2.5"))

ISOLATION_CONTAMINATION: float = float(os.getenv("ISOLATION_CONTAMINATION", "0.05"))