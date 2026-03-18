@echo off
REM
REM Django Platform - Docker-Compose Installation Script
REM Windows Batch Version
REM

setlocal enabledelayedexpansion

cls
color 0A
echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║    Django Platform - Docker Installation              ║
echo ║    Cloude (Cloud Storage) + HelpDesk (Ticketing)     ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM Check prerequisites
echo [1/5] Checking prerequisites...

docker --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo ✗ Docker not found. Please install Docker Desktop.
    echo   Visit: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
color 0A
echo ✓ Docker found

docker-compose --version >nul 2>&1
if errorlevel 1 (
    color 0C
    echo ✗ Docker Compose not found.
    pause
    exit /b 1
)
color 0A
echo ✓ Docker Compose found

REM Get configuration from user
echo.
echo [2/5] Configuration
echo.

set /p DOMAIN="Enter domain [localhost]: "
if "!DOMAIN!"=="" set DOMAIN=localhost
echo Domain: !DOMAIN!

set /p INSTALL_CLOUDE="Install Cloude? (y/n) [y]: "
if "!INSTALL_CLOUDE!"=="" set INSTALL_CLOUDE=y

set /p INSTALL_HELPDESK="Install HelpDesk? (y/n) [y]: "
if "!INSTALL_HELPDESK!"=="" set INSTALL_HELPDESK=y

if /i "!INSTALL_CLOUDE!"!="y" if /i "!INSTALL_HELPDESK!"!="y" (
    color 0C
    echo ✗ You must install at least one application.
    pause
    exit /b 1
)

REM Generate secure passwords using Windows built-in
echo.
echo [3/5] Generating secure passwords...

for /f "tokens=*" %%a in ('powershell -Command "[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Random -Maximum 999999999).ToString().PadRight(32)))"') do (
    set "DB_ROOT_PASSWORD=%%a"
)

for /f "tokens=*" %%a in ('powershell -Command "[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Random -Maximum 999999999).ToString().PadRight(32)))"') do (
    set "DB_PASSWORD=%%a"
)

for /f "tokens=*" %%a in ('powershell -Command "[Convert]::ToBase64String([System.Text.Encoding]::UTF8.GetBytes((Get-Random -Maximum 999999999).ToString().PadRight(64)))"') do (
    set "JWT_SECRET=%%a"
)

color 0A
echo ✓ Passwords generated

REM Create .env file
echo.
echo [4/5] Creating .env configuration...

(
echo # Auto-generated configuration
echo DB_ROOT_PASSWORD=!DB_ROOT_PASSWORD!
echo DB_USER=platform_user
echo DB_PASSWORD=!DB_PASSWORD!
echo.
echo JWT_SECRET_KEY=!JWT_SECRET!
echo SSO_COOKIE_DOMAIN=.!DOMAIN!
echo.
echo CLOUDE_DEBUG=False
echo CLOUDE_SECRET_KEY=dev-secret-key
echo CLOUDE_ALLOWED_HOSTS=cloude.!DOMAIN!,!DOMAIN!
echo.
echo HELPDESK_DEBUG=False
echo HELPDESK_SECRET_KEY=dev-secret-key
echo HELPDESK_ALLOWED_HOSTS=helpdesk.!DOMAIN!,support.!DOMAIN!,!DOMAIN!
echo.
echo EMAIL_HOST=smtp.office365.com
echo EMAIL_PORT=587
echo LANGUAGE_CODE=de-de
echo TIME_ZONE=Europe/Berlin
) > .env

color 0A
echo ✓ .env file created

REM Start Docker services
echo.
echo [5/5] Starting Docker services...
echo This may take a few minutes on first run...
echo.

docker-compose pull
if errorlevel 1 goto error_pull

docker-compose build
if errorlevel 1 goto error_build

docker-compose up -d
if errorlevel 1 goto error_up

echo.
echo Waiting for database to be ready...
timeout /t 15 /nobreak

REM Run migrations
if /i "!INSTALL_CLOUDE!"=="y" (
    echo.
    echo Running Cloude migrations...
    docker-compose exec -T cloude_web python manage.py migrate
    docker-compose exec -T cloude_web python manage.py collectstatic --noinput
)

if /i "!INSTALL_HELPDESK!"=="y" (
    echo.
    echo Running HelpDesk migrations...
    docker-compose exec -T helpdesk_web python manage.py migrate
    docker-compose exec -T helpdesk_web python manage.py collectstatic --noinput
)

REM Print success message
color 0A
echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║         Installation Complete!                        ║
echo ╚════════════════════════════════════════════════════════╝
echo.

if /i "!INSTALL_CLOUDE!"=="y" (
    echo Cloude (Cloud Storage):
    echo   Web:       http://cloude.!DOMAIN!
    echo   Admin:     http://cloude.!DOMAIN!/admin
    echo.
)

if /i "!INSTALL_HELPDESK!"=="y" (
    echo HelpDesk (Support Ticketing):
    echo   Web:       http://helpdesk.!DOMAIN!
    echo   Admin:     http://helpdesk.!DOMAIN!/admin
    echo.
)

echo Next steps:
echo 1. Edit C:\Windows\System32\drivers\etc\hosts to add:
echo    127.0.0.1 cloude.!DOMAIN! helpdesk.!DOMAIN!
echo.
echo 2. Create superuser accounts:
if /i "!INSTALL_CLOUDE!"=="y" (
    echo    docker-compose exec cloude_web python manage.py createsuperuser
)
if /i "!INSTALL_HELPDESK!"=="y" (
    echo    docker-compose exec helpdesk_web python manage.py createsuperuser
)
echo.
echo 3. View logs:
echo    docker-compose logs -f
echo.
echo 4. Stop services:
echo    docker-compose down
echo.

color 0A
echo ✓ Installation finished!
echo.
pause
exit /b 0

:error_pull
color 0C
echo ✗ Error pulling Docker images
pause
exit /b 1

:error_build
color 0C
echo ✗ Error building Docker images
pause
exit /b 1

:error_up
color 0C
echo ✗ Error starting Docker containers
pause
exit /b 1
