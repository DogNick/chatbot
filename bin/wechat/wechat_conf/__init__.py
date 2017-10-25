from config import Config, GloVar
import redis

redis_pool_perday = redis.ConnectionPool(host='b.redis.sogou', port=1769, db=0, password='chatbot')
redis_pool_afanti = redis.ConnectionPool(host = Config.WECHAT_REDIS[0], port = Config.WECHAT_REDIS[1], db = 4, password = Config.WECHAT_REDIS[3]) # db 4 for afanti result html
redis_pool_user_info = redis.ConnectionPool(host = Config.WECHAT_REDIS[0], port = Config.WECHAT_REDIS[1], db = 1, password = Config.WECHAT_REDIS[3]) # db 1 for user_info
redis_pool_token = redis.ConnectionPool(host = Config.WECHAT_REDIS[0], port = Config.WECHAT_REDIS[1], db = 2, password = Config.WECHAT_REDIS[3]) # db 2 for token
redis_pool_user_cmd = redis.ConnectionPool(host = Config.WECHAT_REDIS[0], port = Config.WECHAT_REDIS[1], db = 0, password=Config.WECHAT_REDIS[3])
