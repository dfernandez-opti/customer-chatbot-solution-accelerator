from pathlib import Path
from typing import List, Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings

# Get the absolute path to the .env file
_current_dir = Path(__file__).parent  # This is the app directory
_env_file_path = _current_dir.parent / ".env"  # Go up one level to src/api/.env


class Settings(BaseSettings):
    # Application
    app_name: str = "E-commerce Chat API"
    app_version: str = "1.0.0"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS - Use string type to avoid JSON parsing issues (incl. 5174 when 5173 is in use)
    allowed_origins_str: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:5174"

    @property
    def allowed_origins(self) -> List[str]:
        """Parse allowed origins from comma-separated string"""
        return [
            origin.strip()
            for origin in self.allowed_origins_str.split(",")
            if origin.strip()
        ]

    # Azure Cosmos DB
    cosmos_db_endpoint: Optional[str] = None
    cosmos_db_database_name: str = "ecommerce_db"
    cosmos_db_containers: dict = {
        "products": "products",
        "users": "users",
        "chat_sessions": "chat_sessions",
        "carts": "carts",
        "transactions": "transactions",
    }

    # Azure OpenAI
    azure_openai_endpoint: Optional[str] = None
    azure_openai_api_version: str = "2025-01-01-preview"
    azure_openai_deployment_name: str = "gpt-4o"

    # Azure Key Vault
    azure_key_vault_url: Optional[str] = None

    # Microsoft Entra ID
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    azure_tenant_id: Optional[str] = None

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window: int = 60  # seconds

    # Azure Search (for reference plugin)
    azure_search_endpoint: Optional[str] = None
    azure_search_index: str = "reference-docs"
    azure_search_product_index: str = "products"

    # Azure AI Foundry
    azure_foundry_endpoint: Optional[str] = None
    # Additional custom agent IDs
    foundry_chat_agent: str = ""
    foundry_product_agent: str = ""
    foundry_policy_agent: str = ""

    # Feature Flags
    use_foundry_agents: bool = False

    # Azure Content Safety (moderación de contenido - alertas por solicitudes indebidas)
    content_safety_endpoint: Optional[str] = None
    content_safety_key: Optional[str] = None
    content_safety_enabled: bool = False

    @field_validator("content_safety_enabled", mode="before")
    @classmethod
    def parse_content_safety_enabled(cls, v):
        """Aceptar 'true', '1', 'yes' desde variables de entorno (Azure env vars son strings)"""
        if isinstance(v, bool):
            return v
        if isinstance(v, str) and v.lower() in ("true", "1", "yes", "on"):
            return True
        return False

    class Config:
        env_file = str(_env_file_path)  # Use absolute path to .env file
        case_sensitive = False
        extra = "ignore"  # Allow extra environment variables


# Global settings instance
settings = Settings()


# Check if we have Cosmos DB configuration
def has_cosmos_db_config() -> bool:
    return (
        settings.cosmos_db_endpoint is not None
    )  # and settings.cosmos_db_key is not None


# Check if we have Azure OpenAI configuration
def has_openai_config() -> bool:
    return (
        settings.azure_openai_endpoint is not None
        and settings.azure_openai_api_key is not None
    )


# Check if we have Entra ID configuration
def has_entra_id_config() -> bool:
    return all(
        [
            settings.azure_client_id,
            settings.azure_client_secret,
            settings.azure_tenant_id,
        ]
    )


# Check if we have Azure Search configuration (AAD authentication)
def has_azure_search_config() -> bool:
    return settings.azure_search_endpoint is not None


# Legacy function for backwards compatibility (now only checks endpoint)
def has_azure_search_endpoint() -> bool:
    return settings.azure_search_endpoint is not None


# Check if Azure AI Foundry is configured
def has_foundry_config() -> bool:
    return settings.azure_foundry_endpoint is not None and (
        settings.foundry_chat_agent != ""
        or settings.foundry_product_agent != ""
        or settings.foundry_policy_agent != ""
    )


# Check if Azure Content Safety is configured (moderación de contenido)
def has_content_safety_config() -> bool:
    return (
        settings.content_safety_enabled
        and settings.content_safety_endpoint is not None
        and settings.content_safety_key is not None
    )
