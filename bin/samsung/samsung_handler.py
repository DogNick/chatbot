#coding=utf-8
import os
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "common"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../lib"))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../"))

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
from emoji_tool import clean_emoji_in_query

from chathub import FutureHandler
from schedules import *
from common_method import *


detlog = logging.getLogger("details")
exclog = logging.getLogger("exception")
onlinelog = logging.getLogger("online")


default_ret = """<?xml version="1.0" encoding="utf-8"?>
<DOCUMENT expireTime="%s">%s</DOCUMENT>
"""

each_doc = """
<doc><item type="15" entitytype="1|1" pvtype="15_300_4" vrid="50022401">
<display type="2">
<answerinfo>
<short_answer><![CDATA[]]></short_answer>
<answer><![CDATA[%s]]></answer>
<url><![CDATA[%s]]></url>
<title><![CDATA[%s]]></title>
<modify_time>2017-08-24</modify_time>
<img_url><![CDATA[]]></img_url>
<source_img><![CDATA[]]></source_img>
<showurl><![CDATA[m.sogou.com]]></showurl>
<question_title></question_title>
<title_flag></title_flag>
<debug_answer_type><![CDATA[%s]]></debug_answer_type>
<answer_subtype><![CDATA[%s]]></answer_subtype>%s
</answerinfo>
</display>
</item></doc>
"""

calculate_doc = """
<math_exp><![CDATA[%s]]></math_exp>"""

sun_doc = """
<city_name><![CDATA[%s]]></city_name>
<event_type><![CDATA[%s]]></event_type>
<event_time><![CDATA[%s]]></event_time>"""

time_doc = """
<city_name><![CDATA[%s]]></city_name>
<time_zone><![CDATA[%s]]></time_zone>
<coordinate><![CDATA[%s]]></coordinate>
"""

class SamsungHandler(FutureHandler):

	def initialize(self, conf, schedules, cache, session_manager):
		super(SamsungHandler, self).initialize(conf, schedules, cache, session_manager)


	@tornado.web.asynchronous
	@tornado.gen.coroutine
	def post(self):
		detlog.info("\n\n************************* new conversation begin *************************")
		detlog.info("[samsung] [BEGIN] [REQUEST] [%s]" % (self.request.uri))
		b1 = time.time()
		debug = self.debug = "0"
		uid = self.uid = None
		query = self.query = None
		source = self.source = None
		try:
			params = self.request.body.split("&")
			for each in params:
				if each.find("query=") == 0:
					query = self.query = urllib.unquote_plus(get_between(each, "query=", "")).decode("utf-16")
				elif each.find("uid=") != -1:
					uid = self.uid = urllib.unquote_plus(get_between(each, "uid=", "")).decode("utf-16")
				elif each.find("source=") != -1:
					source = self.source = urllib.unquote_plus(get_between(each, "source=", "")).decode("utf-16")
			detlog.info(">>>>>>>>uid:" + str(self.uid))
			detlog.info(">>>>>>>>source:" + self.source)
			detlog.info(">>>>>>>>query:" + str(self.query).encode("utf-8"))

			valid, info = self.checkInfoValid()
			if not valid:
				result_xml = default_ret % ("600000", info)
				onlinelog.info(self.log_str_online(result_xml, b1))
				self.write(result_xml)
				self.finish()
				return
			query, acc_params = self.preproc(self.query.decode("utf-8"), self.source, self.uid)
			results = yield self.do_chat(query, source, uid, acc_params)
			result_xml = self.form_response(results)

		except Exception, e:
			result_xml = default_ret % ("600000", "Internal Error")
			exclog.error("[request_body=%s]\n%s" % (str(self.request.body).replace("\n", ""), traceback.format_exc(e)))

		onlinelog.info(self.log_str_online(result_xml, b1))
		self.write(result_xml)
		self.finish()


	def select_results(self, acc_results, acc_status):
		ret = []
		should_cache = False
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
		return ret, should_cache


	#samsung答案格式
	def form_response(self, results, status="ok"):
		result_str = ""
		if len(results) == 0:
			result_str = default_ret % ("600000", "")
		else:
			url = ""
			title = ""
			_from = ""
			sub_type = ""
			answer = results[0]["answer"].encode("utf-8")
			if "url" in results[0]["debug_info"]:
				url = results[0]["debug_info"]["url"]
			else:
				url = "http://m.sogou.com"
			if "title" in results[0]["debug_info"]:
				title = results[0]["debug_info"]["title"].encode("utf-8")
			else:
				title = self.query.encode("utf-8")
			_from = results[0]["debug_info"]["from"].encode("utf-8")
			if "sub_type" in results[0]["debug_info"]:
				sub_type = results[0]["debug_info"]["sub_type"]
			if _from == "universal_time":
				city = ""
				time_zone = ""
				coordinate = ""
				if "place" in results[0]["debug_info"]:
					city = results[0]["debug_info"]["place"]
				if "time_zone" in results[0]["debug_info"]:
					time_zone = results[0]["debug_info"]["time_zone"]
				if "coordinate" in results[0]["debug_info"]:
					coordinate = results[0]["debug_info"]["coordinate"]
				result_str = default_ret % ("-1", each_doc % (answer, url, title, _from, sub_type, time_doc % (city, time_zone, coordinate)))
			elif sub_type == u"计算器":
				math_exp = ""
				sub_type = "calculator"
				if "math_exp" in results[0]["debug_info"]:
					math_exp = results[0]["debug_info"]["math_exp"]
				result_str = default_ret % ("600000", each_doc % (answer, url, title, _from, sub_type, calculate_doc % math_exp))
			elif sub_type == u"日出日落":
				city = ""
				event_type = ""
				event_time = ""
				sub_type = "sunrise_sunset"
				if "city" in results[0]["debug_info"]:
					city = results[0]["debug_info"]["city"]
				if "sunrise_time" in results[0]["debug_info"]:
					event_type = u"日出"
					event_time = results[0]["debug_info"]["sunrise_time"]
				elif "sunset_time" in results[0]["debug_info"]:
					event_type = u"日落"
					event_time = results[0]["debug_info"]["sunset_time"]
				result_str = default_ret % ("600000", each_doc % (answer, url, title, _from, sub_type, sun_doc % (city, event_type, event_time)))
			else:
				result_str = default_ret % ("600000", each_doc % (answer, url, title, _from, sub_type, ""))
		return result_str


	def log_str_online(self, result_xml, query_time):
		try:
			cost_time_str = str(int((time.time() - query_time)*1000))
			log_str = "\n[INFO] [%s] [timestamp=%s] [uid=%s] " % (time.strftime("%Y-%m-%d %H:%M:%S"), str(time.time()), str(self.uid))
			log_str += "[url=%s] [body=%s] [response=%s] [Sogou-Observer, cost=%s, source=%s, debug=%s, ip=%s, Owner=OP]\n" % (
					self.request.uri,
					str(self.request.body).replace("\n", ""),
					str(result_xml).replace("\n", ""),
					cost_time_str,
					self.source.encode("utf-8"),
					self.debug.encode("utf-8"),
					self.request.remote_ip
			)
		except Exception, e:
			log_str = "[INFO] [some error]"
			exclog.error("%s" % (traceback.format_exc(e)))
		return log_str


def make_app(global_conf, schedules, cache, session_manager):
	app = tornado.web.Application(
		[
			(r"/", SamsungHandler, dict(conf=global_conf, schedules=schedules, cache=cache, session_manager=session_manager)),
		]
	)
	return app
