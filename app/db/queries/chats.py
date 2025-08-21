## CREATE

def create_new_chat_message_query():
    return """
    INSERT INTO chats (user_id, message_text, sender, message_order, created_at)
    VALUES (%s, %s, %s, %s, NOW())
    RETURNING id;
    """

def create_multiple_chat_messages_query():
    return """
    INSERT INTO chats (user_id, message_text, sender, message_order, created_at)
    VALUES %s
    RETURNING id;
    """

## READ

def get_all_chats_by_user_query():
    return """
    SELECT id, user_id, message_text, sender, created_at, message_order
    FROM chats 
    WHERE user_id = %s 
    ORDER BY message_order ASC
    """

def get_recent_chats_by_user_query():
    return """
    SELECT id, user_id, message_text, sender, created_at, message_order
    FROM chats 
    WHERE user_id = %s 
    ORDER BY message_order DESC 
    LIMIT %s
    """

def get_chat_count_by_user_query():
    return """
    SELECT COUNT(*) as message_count
    FROM chats 
    WHERE user_id = %s
    """

def get_last_message_order_by_user_query():
    return """
    SELECT COALESCE(MAX(message_order), 0) as last_order
    FROM chats 
    WHERE user_id = %s
    """

## UPDATE

def update_chat_message_query():
    return """
    UPDATE chats 
    SET message_text = %s, created_at = NOW() 
    WHERE id = %s AND user_id = %s
    """

## DELETE

def delete_chat_message_query():
    return """
    DELETE FROM chats 
    WHERE id = %s AND user_id = %s
    """

def delete_all_chats_by_user_query():
    return """
    DELETE FROM chats 
    WHERE user_id = %s
    """

def delete_old_chats_by_user_query():
    return """
    DELETE FROM chats 
    WHERE user_id = %s 
    AND message_order NOT IN (
        SELECT message_order 
        FROM chats 
        WHERE user_id = %s 
        ORDER BY message_order DESC 
        LIMIT %s
    )
    """