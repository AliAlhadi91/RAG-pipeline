from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # defaults (kept as-is where safe)
    BASE_URL: str
    HEADERS: dict = {"User-Agent": "Mozilla/5.0"}
    MAX_THREADS: int = 10
    SOURCE_BUCKET: str
    DEST_BUCKET: str
    PROFILE_NAME: str
    REGION_NAME: str
    MAX_WORKERS: int = 10
    LOG_FILE: str = "errors.log"
    INPUT_GLOB: str = "rulings_*.json"
    OUTPUT_FOLDER: str = "enriched_rulings"
    S3_BUCKET: str
    MAX_RETRIES: int = 3
    AWS_PROFILE: str
    project_id: str
    location: str
    processor_id: str
    json_key_path: str
    s3_bucket_ocr: str
    bucket_name_cleaned: str
    SUBCHUNK_TOKEN_LIMIT: int = 50
    FINAL_CHUNK_TOKEN_LIMIT: int = 250
    WINDOW_SIZE: int = 3
    BREAKPOINT_PERCENTILE: int = 95
    MODEL_ID: str
    CHUNK_BUCKET: str
    WEAVIATE_URL: str
    CLASS_NAME: str
    AWS_REGION: str
    LAYOUT_ENDPOINT_NAME: str
    EXPECTED_DIM: int = 3072

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
        case_sensitive=True,
    )


settings = Settings()
