CREATE TABLE IF NOT EXISTS chats (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    message_text TEXT NOT NULL,
    sender VARCHAR(10) NOT NULL CHECK (sender IN ('user', 'bot')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    message_order INTEGER NOT NULL
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_chats_user_id_order ON chats (user_id, message_order);
CREATE INDEX IF NOT EXISTS idx_chats_created_at ON chats (created_at);