#coding=utf-8
import sys
import os
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../lib'))

import redis
import json
import time
import sys
import logging
import traceback
from config import Config 

detlog = logging.getLogger('details')
exclog = logging.getLogger("exception")

DEFAULT_CONTEXT = {
	"history":[],
	"last_from":"",
	"last_time":0
}

mem = {}
def jdefault(o):
    if isinstance(o, datetime):
         return o.isoformat()
    return o.__dict__

class SessionManager(object):

	def __init__(self, redis_pool, max_turn=20, max_interval=sys.maxint, default_expire=100000):
		self._rp = redis_pool
		self._r = redis.Redis(connection_pool = redis_pool)
		self._max_turn = max_turn
		self._max_interval = max_interval
		self._default_expire = default_expire

	def get(self, uid):
		context_str = self._r.get(uid)
		#context_str = mem.get(uid, None)
		if context_str:
			try:
				context = json.loads(context_str)
				#context = context_str
			except Exception, e:
				exclog.warning("[uid] %s [context] %s\n%s" % (uid, context_str, traceback.format_exc(e)))
				context = DEFAULT_CONTEXT
		else:
			context = DEFAULT_CONTEXT
		return context

	def add(self, uid, query, query_t, result, result_t, last_context=None, expire=None):
		detlog.info("[session_add] [query=%s] [result=%s]\n" % (query, json.dumps(result, ensure_ascii=False)))
		# use first one as default
		context = last_context if last_context else self.get(uid)

		# record recent history
		history = context["history"]
		if query:
			if history and query_t - history[-1]["time"] >= self._max_interval:
				history = []
			history.append({"utterance":query, "time":query_t, "from":None})

		if result:
			res_str, info = result["answer"], result["debug_info"]
			if history and result_t - history[-1]["time"] >= self._max_interval:
				history = []
			history.append({"utterance":res_str, "time":result_t, "from":info["from"]})

		# retrieve infos
		context["history"] = history[0-self._max_turn:]
		context["last_time"] = history[-1]["time"]
		context["last_from"] = history[-1]["from"]

		context_str = json.dumps(context, default=jdefault)
		#mem[uid] = context

		expire = self._default_expire if not expire else expire
		#self._r.setex(uid, expire, context_str)
		self._r.set(uid, context_str)
		return

	def info(self):
		used_memory = self._r.info()['used_memory']
		maxmemory = self._r.config_get()['maxmemory']

		used_memory = float(used_memory/1024/1024)
		return used_memory, maxmemory

	def clear(self):
		self._r.flushdb()



if __name__ == "__main__":
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

	conf = Config("dev", True, "develop")
	session_redis_pool = redis.ConnectionPool(host=conf.USER_LAST_FROM[0], port=conf.USER_LAST_FROM[1], db=conf.USER_LAST_FROM[2], password=conf.USER_LAST_FROM[3])
	sem = SessionManager(session_redis_pool, max_turn=20, max_interval=30, default_expire=7200)

	N = 10000000
	user_n = 1000
	sem.clear()
	#t = time.time()
	#for i in range(N):
	#	context = sem.get(str(i%user_n))
	#	#print context
	#	sem.add(str(i%user_n), "哈哈这是啥_%d" % i, time.time(), ("你在干嘛啊_%d" % i, {"from":"whatever"}), time.time() + 2, context)
	#	if i % user_n == 0:
	#		used_memory, maxmemory = sem.info()
	#		print "%.4f" % used_memory, maxmemory, i / ((time.time() - t) * 1.0)
