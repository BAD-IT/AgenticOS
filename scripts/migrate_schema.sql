DO $$ BEGIN
    CREATE TYPE task_priority AS ENUM ('URGENT', 'NORMAL', 'LOW');
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

ALTER TABLE system_tasks ADD COLUMN IF NOT EXISTS priority task_priority NOT NULL DEFAULT 'NORMAL';
ALTER TABLE system_tasks ADD COLUMN IF NOT EXISTS parent_task_id VARCHAR(255) DEFAULT NULL;
ALTER TABLE system_tasks ADD COLUMN IF NOT EXISTS webhook_url TEXT DEFAULT NULL;
CREATE INDEX IF NOT EXISTS idx_tasks_priority_status ON system_tasks (priority, status, created_at);
