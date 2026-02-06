-- Run these commands in your Database Tool (pgAdmin, DBeaver) or psql terminal
-- You must run this as a SUPERUSER (e.g., 'postgres'), not as 'lms_api_user'.

-- 1. Grant access to the 'assessment' schema
GRANT USAGE ON SCHEMA assessment TO lms_api_user;
GRANT SELECT ON ALL TABLES IN SCHEMA assessment TO lms_api_user;

-- 2. Grant access to the 'lms' schema (for future tasks)
GRANT USAGE ON SCHEMA lms TO lms_api_user;
GRANT SELECT ON ALL TABLES IN SCHEMA lms TO lms_api_user;

-- 3. Ensure future tables are also readable
ALTER DEFAULT PRIVILEGES IN SCHEMA assessment GRANT SELECT ON TABLES TO lms_api_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA lms GRANT SELECT ON TABLES TO lms_api_user;
