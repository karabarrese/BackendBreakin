-- Database Breach Lab Setup Script
-- Creates a PostgreSQL test database with intentional vulnerabilities
-- Usage: psql -d postgres -f setup_lab.sql
--   (add -U postgres if your install has a "postgres" superuser role)

-- ===========================================================================
-- VULNERABILITY CATALOG -- the six weaknesses this lab is built to expose.
-- Each is a demo the agent can discover. Fill in Owner / Status as a team.
-- "Setup needed" flags anything beyond running this script.
--
1. Plaintext passwords (users table)
--        Passwords stored as readable text -- no hashing, salting, or encryption.
--        Fix: hash passwords
--        DONE
--
--   2. Secrets in the clear (secrets table)
--        API keys, AWS key, JWT secret, DB password stored unencrypted.
--        Fix: secrets manager
--	  DONE
--
--   3. Over-permissive grants (app_user)
--        The low-privilege app account can SELECT sensitive tables directly.
--        Fix to teach: least privilege
--	  DONE
--
--   4. Weak / default credentials (escalate app_user -> admin)
--        Guessable role passwords allow privilege escalation.
--        Fix: strong unique secrets
--        Work needed: enforce password auth in pg_hba.conf (trust -> scram-sha-256).
--
--   5. SQL injection via the web front end
--        Unsanitized input reaches a query; one endpoint can leak the whole DB.
--        Fix: parameterized queries.
--        Work needed: build the web server that takes input as passes to DB
--
--   6. Missing audit trail (audit_log table)
--        audit_log is never written to, so none of the above leaves a trace.
--        Fix: log security-relevant actions
--        DONE
-- ===========================================================================

-- Create the test database (Postgres has no CREATE DATABASE IF NOT EXISTS)
SELECT 'CREATE DATABASE breach_lab'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'breach_lab')\gexec

-- Connect to the new database
\c breach_lab

-- Create roles (app_user is the low-privilege application account)
-- Postgres has no CREATE ROLE IF NOT EXISTS, so use a DO block
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user WITH LOGIN PASSWORD 'app_password';
    END IF;
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'admin') THEN
        CREATE ROLE admin WITH LOGIN PASSWORD 'admin_password';
    END IF;
END
$$;

-- Create the users table (Vulnerability: plaintext password storage)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE,
    password VARCHAR(255),
    email VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create the secrets table (Vulnerability: sensitive data stored plaintext)
CREATE TABLE IF NOT EXISTS secrets (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) UNIQUE,
    value TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create the audit_log table (Vulnerability: incomplete audit trail)
CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INT,
    action TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- Seed the users table with test data
TRUNCATE TABLE users CASCADE;
INSERT INTO users (username, password, email) VALUES
    ('alice', 'password123', 'alice@example.com'),
    ('bob', 'letmein456', 'bob@example.com'),
    ('charlie', 'secretpass', 'charlie@example.com');

-- Seed the secrets table with sensitive data
TRUNCATE TABLE secrets CASCADE;
INSERT INTO secrets (key, value) VALUES
    ('API_KEY', 'sk-test-1234567890abcdef'),
    ('DATABASE_PASSWORD', 'prod_db_pass_123'),
    ('JWT_SECRET', 'my-super-secret-jwt-key'),
    ('AWS_ACCESS_KEY', 'AKIAIOSFODNN7EXAMPLE'),
    ('TWILIO_AUTH_TOKEN', 'ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx');

-- Grant permissions to app_user (Vulnerability: over-permissive read access)
GRANT CONNECT ON DATABASE breach_lab TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT ON users TO app_user;
GRANT SELECT ON secrets TO app_user;
GRANT SELECT, INSERT ON audit_log TO app_user;
GRANT USAGE ON SEQUENCE audit_log_id_seq TO app_user;

-- Grant admin role more permissions
GRANT ALL PRIVILEGES ON DATABASE breach_lab TO admin;
GRANT ALL PRIVILEGES ON SCHEMA public TO admin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO admin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO admin;

-- Verify setup
\echo '========================================='
\echo 'Breach Lab Setup Complete'
\echo '========================================='
\echo 'Database: breach_lab'
\echo 'App User: app_user / app_password'
\echo ''
\echo 'Tables:'
SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';

\echo ''
\echo 'Users (passwords stored plaintext):'
SELECT id, username, password FROM users;

\echo ''
\echo 'Secrets (API keys and credentials exposed):'
SELECT key FROM secrets;

\echo ''
\echo 'Roles:'
SELECT rolname FROM pg_roles WHERE rolname IN ('app_user', 'admin', 'postgres');
