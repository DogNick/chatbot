#coding=utf-8
import redis
import pickle
import logging
import traceback

detlog = logging.getLogger('details')
exclog = logging.getLogger('exception')


_cache_config = {
	"weather" : 600.0,
	"translation" : 86400.0,
	"yyzs" : 86400.0,
	"poem" : 86400.0,
	"yaoting" : 86400.0,
	"web_search" : 7200.0,
	"web_search:pesodu_census" : 7200.0,
	"generate" : 86400.0
}

class ResponseCache():
	def __init__(self, host, port, db=0, cache_config=_cache_config):
		self._redis = redis.Redis(host=host, port=port, db=db)
		self._cache_config = cache_config

	def get(self, key):
		try:
			value = self._redis.get(key)
			if value == None:
				return None, False
			else:
				return pickle.loads(value), True
		except Exception, e:
			exclog.error('get cache error\n%s' % (traceback.format_exc(e)))
			return None, False

	def put(self, key, value, channel):
		if channel not in self._cache_config:
			return
		try:
			value = pickle.dumps(value)
			ttl = int(self._cache_config[channel])
			self._redis.setex(key, value, ttl)
		except Exception, e:
			exclog.error('put cache error\n%s' % (traceback.format_exc(e)))
			pass

if __name__=='__main__':
	# 配置logging
	detlog.setLevel(logging.INFO)
	exclog.setLevel(logging.INFO)
	sh1 = logging.StreamHandler(stream=None)
	sh2 = logging.StreamHandler(stream=None)
	sh1.setLevel(logging.INFO)
	sh2.setLevel(logging.INFO)
	formatter1 = logging.Formatter('[pid=%(process)d] [%(asctime)s] [%(filename)s:%(lineno)d] %(message)s')
	formatter2 = logging.Formatter('[pid=%(process)d] [%(asctime)s] [%(filename)s:%(lineno)d] [%(funcName)s] %(message)s')
	sh1.setFormatter(formatter1)
	sh2.setFormatter(formatter2)
	detlog.addHandler(sh1)
	exclog.addHandler(sh2)


	import time
	config = _cache_config
	config["retrieve"] = 2
	r = ResponseCache('127.0.0.1', 9900, 0, config)
	print "empty"
	print r.get("123", "retrieve")
	r.put("123", "123v1", "retrieve")
	print "one value"
	print r.get("123", "retrieve")
	time.sleep(3)
	print "after 2 sec"
	print r.get("123", "retrieve")
