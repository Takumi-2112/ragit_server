## CREATE

def create_new_user_query():
    return """
    INSERT INTO users (username, email, password_hash, vectorstore_path, created_at, updated_at)
    VALUES (%s, %s, %s, %s, NOW(), NOW())
    RETURNING id;
    """


## READ

def get_all_users_query():
    return """
    SELECT id, username, email, vectorstore_path, created_at, updated_at 
    FROM users
    """

def get_user_by_id_query():
    return """
    SELECT id, username, email, password_hash, vectorstore_path, created_at, updated_at
    FROM users WHERE id = %s
    """


def get_user_by_username_query():
    return """
    SELECT id, username, email, password_hash, vectorstore_path, created_at, updated_at
    FROM users WHERE username = %s
    """

def get_user_by_email_query():
    return """
    SELECT id, username, email, password_hash, vectorstore_path, created_at, updated_at
    FROM users WHERE email = %s
    """

def get_newest_user_query():
    return """
    SELECT * FROM users ORDER BY created_at DESC LIMIT 10
    """


## UPDATE

def update_user_email_query():
    return """
    UPDATE users 
    SET email = %s, updated_at = NOW() 
    WHERE id = %s
    """

def update_user_password_query():
    return """
    UPDATE users 
    SET password_hash = %s, updated_at = NOW() 
    WHERE id = %s
    """

def update_user_email_and_password_query():
    return """
    UPDATE users 
    SET email = %s, password_hash = %s, updated_at = NOW() 
    WHERE id = %s
    """

## DELETE

def delete_user_query():
    return """
    DELETE FROM users WHERE id = %s
    """