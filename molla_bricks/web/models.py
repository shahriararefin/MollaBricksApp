# molla_bricks/web/models.py
from flask_login import UserMixin
from molla_bricks.web import db_controller_instance

class User(UserMixin):
    def __init__(self, id, username, password_hash):
        self.id = id
        self.username = username
        self.password_hash = password_hash

    @staticmethod
    def get(user_id):
        query = "SELECT id, username, password_hash FROM users WHERE id = ?"
        user_data = db_controller_instance.execute_query(query, (user_id,), fetch="one")
        if user_data:
            return User(user_data[0], user_data[1], user_data[2])
        return None

    @staticmethod
    def get_by_username(username):
        query = "SELECT id, username, password_hash FROM users WHERE username = ?"
        user_data = db_controller_instance.execute_query(query, (username,), fetch="one")
        if user_data:
            return User(user_data[0], user_data[1], user_data[2])
        return None