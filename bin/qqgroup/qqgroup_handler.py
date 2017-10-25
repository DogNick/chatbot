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
from emoji_tool import clean_emoji_in_query

from chathub import FutureHandler
from schedules import *


detlog = logging.getLogger("details")
exclog = logging.getLogger("exception")
onlinelog = logging.getLogger('online')


def segment_data(text):
	s = 0
	content = []
	for each in re.finditer("\[(.+?)\]", text):
		if s < each.start():
			content.append({"type":0, "data": text[s:each.start()].encode("utf-8")})
		content.append({"type":4, "data": each.group(1).encode("utf-8")})
		s = each.end()
	if s != len(text):
		content.append({"type":0, "data": text[s:].encode("utf-8")})
	return content

class QQGroupHandler(FutureHandler):

	def initialize(self, conf, schedules, cache, session_manager):
		super(QQGroupHandler, self).initialize(conf, schedules, cache, session_manager)


	@tornado.web.asynchronous
	@tornado.gen.coroutine
	def post(self):
		detlog.info("\n\n************************* new conversation begin *************************")
		detlog.info("[qqgroup] [BEGIN] [REQUEST] [%s]" % (self.request.uri))
		# Info from QQ group
		self.ts = self.get_query_argument('ts', None)
		self.sig = self.get_query_argument('sig', None)

		data = json.loads(self.request.body)
		self.senderNickname = data.get('senderNickname', None)
		self.account = self.get_argument('account', None)

		## Vital thing

		# get content
		self.query = ""
		self.towhom = None
		self.pic_id = None
		self.silk_id = None
		self.face = None

		has_at = False # can only @ none-bot members
		has_voice = False
		has_gift = False
		has_unknown_type = False
		# I just concatenate the text and face back to the query
		for each in data["content"]:
			if each["type"] == 0: # text
				self.query += each["data"]
			elif each["type"] == 1: # @
				has_at = True
			elif each["type"] == 3: # voice
				has_voice = True
			elif each["type"] == 4: # system face
				self.query += '[' + each["data"] + ']'
			elif each["type"] == 7: # GIFT
				has_gift = True
			else:
				has_unknown_type = True

		REQUEST_ID = uuid.uuid1()
		onlinelog.info("[#USR#][UUID:%s][timestamp:%s][groupid=%s][uid=%s][query=%s][data=%s]" % (
							REQUEST_ID,
							time.time(),
							data["groupId"].encode("utf-8"),
							data["senderId"].encode("utf-8"),
							self.query.encode("utf-8").replace("\n", " ").replace("\t", " "),
							json.dumps(data["content"], ensure_ascii=False)))

		self.write("")
		self.finish()

		self.query = self.query.strip()

		# begin to respond
		_msg = {
			"receiverId": data["senderId"],
			"groupId": data["groupId"],
			"content":[],
			"masterId": data["masterId"],
			"msgId": data["msgId"],
			"timestamp": data["timestamp"]
		}
		params = []
		self.source = source = "qqgroup"
		self.uid = uid = data["senderId"]

		self.debug = "0"
		self.magic = ""
		schedule = SCHEDULES[self.source]
		self.from_lang = self.get_query_argument('from_lang', 'zh')
		callback_timeout = schedule["callback_timeout"]

		is_emoji_query, emoji_reply, cleaned_query = clean_emoji_in_query(self.query, 'QQ')
		self.query = query = cleaned_query

		if is_emoji_query:
			_msg["content"] = segment_data(emoji_reply)
			from_utf8 = "emoji_reply"
		else:
			# collect infos for current request

			#set timeout
			if has_at and self.query == "":
				_msg["content"].append({"type":0, "data":random.choice(default_ATWANGZAI_QUERY_answer_list)})
				from_utf8 = "default_for_atwangzai_query"
			elif has_voice:
				_msg["content"].append({"type":0, "data":random.choice(default_VOICE_QUERY_answer_list)})
				from_utf8 = "default_for_voice_query"
			elif has_gift:
				_msg["content"].append({"type":0, "data":random.choice(default_GIFT_QUERY_answer_list)})
				from_utf8 = "default_for_gift_query"
			elif self.query == "" and has_unknown_type:
				_msg["content"].append({"type":0, "data":random.choice(default_answer_list)})
				from_utf8 = "default_for_unknown_query"
			elif self.query == "":
				_msg["content"].append({"type":0, "data":random.choice(default_EMPTY_QUERY_answer_list)})
				from_utf8 = "default_for_empty_query"
			elif self.query.find('我在这里，点击查看') == 0:
				_msg["content"].append({"type":0, "data":random.choice(default_SHARELOCATION_QUERY_answer_list)})
				from_utf8 = "default_for_location_query"
			elif self.query.find('[[应用]音乐]') == 0:
				_msg["content"].append({"type":0, "data":random.choice(default_SHAREMUSIC_QUERY_answer_list)})
				from_utf8 = "default_for_sharemusic_query"
			elif self.query.find('[[应用]自选股]') == 0:
				_msg["content"].append({"type":0, "data":random.choice(default_SHARESTOCK_QUERY_answer_list)})
				from_utf8 = "default_for_sharestock_query"
			else:
				query, acc_params = self.preproc(query, source, uid)
				acc_params["groupid"] = data["groupId"]
				acc_params["eid"] = uid
				results = yield self.do_chat(query, source, uid, acc_params)

				result = random.choice(results)

				# segment_data typically for some emoji
				_msg["content"] = segment_data(result["answer"])
				from_utf8 = result["debug_info"]["from"].encode("utf-8")

		params.append(_msg)
		appid = "101356192"
		appkey = "aa353cabd594235a9b30d866f5283610"

		m = hashlib.md5()
		m.update(json.dumps(params) + appid + appkey + self.ts)
		sig = m.hexdigest()
		url = self._conf.QQ_CALLBACK_URL + "?ts=%s&sig=%s&appid=%s" % (self.ts, sig, appid)
		req = tornado.httpclient.HTTPRequest(url, method="POST", headers={"Content-Type":"application/json,text/json"}, body=json.dumps(params))
		http_client = tornado.httpclient.AsyncHTTPClient(force_instance=True, defaults=dict(request_timeout=callback_timeout, connect_timeout=callback_timeout))
		res = yield http_client.fetch(req)

		# only log content[0] is enough
		onlinelog.info("[#BOT#][UUID:%s][timestamp:%s][groupid=%s][uid=%s][answer=%s][from=%s]" % (
							REQUEST_ID,
							time.time(),
							data["groupId"].encode("utf-8"),
							data["senderId"].encode("utf-8"),
							_msg["content"][0]["data"].replace("\n", " ").replace("\t", " "),
							from_utf8))

		onlinelog.info("[#ANALYSE-VERBOSE#][UUID:%s][timestamp:%s][time:%s][groupid=%s][uid=%s][query=%s][data=%s][answer=%s][from=%s]" % (
							REQUEST_ID,
							time.time(),
							time.strftime('%H:%M:%S'),
							data["groupId"].encode("utf-8"),
							data["senderId"].encode("utf-8"),
							self.query.encode("utf-8").replace("\n", " ").replace("\t", " "),
							json.dumps(data["content"], ensure_ascii=False),
							_msg["content"][0]["data"].replace("\n", " ").replace("\t", " "),
							from_utf8))

		raise gen.Return(res)


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
					if should_cache:
						for j in range(i):
							if acc_status[j] == "timeout":
								should_cache = False
								break
					done = True
					break
			if done:
				break
		if len(ret) == 0:
			debug_info = {"err":"use_default", "from":"default"}
			ret.append({"answer":random.choice(default_answer_list), "debug_info":debug_info})
			should_cache = False
		# Need more condideration here
		return ret, should_cache


	@tornado.web.asynchronous
	@tornado.gen.coroutine
	def get(self):
		try:
			self.query = query = self.get_argument('query', None)
			self.source = source = self.get_argument('source', None)
			self.uid = uid = self.get_argument('uid', None)
			self.debug = "0"
			query, acc_params = self.preproc(query, source, uid)
			acc_params["eid"] = self.uid
			acc_params["groupid"] = "12345"
			results = yield self.do_chat(query, source, uid, acc_params)
			results = self.form_response(results)
		except Exception, e:
			exclog.error("\n%s" % traceback.format_exc(e))
			results = "{}"
		self.write(results)
		self.finish()


def make_app(global_conf, schedules, cache, session_manager):
	favicon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../favicon.ico')
	app = tornado.web.Application(
		[
			(r'/', QQGroupHandler, dict(conf=global_conf, schedules=schedules, cache=cache, session_manager=session_manager)),
			(r'/(favicon.ico)', tornado.web.StaticFileHandler, {"path": favicon_path}),
		]
	)
	return app
