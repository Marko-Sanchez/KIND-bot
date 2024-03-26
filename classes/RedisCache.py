import redis
import datetime

"""
    This class represents the Redis Cache.
"""
class RedisCache:

    LOG_DATABASE  = 0
    USER_DATABASE = 1

    PST_OFFSET    = -7

    def __init__(self, host="localhost", port=6379):
        self.redis_client = redis.Redis(host=host, port=port, decode_responses=True)

    def ping(self):
        return self.redis_client.ping()

    def log_message(self, message, expiration_time=43200):
        self.redis_client.select(self.LOG_DATABASE)

        pst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=self.PST_OFFSET)
        key     = f"log:{pst_now.strftime('%I:%M:%S %p %f')[:-3]}"

        self.redis_client.setex(key, expiration_time, message)

    def log_error(self, error, expiration_time=43200):
        self.redis_client.select(self.LOG_DATABASE)

        pst_now = datetime.datetime.utcnow() + datetime.timedelta(hours=self.PST_OFFSET)
        key     = f"error:{pst_now.strftime('%I:%M:%S %p %f')[:-3]}"

        self.redis_client.setex(key, expiration_time, error)

    def get_logs(self, limit=10):
        self.redis_client.select(self.LOG_DATABASE)

        logs = []
        keys = self.redis_client.keys("log:*")
        keys.sort(reverse=True)

        for key in keys[:limit]:
            logs.append(self.redis_client.get(key))

        return logs

    def does_user_exist(self, authorID: str):
        self.redis_client.select(self.USER_DATABASE)

        authorID_str = str(authorID)
        return self.redis_client.exists(authorID_str)

    def does_guild_exist(self, authorID: str, guildID: str):
        self.redis_client.select(self.USER_DATABASE)

        return self.redis_client.json().get(authorID).get(guildID)

    def get_user(self, authorID: str):
        self.redis_client.select(self.USER_DATABASE)

        return self.redis_client.json().get(authorID)

    def get_user_field(self, authorID:int, path: str):
        self.redis_client.select(self.USER_DATABASE)

        return self.redis_client.json().get(authorID, path)


    def set_user(self, authorID: int, *args, expire: bool = False):
        self.redis_client.select(self.USER_DATABASE)

        self.redis_client.json().set(authorID, *args)
        self.redis_client.expire(str(authorID), 10800) if expire else None

    def increment_user(self, authorID: int, *args):
        self.redis_client.select(self.USER_DATABASE)

        return self.redis_client.json().numincrby(authorID, *args)
