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


class ChatENHandler(FutureHandler):
	def initialize(self, conf, schedules, cache, session_manager):
		super(ChatENHandler, self).initialize(conf, schedules, cache, session_manager)


	@tornado.gen.coroutine
	def trans(self, query_list, timeout, src, tar):
		data = {
			"uuid":"the_uuid_123456",
			"from_lang":src,
			"to_lang":tar,
			#"callback":"cb_func",
			#"model":"title_sum",
			"trans_frag":[{"id":"doc1","text":q.encode("utf-8")} for q in query_list]
		}

		params = json.dumps(data)
		req = tornado.httpclient.HTTPRequest(self._conf.TRANSLATE_URL, method="POST", headers=None, body=params)
		http_client = tornado.httpclient.AsyncHTTPClient(force_instance=True,
							defaults=dict(request_timeout=timeout,connect_timeout=timeout))
		res = yield http_client.fetch(req)
		res_list = []
		#if res.body.find("cb_func(") != -1:
		#res_str = res.body[8:-1]
		res = json.loads(res.body)
		for each in res["trans_result"]:
			if each["success"] == True:
				res_list.append(each["trans_text"])
			else:
				res_list.append(None)
				detlog.warning("[chaten] [WARNING] translate not successful query:%s" % str(each))
		#else:
		#	exclog.error("\n[chaten] [ERROR] returned data doesn't have 'cb_func' ahead")
		#	res_list = ""
		raise gen.Return(res_list)


	@tornado.web.asynchronous
	@tornado.gen.coroutine
	def get(self):
		try:
			detlog.info('\n\n************************* new conversation begin *************************')
			detlog.info('[chatbot] [BEGIN] [REQUEST] [%s]' % (self.request.uri))
			self.query = query = self.get_argument('query', None)
			self.source = source = "chaten"
			self.uid = uid = self.get_argument('uid', None)
			self.debug = "1"

			# translate to ch
			detlog.info("[chaten] translate en2ch...")
			ch_querys = yield self.trans([query], 1, "en", "zh-CHS")

			ch_query, acc_params = self.preproc(ch_querys[0], source, uid)
			detlog.info("[chaten] do chat...")
			results = yield self.do_chat(ch_query, source, uid, acc_params)
			results =  filter(lambda x:x["answer"]!=None, results)
			detlog.info("[chaten] translate all res to en...")
			res_strs = yield self.trans([each["answer"] for each in results], 1, "zh-CHS", "en")
			detlog.info("[chaten] [TRANSLATE] %s --> %s" % (query.encode("utf-8"), ch_querys[0].encode("utf-8")))
			en_results = []
			for i, each in enumerate(results):
				if res_strs[i]:
					detlog.info("[chaten] [TRANSLATE BACK] %d:%s --> %s " % (i, each["answer"], res_strs[i]))
					each["debug_info"]["trans_en2cn"] = "%s --> %s" % (query.encode("utf-8"), ch_querys[0].encode("utf-8"))
					each["debug_info"]["trans_cn2en"] = "%s --> %s " % (each["answer"], res_strs[i])
					each["answer"] = res_strs[i]
					en_results.append(each)
			results = self.form_response(en_results)
		except Exception, e:
			exclog.info("\n%s" % traceback.format_exc(e))
			results = {}
		self.write(results)
		self.finish()


def make_app(global_conf, schedules, cache, session_manager):
	favicon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../favicon.ico')
	
	app = tornado.web.Application(
		[
			(r'/', ChatENHandler, dict(conf=global_conf, schedules=schedules, cache=cache, session_manager=session_manager)),
			(r'/(favicon.ico)', tornado.web.StaticFileHandler, {"path": favicon_path}),
		]
	)
	return app
