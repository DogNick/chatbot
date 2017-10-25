#coding=utf-8

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'common'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../lib'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../'))

import hashlib
import logging

import gc
import re
import pdb
import json
import time
import copy
import urllib
import random
import traceback

from lxml import etree as ET
from lxml.etree import CDATA
from tornado.locks import Event
from tornado import gen, locks
import tornado.httpclient
import tornado.web
import tornado.gen
from tornado.options import options

from chathub import FutureHandler
from schedules import *
from preprocessing import *


detlog = logging.getLogger("details")
exclog = logging.getLogger("exception")
onlinelog = logging.getLogger('online')


class IntegratedHandler(FutureHandler):
	def initialize(self, conf, schedules, cache, session_manager):
		super(IntegratedHandler, self).initialize(conf, schedules, cache, session_manager)

	def preproc(self, query, source, uid, types=''):
		# 纠正汪仔的名字
		self.c_query = get_query_correction(query, source, types)
		self.r_query = self.c_query
		acc_params = preprocessing(self.r_query, source, self.request.remote_ip, uid)
		return self.r_query, acc_params


	@tornado.web.asynchronous
	@tornado.gen.coroutine
	def get(self):
		try:
			detlog.info('\n\n************************* new conversation begin *************************')
			detlog.info('[chatbot] [BEGIN] [REQUEST] [%s]' % (self.request.uri))
			#gc.disable()
			b1 = time.time()
			# collect vital infos
			self.query = query = self.get_query_argument('query', None)
			self.source = source = self.get_query_argument('source', options.source)
			self.uid = uid = self.get_query_argument('uid', None)

			# collect other infos
			self.debug = self.get_query_argument('debug', '0')

			# source = tsinghua_robot
			self.querytype = self.get_argument('querytype', None)

			# source = common_show yzdd_onsite show_medical
			self.from_lang = self.get_query_argument('from_lang', 'zh')
			self.robot_model = self.get_query_argument('robot_model', '1')

			# source = gd_mobile
			self.skillId = self.get_query_argument('skillId', None)

			# check info valid
			valid, info = self.checkInfoValid()
			if not valid:
				results = {'status':'ok', 'status_code':info}
				onlinelog.info(self.log_str_online(results, b1))
				result_str = json.dumps(results, ensure_ascii=False)
				self.write(result_str)
				self.finish()
				return

			# preprocess
			query, acc_params = self.preproc(query, source, uid, self.querytype)
			acc_params['tsinghua_querytype'] = self.querytype		#source=tsinghua_robot
			acc_params['robot_model'] = self.robot_model			#source用于机器人汪仔
			acc_params['skillId'] = self.skillId					#source=gd_mobile

			# handle requests
			results = yield self.do_chat(query, source, uid, acc_params)

			# form and clean response
			result_str = self.form_response(results)
		except Exception, e:
			exclog.error("\n%s" % traceback.format_exc(e))
			results = {'status':'ok', 'status_code':'Internal Server Error'}
			result_str = json.dumps(results, ensure_ascii=False)
		onlinelog.info(self.log_str_online(results, b1))

		# send
		self.write(result_str)
		self.finish()


	def xml_format(self, d):
		result = json.dumps(d, ensure_ascii=False).encode('utf8')
		json_result = json.loads(result)
		xml_result = ET.Element('result')
		total = ET.SubElement(xml_result, 'total')
		total.text = str(len(json_result['result']))
		ET.SubElement(xml_result, 'situation').text = CDATA('1')
		ET.SubElement(xml_result, 'key').text = CDATA(self.query)
		ET.SubElement(xml_result, 'type').text = u'100'
		items = ET.SubElement(xml_result, 'items')
		for res in json_result['result']:
			if res['answer'] and res['answer'].find('__qt__') == 0:
				whites = res['answer'][6:].split(';')
				total.text = str(len(whites))
				for white in whites:
					item = ET.SubElement(items, 'item')
					ET.SubElement(item, 'stype').text = CDATA('100')
					ET.SubElement(item, 'answer').text = CDATA(white)
				break
			elif res['answer']:
				item = ET.SubElement(items, 'item')
				ET.SubElement(item, 'stype').text = CDATA('100')
				ET.SubElement(item, 'answer').text = CDATA(res['answer'])
		xml_str = ET.tostring(xml_result, pretty_print=True, xml_declaration=True, encoding='utf-8')
		return xml_str


	def select_results(self, acc_results, acc_status):
		ret = []
		should_cache = False
		#### test ####
		if self.source == "board" or self.source == "test":
			for result_list in acc_results:
				if not result_list:
					continue
				for res in result_list:
					ret.append({"answer":res["answer"], "debug_info":res["debug_info"]})
		###### wenda ######
		elif self.source == "wenda":
			ret, should_cache = self.select_results_format(acc_results, acc_status)
		###### online ######
		###### internal service [test] ######
		elif self.source == "wechat" or self.source == "tsinghua_robot":
			ret, should_cache = self.select_results_format_default(acc_results, acc_status)
		elif self.source == "samsung":
			ret, should_cache = self.select_results_format(acc_results, acc_status)
		###### internal other product service ######
		elif self.source == "weimi":
			ret, should_cache = self.select_results_format_weimi(acc_results, acc_status)
		elif self.source == "gd_mobile":
			ret, should_cache = self.select_results_format_default(acc_results, acc_status)
		elif self.source.find("aiplatform") == 0:
			ret, should_cache = self.select_results_format_aiplatform(acc_results, acc_status)
		###### wangzai robot service ######
		elif self.source == "yzdd_onsite" or self.source == 'common_show':
			ret, should_cache = self.select_results_format_show(acc_results, acc_status)
		elif self.source == 'show_medical':
			ret, should_cache = self.select_results_format_medical(acc_results, acc_status)
		###### external service ######
		elif self.source == "qcloud":
			ret, should_cache = self.select_results_format_qcloud(acc_results, acc_status)
		elif self.source == "afanti":
			ret, should_cache = self.select_results_format_afanti(acc_results, acc_status)
		###### external service [test] ######
		elif self.source == "qqgroup":
			ret, should_cache = self.select_results_format_default(acc_results, acc_status)
		###### other ######
		elif self.source == "quickanswer":
			ret, should_cache = self.select_results_format_quickanswer(acc_results, acc_status)
		else:
			debug_info = {"from":"nothing", "err":"unknown source, just use default"}
			ret.append({"answer":None, "debug_info":debug_info})
		return ret, should_cache


	def form_response(self, results, status="ok"):
		ret = {}
		ret["status"] = status
		###### internal service [test] ######
		if self.source == "tsinghua_robot":
			result_str = self.form_response_tsinghua_robot(results, status)
		###### internal other product service ######
		elif self.source == "weimi":
			result_str = self.form_response_weimi(results, status)
		elif self.source.find("aiplatform") == 0:
			result_str = self.form_response_aiplatform(results, status)
		###### wangzai robot service ######
		elif self.source == "yzdd_onsite" or self.source == 'common_show' or self.source == 'show_medical':
			result_str = self.form_response_show(results, status)
		###### external service ######
		elif self.source == "qcloud":
			result_str = self.form_response_qcloud(results, status)
		###### other ######
		elif self.source == "quickanswer":
			result_str = self.form_response_quickanswer(results, status)
		elif not results:
			return json.dumps(ret, ensure_ascii=False).encode('utf8')
		else:
			ret["result"] = []
			for each in results:
				res = {"answer":each["answer"]}
				if "from" in each["debug_info"]:
					res["from"] = each["debug_info"]["from"]
				if self.debug == '1':
					res["debug_info"] = each["debug_info"]
				ret["result"].append(res)
			result_str = json.dumps(ret, ensure_ascii=False).encode('utf8')
		return result_str


	# 标准顺序
	def select_results_format(self, acc_results, acc_status):
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


	# 标准顺序默认回复
	def select_results_format_default(self, acc_results, acc_status):
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
		if len(ret) == 0:
			debug_info = {"err":"use_default", "from":"default", "sub_type":"闲聊-默认"}
			ret.append({"answer":random.choice(default_answer_list), "debug_info":debug_info})
		return ret, should_cache


	#维秘，用于source=weimi时
	def select_results_format_weimi(self, acc_results, acc_status):
		ret = []
		should_cache = False
		cnt = 0
		done = False
		ca_op_result = []
		for result_list in acc_results:
			if not result_list:
				continue
			for res in result_list:
				if res["answer"]:
					answer = res["answer"]
					debug_info = res["debug_info"]
					if debug_info["from"] == "weimi_category" and answer == "OP":
						ca_op_result.append({"answer":answer, "debug_info":debug_info})
					elif debug_info["from"] == "web_search":
						if len(ca_op_result) > 0 and debug_info.get("is_ugc", True) == True:
							ret.append(ca_op_result[0])
						else:
							ret.append({"answer":res["answer"], "debug_info":debug_info})
						done = True
					else:
						ret.append({"answer":res["answer"], "debug_info":debug_info})
						if debug_info["from"] == "weimi_faq":			#from=weimi_faq时返回至多两条结果
							cnt += 1
							if cnt == 2:
								done = True
						elif debug_info["from"] != "weimi_order":		#from=weimi_order时返回所有单号
							done = True
				if done == True:
					break
			if done == True or len(ret) != 0:
				break
		if len(ret) == 0:
			debug_info = {"err":"use_default", "from":"default"}
			ret.append({"answer":random.choice(default_weimi_answer_list), "debug_info":debug_info})
		return ret, should_cache


	#搜狗AI云，用于source=aiplatform开头的source
	def select_results_format_aiplatform(self, acc_results, acc_status):
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
		if len(ret) == 0:
			debug_info = {"err":"use_default", "from":"default", "result_type":"默认"}
			ret.append({"answer":random.choice(default_no_wangzai_answer_list), "debug_info":debug_info})
		return ret, should_cache


	#机器人汪仔，用于source=yzdd_onite 和 source=common_show时
	def select_results_format_show(self, acc_results, acc_status):
		ret = []
		should_cache = False
		answer_set = set()
		for result_list in acc_results:
			if not result_list:
				continue
			cnt = 0
			for res in result_list:
				if res["answer"] and res["answer"] not in answer_set:
					answer = res["answer"]
					debug_info = res["debug_info"]
					answer_set.add(res["answer"])
					ret.append({"answer":answer, "debug_info":debug_info})
					if debug_info["from"] == "retrieve":
						cnt = cnt + 1
					if cnt == 2:
						break
		if len(ret) == 0:
			debug_info = {"err":"use_default", "from":"dafault"}
			if self.from_lang == 'en':
				answer = random.choice(default_Englist_answer_list)
			else:
				answer = andom.choice(default_answer_list)
			ret.append({"answer":answer, "debug_info":debug_info})
		return ret, should_cache


	#机器人汪仔，用于source=show_medical时
	def select_results_format_medical(self, acc_results, acc_status):
		ret = []
		should_cache = False
		answer_set = set()
		for result_list in acc_results:
			if not result_list:
				continue
			cnt = 0
			for res in result_list:
				if res["answer"] and res["answer"] not in answer_set:
					answer = res["answer"]
					debug_info = res["debug_info"]
					answer_set.add(res["answer"])
					if debug_info['from'] == 'special_skill':
						ret.insert(0, {"answer":answer, "debug_info":debug_info})
					else:
						ret.append({"answer":answer, "debug_info":debug_info})
					if debug_info["from"] == "retrieve":
						cnt = cnt + 1
					if cnt == 2:
						break
		if len(ret) == 0:
			debug_info = {"err":"use_default", "from":"dafault"}
			if self.from_lang == 'en':
				answer = random.choice(default_Englist_answer_list)
			else:
				answer = andom.choice(default_answer_list)
			ret.append({"answer":answer, "debug_info":debug_info})
		return ret, should_cache


	#腾讯QQ音响，用于source=qcloud时
	def select_results_format_qcloud(self, acc_results, acc_status):
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
					if debug_info["from"] == "qrobot":
						if len(ret) == 0 or debug_info['level'] <= 2:
							ret = []
							ret.append({"answer":answer, "debug_info":debug_info})
						done = True
					else:
						ret.append({"answer":answer, "debug_info":debug_info})
						if debug_info['from'] != 'web_search' or debug_info.get("is_ugc", True) == False:
							done = True
				elif res["debug_info"]["from"] == "qrobot" and len(ret) != 0:
						done = True
				if done or len(ret) != 0:
					break
			if done:
				break
		if len(ret) == 0:
			debug_info = {"from":"empty", "result_type":"无结果"}
			ret.append({"answer":"", "debug_info":debug_info})
		return ret, should_cache


	#afanti，用于source=afanti时
	def select_results_format_afanti(self, acc_results, acc_status):
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
		if len(ret) == 0:
			debug_info = {"from":"empty", "sub_type":"无结果", "result_type":"无结果"}
			ret.append({"answer":"", "debug_info":debug_info})
		return ret, should_cache


	def select_results_format_quickanswer(self, acc_results, acc_status):
		ret = []
		should_cache = False
		cnt = 0
		N = 3
		answer_set = set()
		for result_list in acc_results:
			if not result_list:
				continue
			for res in result_list:
				ans = res["answer"]
				if ans and ans not in answer_set and len(ans) < 200:
					answer_set.add(ans)
					ret.append({"answer":ans,"debug_info":res["debug_info"]})
					cnt += 1
					if cnt == N:
						break
			if cnt == N:
				break
		return ret, should_cache


	#tsinghua_robot答案格式
	def form_response_tsinghua_robot(self, results, status):
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
		result_str = json.dumps(ret, ensure_ascii=False).encode('utf8')
		return result_str


	#weimi答案格式
	def form_response_weimi(self, results, status):
		ret = {}
		ret["status"] = status
		ret["result"] = []
		for each in results:
			res = {"answer":each["answer"]}
			if "from" in each["debug_info"]:
				_from = each["debug_info"]["from"]
				if _from in source_for_simple:
					_from = source_for_simple[_from]
				res["from"] = _from
			if "result_type" in each["debug_info"]:
				res["result_type"] = each["debug_info"]["result_type"]
			if res["from"] == "CA" and "SQ" in each["debug_info"]:
				res["SQ"] = each["debug_info"]["SQ"]
			if self.debug == '1':
				res["debug_info"] = each["debug_info"]
			ret["result"].append(res)
		result_str = json.dumps(ret, ensure_ascii=False).encode('utf8')
		return result_str


	#aiplatform答案格式
	def form_response_aiplatform(self, results, status):
		ret = {}
		ret["status"] = 0
		ret["statusText"] = "Success"
		ret["result"] = []
		for each in results:
			res = {"answer":each["answer"]}
			if "from" in each["debug_info"]:
				if each["debug_info"]["from"] == "blacklist":
					ret["status"] = 10001
			if each["debug_info"]["from"] in aiplatform_result_type:
				res["result_type"] = aiplatform_result_type[each["debug_info"]["from"]]
			elif "result_type" in each["debug_info"]:
				res["result_type"] = each["debug_info"]["result_type"]
			else:
				res["result_type"] = "其他"
			if self.debug == '1':
				res["debug_info"] = each["debug_info"]
			ret["result"].append(res)
		result_str = json.dumps(ret, ensure_ascii=False).encode('utf8')
		return result_str


	#show答案格式
	def form_response_show(self, results, status):
		ret = {}
		ret["status"] = status
		ret["result"] = []
		for each in results:
			res = {"answer":each["answer"]}
			if "from" in each["debug_info"]:
				if each["debug_info"]["from"] in source_for_simple:
					res["from"] = source_for_simple[each["debug_info"]["from"]]
				else:
					res["from"] = each["debug_info"]["from"]
			if "action" in each["debug_info"]:
				res["action"] = each["debug_info"]["action"]
			if res["from"] == "FA" and "title" in debug_info:
				res['title'] = each["debug_info"]["title"]
			if self.debug == '1':
				res["debug_info"] = each["debug_info"]
			ret["result"].append(res)
		result_str = json.dumps(ret, ensure_ascii=False).encode('utf8')
		return result_str


	#qcloud答案格式
	def form_response_qcloud(self, results, status):
		ret = {}
		if results[0]["debug_info"]["from"] == "blacklist":
			ret["content"] = ""
		else:
			ret["content"] = results[0]["answer"]
		if "result_type" in results[0]["debug_info"]:
			ret["result_type"] = results[0]["debug_info"]["result_type"]
		else:
			from_ = results[0]["debug_info"]["from"] if "from" in results[0]["debug_info"] else "闲聊"
			rt = qcloud_from_to_type[from_] if from_ in qcloud_from_to_type else from_
			ret["result_type"] = rt
		if "baike_image" in results[0]["debug_info"]:
			ret["baike_image"] =results[0]["debug_info"]["baike_image"]
		if "is_ugc" in results[0]["debug_info"]:
			ret["is_ugc"] = results[0]["debug_info"]["is_ugc"]
		else:
			ret["is_ugc"] = False
		if self.debug == '1':
			ret["debug_info"] = results[0]["debug_info"]
		result_str = json.dumps(ret, ensure_ascii=False).encode('utf8')
		return result_str


	#quickanswer答案格式
	def form_response_quickanswer(self, results, status):
		ret = {}
		ret["status"] = status
		ret["result"] = []
		for each in results:
			res = {"answer":each["answer"]}
			if "from" in each["debug_info"]:
				res["from"] = each["debug_info"]["from"]
			if self.debug == '1':
				res["debug_info"] = each["debug_info"]
			ret["result"].append(res)
		result_str = self.xml_format(ret)
		return ret


def make_app(conf, schedules, cache, session_manager):
	app = tornado.web.Application(
		[
			(r'/', IntegratedHandler, dict(conf=conf, schedules=schedules, cache=cache, session_manager=session_manager)),
		]
	)
	return app
