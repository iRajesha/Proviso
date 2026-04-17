from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # OCI
    oci_region: str = "us-chicago-1"
    oci_compartment_id: str = ""
    oci_tenancy_id: str = ""

    # OCI GenAI
    oci_genai_endpoint: str = (
        "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com/20231130"
    )
    oci_genai_model_id: str = "cohere.command-r-plus"
    oci_genai_api_key: str = ""

    # ADB
    adb_dsn: str = ""
    adb_user: str = "WORKBENCH_USER"
    adb_password: str = ""
    adb_wallet_dir: str = "/opt/oracle/wallet"

    # App
    api_port: int = 8000
    log_level: str = "INFO"
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
