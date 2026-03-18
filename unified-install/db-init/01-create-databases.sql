-- ========================================
-- Create Databases and Users
-- ========================================

-- Create shared authentication database
CREATE DATABASE IF NOT EXISTS `platform_auth` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create Cloude database
CREATE DATABASE IF NOT EXISTS `cloude_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create HelpDesk database
CREATE DATABASE IF NOT EXISTS `helpdesk_db` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create application user with limited permissions
-- Note: Password should be changed in production!
-- Get the password from environment variable (set in docker-compose)
CREATE USER IF NOT EXISTS 'platform_user'@'%' IDENTIFIED BY 'platform_password';

-- Grant permissions to shared auth database
GRANT ALL PRIVILEGES ON `platform_auth`.* TO 'platform_user'@'%';

-- Grant permissions to Cloude database
GRANT ALL PRIVILEGES ON `cloude_db`.* TO 'platform_user'@'%';

-- Grant permissions to HelpDesk database
GRANT ALL PRIVILEGES ON `helpdesk_db`.* TO 'platform_user'@'%';

-- Apply permissions immediately
FLUSH PRIVILEGES;

-- ========================================
-- Verify Creation
-- ========================================

-- Show created databases
SHOW DATABASES LIKE 'platform_%';
SHOW DATABASES LIKE 'cloude_%';
SHOW DATABASES LIKE 'helpdesk_%';

-- Show created user
SELECT User, Host FROM mysql.user WHERE User='platform_user';
