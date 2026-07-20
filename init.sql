CREATE EXTENSION IF NOT EXISTS vector;

CREATE TYPE task_status AS ENUM ('USER_INPUT', 'TASK', 'PENDING', 'REVIEW', 'RESULT_OUTPUT', 'ERROR');

CREATE TABLE IF NOT EXISTS system_tasks (
    message_id VARCHAR(255) PRIMARY KEY,
    payload JSONB NOT NULL,
    status task_status NOT NULL DEFAULT 'USER_INPUT',
    workspace_id INT DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS system_notifications (
    message_id VARCHAR(255) PRIMARY KEY,
    payload JSONB NOT NULL,
    workspace_id INT DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_skills (
    id SERIAL PRIMARY KEY,
    task_intent TEXT,
    skill_abstraction TEXT,
    embedding vector(768)
);

CREATE TABLE IF NOT EXISTS system_debug_trace (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255),
    node_name VARCHAR(100),
    state_diff JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Triggers for Real-Time WebSockets
CREATE OR REPLACE FUNCTION notify_system_tasks() RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('system_tasks_channel', row_to_json(NEW)::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS system_tasks_notify_trigger ON system_tasks;
CREATE TRIGGER system_tasks_notify_trigger
AFTER INSERT OR UPDATE ON system_tasks
FOR EACH ROW EXECUTE FUNCTION notify_system_tasks();

CREATE OR REPLACE FUNCTION notify_system_notifications() RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('system_notifications_channel', row_to_json(NEW)::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS system_notifications_notify_trigger ON system_notifications;
CREATE TRIGGER system_notifications_notify_trigger
AFTER INSERT ON system_notifications
FOR EACH ROW EXECUTE FUNCTION notify_system_notifications();

CREATE OR REPLACE FUNCTION notify_system_debug() RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('system_debug_channel', row_to_json(NEW)::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS system_debug_notify_trigger ON system_debug_trace;
CREATE TRIGGER system_debug_notify_trigger
AFTER INSERT ON system_debug_trace
FOR EACH ROW EXECUTE FUNCTION notify_system_debug();
