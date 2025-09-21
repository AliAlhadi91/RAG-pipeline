# settings.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # defaults (kept as-is)
    BASE_URL: str = "http://77.42.251.205"
    HEADERS: dict = {"User-Agent": "Mozilla/5.0"}
    MAX_THREADS:int = 10
    SOURCE_BUCKET:str = "ai-lawyer-judgments-raw-pdf"
    DEST_BUCKET:str = "ai-lawyer-judgments-images"
    PROFILE_NAME:str = "AdministratorAccess-064977599910"
    REGION_NAME:str = "eu-west-1"
    MAX_WORKERS:int = 10
    LOG_FILE:str = "errors.log"
    INPUT_GLOB:str = "rulings_*.json"
    OUTPUT_FOLDER:str = "enriched_rulings"
    S3_BUCKET:str = "ai-lawyer-judgments-raw-pdf"
    MAX_RETRIES:int = 3
    AWS_PROFILE:str = "AdministratorAccess-064977599910"
    project_id:str = "ai-laywer"
    location:str = "us"
    processor_id:str = "3ff0a6f8c449dbc6"
    json_key_path:str = "ai-laywer-4e3c21d3e485.json"
    s3_bucket_ocr:str = "ai-lawyer-judgments-json-ocr"
    bucket_name_cleaned:str = "ai-lawyer-judgments-cleaned"
    SUBCHUNK_TOKEN_LIMIT:int = 50
    FINAL_CHUNK_TOKEN_LIMIT:int = 250
    WINDOW_SIZE:int = 3
    BREAKPOINT_PERCENTILE:int = 95
    MODEL_ID:str = "amazon.titan-embed-text-v2:0"
    CHUNK_BUCKET:str = "ai-lawyer-chunks"
    WEAVIATE_URL:str = "http://3.254.142.125:8080"
    CLASS_NAME:str = "LegalChunk"
    AWS_REGION:str = "us-east-1"
    EXPECTED_DIM:int = 3072

    # required (must come from env/.env)
    PROJECT_ID: str
    TYPE: str
    PRIVATE_KEY_ID: str
    PRIVATE_KEY: str
    CLIENT_EMAIL: str
    CLIENT_ID: str
    AUTH_URI: str
    TOKEN_URI: str
    AUTH_PROVIDER_X509_CERT_URL: str
    CLIENT_X509_CERT_URL: str
    UNIVERSE_DOMAIN: str
    GENAI_API_KEY: str

    # IMPORTANT: resolve .env next to this file (not CWD)
    model_config = SettingsConfigDict(
        env_file=Path(__file__).with_name(".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,  # your field names are uppercase; keep this True
    )

settings = Settings()
