from azure.identity import DefaultAzureCredential, ManagedIdentityCredential

APP_ENV = "dev"  # Change to 'dev' for local development


def get_azure_credential(client_id=None):
    """
    Retrieves the appropriate Azure credential based on the application environment.

    If the application is running locally, it uses DefaultAzureCredential (tries
    Azure CLI, Azure PowerShell, Interactive Browser, etc.). Use this when az CLI
    fails (e.g. purview extension PermissionError) — Azure PowerShell will work.

    Otherwise, it uses a managed identity credential.

    Args:
        client_id (str, optional): The client ID for the managed identity. Defaults to None.

    Returns:
        DefaultAzureCredential or ManagedIdentityCredential: The Azure credential object.
    """
    if APP_ENV == "dev":
        return DefaultAzureCredential()
    else:
        return ManagedIdentityCredential(client_id=client_id)
