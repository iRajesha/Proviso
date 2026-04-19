from pydantic import AliasChoices, Field
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
    # Retained for backwards compatibility with older OpenAI-compatible setup.
    oci_genai_api_key: str = ""
    oci_config_file: str = "~/.oci/config"
    oci_config_profile: str = ""

    # ADB
    adb_dsn: str = Field(
        default="",
        validation_alias=AliasChoices("ADB_DSN_PROVISO", "ADB_DSN"),
    )
    adb_user: str = Field(
        default="WORKBENCH_USER",
        validation_alias=AliasChoices("ADB_USER_PROVISO", "ADB_USER"),
    )
    adb_password: str = Field(
        default="",
        validation_alias=AliasChoices("ADB_PASSWORD_PROVISO", "ADB_PASSWORD"),
    )
    adb_wallet_dir: str = Field(
        default="/opt/oracle/wallet",
        validation_alias=AliasChoices(
            "ADB_WALLET_DIR_PROVISO",
            "ADB_WALLET_DIR",
        ),
    )

    # App
    api_port: int = 8000
    log_level: str = "INFO"
    cors_origins: str = "*"

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
