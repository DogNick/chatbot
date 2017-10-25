#!/usr/bin/env python
#coding=utf8

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'common'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../lib'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'conf'))

import hashlib
import logging

import re
import json
import time
import random
import traceback
import urllib

from lxml import etree as ET
from lxml.etree import CDATA
from tornado.locks import Event
from tornado import gen, locks, web
import tornado

from preprocessing import *
from intervene import get_whitelist, get_blacklist, cache, SessionManager, DEFAULT_CONTEXT

reload(sys)
sys.setdefaultencoding('utf-8')

detlog = logging.getLogger("details")
exclog = logging.getLogger("exception")
onlinelog = logging.getLogger("online")


class FutureHandler(web.RequestHandler):

	def initialize(self, conf, schedules, cache, session_manager):
		self._cache = cache
		self._session_manager = session_manager
		self._conf = conf
		self._schedules = schedules

	def set_default_headers(self):
		self.set_header('Access-Control-Allow-Origin', "*")


	def checkInfoValid(self):
		"""check vital params interface.

		Do some check and return some info
		Args:
		Returns:
		Raises:
		"""
		if not self.uid or not self.query:
			return False, "missing params, need uid and query"
		return True, None


	def preproc(self, query, source, uid):
		"""preprocess interface.

		Do some basic preproc things, here use preprocessing in common
		may be overwrite by any subclass

		Args:
		Returns:
		Raises:
		"""
		self.c_query = get_query_correction(query, source)		#纠正汪仔的名字
		self.r_query = self.c_query
		acc_params = preprocessing(self.r_query, source, self.request.remote_ip, uid)
		return self.r_query, acc_params

	@gen.coroutine
	def check_intent(self, disabled):
		try:
			url = self._conf.INTENT_SERVER_URL + "/intent?query=" + urllib.quote_plus(self.r_query.encode("utf-8"))
			req = tornado.httpclient.HTTPRequest(url, method='GET')
			http_client = tornado.httpclient.AsyncHTTPClient(force_instance=True,
				defaults=dict(request_timeout=1000,connect_timeout=1000))
			resp = yield http_client.fetch(req)
			detlog.info("[check_intent] [query=%s] [intent=%s]" % (self.query.encode('utf-8'), resp.body))
			resp = json.loads(resp.body)
			if resp["result"][0]["tags"] == "0":
				disabled["accessor.parse_web_search"] = 1
				disabled["accessor.parse_yaoting"] = 1
		except Exception, e:
			exclog.error("[query=%s]\n%s" % (self.r_query.encode("utf-8"), traceback.format_exc(e)))


	@gen.coroutine
	def _accParallelAsync(self, acc_tuples, acc_params):
		"""Call group accs in parallel asynchronously with judge_method

		Call all accs in one group in parallel, and wait until the judgemthod
		return True

		Args:
			acc_tuple_list: a list of tuples of (acc_fun, judgemethod, timeout)
		Returns:
			acc_results: results of all accs in this acc_tuples
			acc_status: status of execution of all accs in this acc_tuples
		Raises:
		"""
		disabled = acc_params["disabled"]
		acc_results = [None] * len(acc_tuples)
		acc_status = [None] * len(acc_tuples)
		acc_finished = []
		self.evt = Event()
		self.lock = locks.Lock()
		for acc_id, acc_tuple in enumerate(acc_tuples):
			acc, judge_method, timeout = acc_tuple
			if acc.acc_name in disabled:
				acc_results[acc_id] = [{"answer":None, "debug_info":{"No result": "downstream disabled"}}]
				acc_status[acc_id] = "disabled"
			else:
				detlog.debug("=====[DEBUG]===== Create acc gen.Task: %d, %s..." % (acc_id, acc_tuples[acc_id][0].acc_name))
				gen.Task(self._request_downstream, acc_id, acc_tuples, acc_params, acc_results, acc_finished, acc_status, judge_method, timeout)
		detlog.debug("=====[DEBUG]===== Waiting for finish evt...")
		yield self.evt.wait()
		detlog.debug("=====[DEBUG]===== Evt set, acc_tuples finished")
		raise gen.Return((acc_results, acc_status))


	@gen.coroutine
	def _request_downstream(self, acc_id, acc_tuples, acc_params, acc_results, acc_finished, acc_status, JudgeMethod, timeout):
		"""Call one acc asynchronously with a judgemethod to stop

		This will make async http request to one downstream ,catch exceptions and judge whether to
		stop other accs in the same group using JudgeMethod

		Args:
		Returns
		"""
		log_str = ''
		begin = time.time()
		try:
			acc = acc_tuples[acc_id][0]
			log_str = "[downstream] [acc_name=%s]" % acc.acc_name
			result_tuple_list = yield acc.run(self.r_query, acc_params)
			result_list = [{"answer":tpl[0], "debug_info":tpl[1]} for tpl in result_tuple_list]
			with(yield self.lock.acquire()):
				acc_results[acc_id] = result_list
				acc_status[acc_id] = "done"
				acc_finished.append(result_list)
				log_str += " [acc_result=True]"
		except Exception, e:
			exclog.error("[acc_name=%s]\n%s" % (acc.acc_name, traceback.format_exc(e)))
			with(yield self.lock.acquire()):
				acc_results[acc_id] = [{"answer":None, "debug_info":{"from":acc.acc_name, "err":str(e)}}]
				acc_status[acc_id] = "timeout"
				log_str += " [acc_result=False]"
		finally:
			detlog.debug("=====[DEBUG]===== Finally begin acc: %d,%s" % (acc_id, acc_tuples[acc_id][1].__name__))
			cost_time_str = str(int((time.time() - begin)*1000))
			log_str += " [raw_cost=%s] [begin_JudgeMethod=%s]" % (cost_time_str, acc_tuples[acc_id][1].__name__)
			detlog.info(log_str)
			detlog.debug("=====[DEBUG]===== Finally JudgeMethod acc: %d,%s" % (acc_id, acc_tuples[acc_id][1].__name__))
			should_return = JudgeMethod(acc_results, acc_finished, acc_tuples, acc_id, acc.acc_name)
			detlog.debug("=====[DEBUG]===== Finally should return: %s, acc: %d, %s" % (should_return, acc_id, acc.acc_name))
			if not self.evt.is_set() and should_return:
				detlog.info("[downstream_return] [acc_name=%s] " % (acc.acc_name))
				self.evt.set()


	@gen.coroutine
	def strategy(self, acc_tuples, acc_params):
		"""Main strategy to handle accessors

		This strategy will make asynchronous request in parallel to accs with defined strategy.
		As default strategy, it will query all the accs depending on it's timeout and judgemethod

		Args:
			acc_tuples: it's a list of accessor tuple like:
				[
					(acc1, JudgeMethod_1, timeout),
					(acc2, JudgeMethod_3, timeout),
				]
		Returns:
			acc_results: list as before
			acc_status: list of execution status of the same length with acc_results
		"""
		# default strategy, simply query all accs
		results, status = yield self._accParallelAsync(acc_tuples, acc_params)
		self.acc_results = results
		self.accessors = acc_tuples
		raise gen.Return((results, status))


	@gen.coroutine
	def do_chat(self, query, source, uid, acc_params={}):
		"""Handle main tornado requests.

		Finish most things here, including blacklist, whitelist, cache,
		user session record, and various schedules or strategies

		Args:
		Returns:
		Raises:
		"""
		query_time = t1 = time.time()
		# to retrieve info from service-specific schedule
		schedule = self._schedules.schedule(source)

		# Get user context
		if schedule.use_session_manager:
			user_context = self._session_manager.get(uid)
		else:
			user_context = DEFAULT_CONTEXT
		acc_params["context"] = user_context

		disabled = acc_params.get("disabled", {})
		if schedule.use_intent:
			# do maybe more...
			yield self.check_intent(disabled)
		acc_params["disabled"] = disabled
		if self._conf._verbose:
			detlog.info('[do_chat] [query=%s] [acc_params=%s]' % (query.encode('utf-8'), json.dumps(acc_params, ensure_ascii=False)))

		# Check Blacklist first
		if schedule.use_blacklist:
			results = get_blacklist(query, source, acc_params)
			ret_str, info = results[0]
			if ret_str:
				results = [{"answer":ret_str, "debug_info":info}]
				detlog.info(self.log_str_selected(results, query_time))
				if schedule.use_session_manager:
					self._session_manager.add(uid, query, t1, results[0], time.time())
				raise gen.Return(results)

		# Check Whitelist
		if schedule.use_whitelist:
			results = get_whitelist(query, source, acc_params)
			ret_str, info = results[0]
			if ret_str:
				results = [{"answer":ret_str, "debug_info":info}]
				detlog.info(self.log_str_selected(results, query_time))
				if schedule.use_session_manager:
					self._session_manager.add(uid, query, t1, results[0], time.time())
				raise gen.Return(results)

		# Check the cache, if cache is used
		if schedule.use_cache:
			obj, cached = self._cache.get(query)
			if cached:
				detlog.info("[cache] [get] [query=%s] [cached=%s]" % (query, str(cached)))
				detlog.info(self.log_str_selected(obj, query_time))
				if schedule.use_session_manager:
					self._session_manager.add(uid, query, t1, obj[0], time.time())
				raise gen.Return(obj)

		# do accessors
		results, status = yield self.strategy(schedule.acc_tuples, acc_params)

		# Select
		selected, should_cache = self.select_results(results, status)

		detlog.info(self.log_str_accs(selected, query_time))
		detlog.info(self.log_str_selected(selected, query_time))

		# Cache if needed
		if schedule.use_cache and should_cache and not cached:
			self._cache.put(query, selected, selected[0]["debug_info"]["from"])
			detlog.info("[cache] [put] [query=%s] [cached_from=%s]" % (query, selected[0]["debug_info"]["from"]))

		# Add session
		if schedule.use_session_manager:
			self._session_manager.add(uid, query, query_time, selected[0], time.time(), acc_params["context"])

		raise gen.Return(selected)


	#yaoting下游返回结果时，处理问答优先级
	def select_qa_results(self, index, acc_results, level=6):
		qa = []
		yaoting = []			#暂时存放yaoting下游结果
		for i in range(index, index+2):
			if not acc_results[i]:
				continue
			for res in acc_results[i]:
				answer = res["answer"]
				debug_info = res["debug_info"]
				if debug_info['from'] == 'web_search':
					#yaoting未出结果或者web_search结果质量较高时，优先出web_search结果，否则出姚婷结果
					if len(yaoting) == 0 or ('level' in debug_info and debug_info['level'] <= level):
						qa.append({"answer":answer, "debug_info":debug_info})
					else:
						qa = yaoting
						break
				else:
					yaoting.append({"answer":answer, "debug_info":debug_info})
			if len(qa) != 0:
				break
		if len(qa) == 0 and len(yaoting) != 0:
			qa = yaoting
		return index+1, qa

	
	def select_results(self, acc_results, acc_status):
		need_cache = False
		ret = []
		for result_list in acc_results:
			if not result_list:
				continue
			for res in result_list:
				ret.append({"answer":res["answer"], "debug_info":res["debug_info"]})
		return ret, need_cache


	def form_response(self, results, status="ok"):
		ret = {}
		ret["status"] = status
		if not results:
			return json.dumps(ret, ensure_ascii=False).encode('utf8')
		ret["result"] = []
		for each in results:
			res = {"answer":each["answer"]}
			if self.debug == '1':
				res["debug_info"] = each["debug_info"]
			ret["result"].append(res)
		result_str = json.dumps(ret, ensure_ascii=False).encode('utf8')
		return result_str


	#accessors result
	def log_str_accs(self, results, query_time):
		cost_time_str = str(int((time.time() - query_time)*1000))
		acc_res_str = ""
		acc_debug_str = ""
		for acc_id, acc_tuple in enumerate(self.accessors):
			if not self.acc_results[acc_id]:
				acc_res_str += "\n%s(0)  NOT RETURNED" % acc_tuple[0].acc_name
				acc_debug_str += "\n%s(0)  NOT RETURNED" % acc_tuple[0].acc_name
			else:
				for idx, res in enumerate(self.acc_results[acc_id]):
					ans_str = res["answer"].replace("\n", "").encode("utf-8") if res["answer"] else "None"
					debug_str = res["debug_info"]
					acc_res_str += "\n%s(%d)  %s" % (acc_tuple[0].acc_name, idx, ans_str)
					acc_debug_str += "\n%s(%d)  %s" % (acc_tuple[0].acc_name, idx, json.dumps(debug_str, ensure_ascii=False))
		log_str = "\n========================================"
		log_str += "%s\n----------------------------------------" % acc_res_str
		log_str += "%s\n========================================" % acc_debug_str
		for each in results:
			log_str += "\n%s %s" % (each["debug_info"]["from"].encode("utf-8"), str(each["answer"]).replace('\n', '').encode("utf-8"))
		log_str += "\ncost: %s\n" % cost_time_str
		return log_str


	# selected result
	def log_str_selected(self, results, query_time):
		cost_time_str = str(int((time.time() - query_time)*1000))
		log_str = "[SELECTED_INFO] [timestamp=%s] [uid=%s] " % (str(time.time()), str(self.uid).encode("utf-8"))
		log_str += "[cost=%s, source=%s, query=%s, c_query=%s, r_query=%s, result=%s, debug=%s, ip=%s]\n" % (
				cost_time_str,
				self.source.encode("utf-8"),
				self.query.encode("utf-8"),
				self.c_query.encode("utf-8"),
				self.r_query.encode("utf-8"),
				json.dumps(results, ensure_ascii=False),
				self.debug.encode("utf-8"),
				self.request.remote_ip
		)
		return log_str


	# online log, use in each handler
	def log_str_online(self, results, query_time):
		try:
			cost_time_str = str(int((time.time() - query_time)*1000))
			log_str = "[INFO] [%s] [timestamp=%s] [uid=%s] " % (time.strftime('%Y-%m-%d %H:%M:%S'), str(time.time()), str(self.uid))
			log_str += "[Sogou-Observer, cost=%s, source=%s, query=%s, c_query=%s, r_query=%s, result=%s, debug=%s, ip=%s, Owner=OP]\n" % (
					cost_time_str,
					self.source.encode("utf-8"),
					self.query.encode("utf-8"),
					self.c_query.encode("utf-8"),
					self.r_query.encode("utf-8"),
					json.dumps(results, ensure_ascii=False).encode("utf8"),
					self.debug.encode("utf-8"),
					self.request.remote_ip
			)
		except Exception, e:
			log_str = "[INFO] [some error]"
			exclog.error("%s" % (traceback.format_exc(e)))
		return log_str
