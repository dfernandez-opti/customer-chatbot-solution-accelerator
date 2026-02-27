# Elimina la extensión purview de az CLI que causa PermissionError
# Ejecutar: .\scripts\fix-az-purview.ps1
# Tras ejecutarlo, az y run_create_agents_scripts.ps1 deberían funcionar.

$purviewPath = "$env:USERPROFILE\.azure\cliextensions\purview"
if (Test-Path $purviewPath) {
    Write-Host "Eliminando extensión purview: $purviewPath" -ForegroundColor Yellow
    Remove-Item -Recurse -Force $purviewPath -ErrorAction Stop
    Write-Host "Listo. Prueba: az account show" -ForegroundColor Green
} else {
    Write-Host "La extensión purview no está instalada." -ForegroundColor Gray
}
Write-Host "`nSi az sigue fallando, ejecuta: az extension remove --name purview" -ForegroundColor Gray
