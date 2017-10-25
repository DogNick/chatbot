#coding=utf-8
import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'common'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../lib'))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../'))

import hashlib
import logging

import gc
import re
import pdb
import json
import time
import copy
import redis
import urllib
import uuid
import random
import traceback

from tornado import gen, locks
import tornado.httpserver
import tornado.httpclient
import tornado.ioloop
import tornado.web
import tornado.gen

from chathub import FutureHandler
from schedules import *
from preprocessing import *


detlog = logging.getLogger("details")
exclog = logging.getLogger("exception")
onlinelog = logging.getLogger('online')


class TsinghuaRobotHandler(FutureHandler):

	def initialize(self, conf, schedules, cache, session_manager):
		super(TsinghuaRobotHandler, self).initialize(conf, schedules, cache, session_manager)

	def preproc(self, query, source, uid, types=''):
		# 纠正汪仔的名字
		self.c_query = get_query_correction(query, source, types)
		self.r_query = self.c_query
		acc_params = preprocessing(self.r_query, source, self.request.remote_ip, uid)
		return self.r_query, acc_params


	@tornado.web.asynchronous
	@tornado.gen.coroutine
	def get(self):
		t1 = time.time()
		detlog.info("\n\n************************* new conversation begin *************************")
		detlog.info("[tsinghua_robot] [BEGIN] [REQUEST] [%s]" % (self.request.uri))
		try:
			self.query = query = self.get_argument('query', None)
			self.source = source = self.get_argument('source', None)
			self.uid = uid = self.get_argument('uid', None)
			self.debug = self.get_argument('debug', '0')
			self.querytype = self.get_argument('querytype', None)
			self.referer_info = str(self.request.headers.get('Referer'))
			# 检测是否是从小程序发来的请求
			if self.referer_info.find('https://servicewechat.com/wx99d16f4f652f644d') == -1:
				results = {'code':-1, 'status':'Illegal request'}
				onlinelog.info(self.log_str_online(results, t1))
				self.finish()
				return
			valid, info = self.checkInfoValid()
			if not valid:
				results = {'code':-1, 'status':'parameter problem'}
				onlinelog.info(self.log_str_online(results, t1))
				self.write(results)
				self.finish()
				return
			query, acc_params = self.preproc(query, source, uid, self.querytype)
			acc_params['tsinghua_querytype'] = self.querytype
			results = yield self.do_chat(query, source, uid, acc_params)
			results = self.form_response(results)
		except Exception, e:
			results = {'code':-1, 'status':'internal error'}
			exclog.error("[query=%s] [uid=%s]\n%s" % (self.query.encode('utf-8'), self.uid, traceback.format_exc(e)))
		onlinelog.info(self.log_str_online(results, t1))
		if self.debug == '0' and 'debug_info' in results:
			del results['debug_info']
		self.write(results)
		self.finish()


	def select_results(self, acc_results, acc_status):
		ret = []
		should_cache = True
		done = False
		for result_list in acc_results:
			if not result_list:
				continue
			for res in result_list:
				if res["answer"]:
					answer = res["answer"]
					debug_info = res["debug_info"]
					ret.append({"answer":answer, "debug_info":debug_info})
					done = True
					break
			if done:
				break
		if len(ret) == 0:
			debug_info = {"err":"use_default", "from":"default"}
			ret.append({"answer":random.choice(default_answer_list), "debug_info":debug_info})
			should_cache = False
		return ret, should_cache


	#tsinghua_robot答案格式
	def form_response(self, results, status="ok"):
		ret = {}
		if len(results) == 0:
			ret["code"] = -1
		else:
			ret["code"] = 0
			for each in results:
				ret["msg"] = each["answer"]
				ret["from"] = each["debug_info"]["from"]
				if each["debug_info"]["from"] == "tsinghua_qa" and each["answer"] == "read_file":
					ret["msg"] = ""
				if "card" in each["debug_info"]:
					ret["card"] = each["debug_info"]["card"]
				if self.debug == '1':
					ret["debug_info"] = each["debug_info"]
				break
		return ret


	def log_str_online(self, results, query_time):
		try:
			cost_time_str = str(int((time.time() - query_time)*1000))
			log_str = '\n[INFO] [%s] [timestamp=%s] [uid=%s] ' % (time.strftime('%Y-%m-%d %H:%M:%S'), str(time.time()), self.uid)
			log_str += '[Sogou-Observer, cost=%s, source=%s, query=%s, result=%s, debug=%s, Owner=OP]\n' % (
					cost_time_str,
					self.source.encode("utf-8"),
					self.query.encode("utf-8"),
					json.dumps(results, ensure_ascii=False),
					self.debug.encode("utf-8")
			)
		except Exception, e:
			log_str = "[INFO] [some error]"
			exclog.error("%s" % (traceback.format_exc(e)))
		return log_str


def make_app(global_conf, schedules, cache, session_manager):
	app = tornado.web.Application(
		[
			(r'/', TsinghuaRobotHandler, dict(conf=global_conf, schedules=schedules, cache=cache, session_manager=session_manager)),
		]
	)
	return app
