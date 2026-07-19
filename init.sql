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
    embedding vector(3)
);
