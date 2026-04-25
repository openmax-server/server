class SQLQueries:
    def __init__(self):
        pass

    SELECT_USER_BY_TG_ID = "SELECT * FROM users WHERE telegram_id = %s"

    INSERT_USER = """
        INSERT INTO users
        (phone, telegram_id, firstname, lastname, username,
         profileoptions, options, accountstatus, updatetime, lastseen)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    INSERT_USER_DATA = """
        INSERT INTO user_data
        (phone, user_config, chat_config)
        VALUES (%s, %s, %s)
    """

    INSERT_DEFAULT_FOLDER = """
        INSERT INTO user_folders
        (id, phone, title, sort_order)
        VALUES ('all.chat.folder', %s, 'Все', 0)
    """
