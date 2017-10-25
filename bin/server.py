#a1. import sys
from datetime import datetime
import logging
from logging.config import fileConfig
import os
import ssl
import sys
import time

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'common'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../lib'))

#a2. import thirdparty
from config import Config 
from mpfhandler import MultProcTimedRotatingFileHandler
import hashlib
import redis
import tornado
import tornado.httpserver
import tornado.ioloop
import traceback
from tornado.options import define, options, parse_command_line


#b. env & global
# these things will be used globally so must be defined before application imports
fileConfig("log.ini")
logging.getLogger("").handlers[0].suffix = "%Y%m%d-%H"
define('port',default=1024,help='port',type=int)
define('procnum',default=2,help='process num',type=int)
define('source',default='dummy',help='default source',type=bytes)
define('detail_log_dir',default="../logs", help='default source',type=bytes)
define('service', default="chathub", type=bytes)
define('account',default='sogouwangzai', help='account',type=bytes)
define('source_to_load',default="", help='sources to load: wechat,weimi',type=bytes)
define('loglevel',default="info", help='warning, info, debug, error... as logging defined',type=bytes)

#a3. import applicaitons
from intervene import cache, SessionManager
from schedules import SchedulesManager, SCHEDULES
import integrated
import qqgroup
import wechat
import groupqa
import tsinghua_robot
import chaten
import samsung


detlog = logging.getLogger("details")
exclog = logging.getLogger("exception")
parse_command_line()

def main():
	try:
		# resolve log level according to options
		if options.loglevel == "debug":
			detlog.setLevel(logging.DEBUG)
			detlog.handlers[0].setLevel(logging.DEBUG)

		# Aqcuire global configuratino according to options flags
		conf = Config(options.mode, options.log_verbose, options.env)

		# Create SchedulesManager object from schedule defines, conf and other options to handle heavy resources 
		schedules = SchedulesManager(conf, SCHEDULES, options.source_to_load)

		# Initialize response cache 
		response_cache = cache.ResponseCache(host=conf.RESPONSE_CACHE_REDIS[0], port=conf.RESPONSE_CACHE_REDIS[1], db=conf.RESPONSE_CACHE_REDIS[2])

		# Initialize session_manager 
		session_redis_pool = redis.ConnectionPool(host=conf.USER_LAST_FROM[0], port=conf.USER_LAST_FROM[1], db=conf.USER_LAST_FROM[2], password=conf.USER_LAST_FROM[3])
		session_manager = SessionManager(session_redis_pool, max_turn=20)

		# Create Apps for server
		if options.service == "weixin":
			app = wechat.make_app(conf, schedules, response_cache, session_manager, options.account)
		elif options.service == "tsinghua_robot":
			app = tsinghua_robot.make_app(conf, schedules, response_cache, session_manager)
		elif options.service == "samsung":
			app = samsung.make_app(conf, schedules, response_cache, session_manager)
		elif options.service == "qqgroup":
			app = qqgroup.make_app(conf, schedules, response_cache, session_manager)
		elif options.service == "groupqa":
			app = groupqa.make_app(conf, schedules, response_cache, session_manager)
		elif options.service == "chaten":
			app = chaten.make_app(conf, schedules, response_cache, session_manager)
		else:
			app = integrated.make_app(conf, schedules, response_cache, session_manager)

		# https service test
		'''
		if options.service == "tsinghua_robot":
			ssl_dir = "tsinghua_robot/certificate/"
			ssl_ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
			ssl_ctx.load_cert_chain(ssl_dir + "test.tsinghua.robot.com.crt", ssl_dir + "test.tsinghua.robot.com.key")
			server = tornado.httpserver.HTTPServer(app, ssl_options=ssl_ctx)
		else:
			server = tornado.httpserver.HTTPServer(app)
		'''
		server = tornado.httpserver.HTTPServer(app)
		server.bind(options.port)
		server.start(options.procnum)
		detlog.info('[SERVICE START] [%s] server start, listen on %d' % (options.service, options.port))
		tornado.ioloop.IOLoop.instance().start()
	except Exception, e:
		exclog.error("[SERVICE START] [%s] ERROR\n%s" % (options.service, traceback.format_exc(e)))

if __name__ == "__main__":
	main()
