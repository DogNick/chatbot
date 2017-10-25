#coding=utf-8

import os
import sys
import logging
import re

reload(sys)
sys.setdefaultencoding('utf-8')
curr_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(curr_dir, 'common'))
sys.path.append(os.path.join(curr_dir, '../lib'))
sys.path.append(os.path.join(curr_dir, '../conf'))

from accessor.acc_retrieve import Retrieve
from accessor.acc_generate import Generate
from accessor.acc_point24 import Point24
from accessor.acc_knowledge import Knowledge
from accessor.acc_special_skill import SpecialSkill
from accessor.acc_group_special_skill import GroupSpecialSkill
from accessor.acc_weimi import Weimi
from accessor.acc_whitelist import Whitelist
from accessor.acc_poem import Poem
from accessor.acc_weather import Weather
from accessor.acc_translation import Translation
from accessor.acc_haomatong import Haomatong
from accessor.acc_yyzs import Yyzs
from accessor.acc_universal_time import UniversalTime
from accessor.acc_web_search import WebSearch
from accessor.acc_qrobot import Qrobot
from accessor.acc_skill_platform import SkillPlatform
from accessor.acc_tsinghua_qa import TsinghuaQa
from accessor.acc_gd_mobile_kb import GdMobileKb
from default_answers import *



detlog = logging.getLogger("details")
exclog = logging.getLogger("exception")

def wait_for_all(acc_results, finished_results, all_acc_tuples, curr_acc_id, curr_acc_name):
	for result_list in acc_results:
		if not result_list:
			return False
	return True

def first_with_res(acc_results, finished_results, all_acc_tuples, curr_acc_id, curr_acc_name):
	curr_result_list = acc_results[curr_acc_id]
	for res in curr_result_list:
		if res["answer"]:
			return True
	for result_list in acc_results:
		if not result_list:
			return False
	return True

def highest_priority(acc_results, finished_results, all_acc_tuples, curr_acc_id, curr_acc_name):
	for result_list in acc_results:
		if not result_list:
			return False
		else:
			for res in result_list:
				if res["answer"]:
					return True
	return True

def highest_priority_for_qcloud(acc_results, finished_results, all_acc_tuples, curr_acc_id, curr_acc_name):
	if curr_acc_name == 'web_search':
		flag = False
		for res in finished_results:
			if res[0]["debug_info"]["from"] == "qrobot":
				flag = True
		if flag == False:
			return False
	for result_list in acc_results:
		if not result_list:
			return False
		else:
			for res in result_list:
				if res["answer"]:
					return True
	return True

def highest_N_priority(acc_results, finished_results, all_acc_tuples, curr_acc_id, curr_acc_name):
	N = 3
	cnt = 0
	for result_list in acc_results:
		if cnt == N:
			return True
		if not result_list:
			return False
		else:
			for res in result_list:
				if res["answer"]:
					cnt = cnt + 1
					break
	return True


NEED_PATTERN_SOURCE = {
		"wechat":0,
		"qqgroup":0,
		"aiplatform":0,
		"aiplatform_chat":0,
		"yzdd_onsite":0,
		"common_show":0,
		"board":0,
		"monitor":0,
		"test":0.
}

ACC_GROUPS = {
	"ALL":[
		SpecialSkill,
		Whitelist,
		Knowledge,
		Poem,
		Weather,
		Translation,
		UniversalTime,
		Haomatong,
		Yyzs,
		WebSearch,
		Generate,
		#Retrieve,
	],
	"VR":[
		Knowledge,
		Poem,
		Weather,
		Translation,
		UniversalTime,
		Yyzs,
    ],
	"CHAT":[
		Generate,
		#Retrieve
	],
	"SEARCH":[
		WebSearch
	]
}

SCHEDULES = {
	"dummy":{
		"accs":[
			("CHAT", highest_priority, 3.0)
		],
	},

	##############  internal service #############
	"wechat":{
		"accs":[
			(SkillPlatform, highest_priority, 1.0),
			("ALL", highest_priority, 3.0)
		],
		"use_session_manager":True
	},
	"tsinghua_robot":{
		"accs":[
			(TsinghuaQa, highest_priority, 1.5),
			("VR", highest_priority, 1.5),
			("SEARCH", highest_priority, 1.5),
			("CHAT", highest_priority, 1.5),
		],
		"use_cache":False,
		"use_session_manager":False
	},
	"samsung":{
		"accs":[
			(Knowledge, highest_priority, 1.0),
			(Poem, highest_priority, 1.0),
			(Weather, highest_priority, 1.0),
			(SkillPlatform, highest_priority, 1.0),
			(UniversalTime, highest_priority, 1.0),
			(Yyzs, highest_priority, 1.0),
		],
		"use_intent":False,
		"use_blacklist":False,
		"use_whitelist":False,
		"use_cache":False,
		"use_session_manager":False
	},

	##############  internal other product service #############
	"weimi":{
		"accs":[
			(Weimi, wait_for_all, 4.0),
			("VR", wait_for_all, 4.0),
			(Haomatong, wait_for_all, 4.0),
			("SEARCH", wait_for_all, 4.0),
			("CHAT", wait_for_all, 4.0),
		],
		"use_whitelist":False
	},
	"gd_mobile":{
		"accs":
		[
			(SkillPlatform, highest_priority, 1.0),
			(GdMobileKb, highest_priority, 1.0),
			("VR", highest_priority, 1.0),
			(Haomatong, highest_priority, 1.0),
			("SEARCH", highest_priority, 1.0),
			("CHAT", highest_priority, 1.0),
		],
		"use_whitelist":False,
		"use_session_manager":True
	},
	"aiplatform":{
		"accs":
		[
			("VR", highest_priority, 1.5),
			(Haomatong, highest_priority, 1.5),
			("SEARCH", highest_priority, 1.5),
			(Generate, highest_priority, 1.5),
		]
	},
	"aiplatform_chat":{
		"accs":
		[
			(Whitelist, highest_priority, 1.5),
			("CHAT", highest_priority, 1.5)
		],
	},
	"aiplatform_qa":{
		"accs":
		[
			("VR", highest_priority, 1.5),
			(Haomatong, highest_priority, 1.5),
			("SEARCH", highest_priority, 1.5),
		],
		"use_whitelist":False
	},
	"aiplatform_teemo":{
		"accs":
		[
			("VR", highest_priority, 1.5),
			(Haomatong, highest_priority, 1.5),
			("SEARCH", highest_priority, 1.5),
		],
		"use_whitelist":False
	},

	##############  wangzai robot service #############
	"yzdd_onsite":{
		"accs":
		[
			(SpecialSkill, highest_priority, 1.0),
			(Whitelist, highest_priority, 1.0),
			(Point24, highest_priority, 1.0),
			("VR", highest_priority, 1.0),
			(Haomatong, highest_priority, 1.0),
			("SEARCH", highest_priority, 1.0),
			("CHAT", highest_priority, 1.0),
		],
		"use_session_manager":True
	},
	"common_show":{
		"accs":
		[
			(SpecialSkill, highest_priority, 2.0),
			(Point24, highest_priority, 2.0),
			("VR", highest_priority, 2.0),
			(Haomatong, highest_priority, 2.0),
			("SEARCH", highest_priority, 2.0),
			("CHAT", highest_priority, 2.0),
		],
		"use_blacklist":False,
		"use_session_manager":True
	},
	"show_medical":{
		"accs":
		[
			(SpecialSkill, highest_priority, 2.0),
			(Point24, highest_priority, 2.0),
			("VR", highest_priority, 2.0),
			(Haomatong, highest_priority, 2.0),
			("SEARCH", highest_priority, 2.0),
			("CHAT", highest_priority, 2.0),
		],
		"use_blacklist":False,
		"use_session_manager":True
	},

	##############  external service #############
	"qqgroup":{
		"accs":
		[
			("VR", highest_priority, 1.8),
			("SEARCH", highest_priority, 1.8),
			(Generate, highest_priority, 1.8),
		],
		"use_cache":True,
		"callback_timeout":2.0
	},
	"qcloud":{
		"accs":[
			("VR", highest_priority_for_qcloud, 2.0),
			(Haomatong, highest_priority_for_qcloud, 2.0) ,
			(WebSearch, highest_priority_for_qcloud, 2.0),
			(Qrobot,highest_priority_for_qcloud, 2.0),
			#(baike, highest_priority_for_qcloud, 2.0)
		],
		"use_whitelist":False
	},
	"afanti":{
		"accs":[
			("VR", highest_priority, 1.5),
			(Haomatong, highest_priority, 1.5),
			("SEARCH", highest_priority, 1.5),
		],
	},

	##############  service test #############
	"chaten":{
		"accs":
		[
			#(GroupSpecialSkill, highest_priority, 2.0),
			(Generate, highest_priority, 1.8),
		],
		"use_intent":False,
		"use_blacklist":False,
		"use_whitelist":False,
		"use_cache":False,
		"callback_timeout":2.0,
		"use_session_manager":False
	},
	"groupqa":{
		"accs":
		[
			(GroupSpecialSkill, highest_priority, 2.0),
			#(Generate, highest_priority, 1.8),
		],
		"use_cache":False,
		"callback_timeout":2.0,
		"use_session_manager":True
	},

	##############  wenda #############
	"wenda":{
		"accs":[
			("VR", highest_priority, 1.5),
			(SkillPlatform, highest_priority, 1.5),
			(Haomatong, highest_priority, 1.5),
			("SEARCH", highest_priority, 1.5),
		],
		"use_intent":False,
		"use_blacklist":False,
		"use_whitelist":False,
		"use_cache":False,
		"use_session_manager":False
	},

	##############  test  #############
	"board":{
		"accs":[
			("ALL", wait_for_all, 3.0)
		],
	},
	"test":{
		"accs":[
			(Generate, wait_for_all, 4.0),
			(WebSearch, highest_priority, 1.8),
		],
	},
	"test2":{
		"accs":[
			(WebSearch, wait_for_all, 4.0),
			(Retrieve, highest_priority, 1.8),
		],
	}
}

source_for_simple = {
		"faq":"FA",
		"weimi_whitelist":"WM",
		"weimi_order":"DA",
		"weimi_people":"SP",
		"weimi_faq":"QA",
		"weimi_category":"CA",
		"whitelist_pattern":"WP",
		"precise_chat":"PC",
		"whitelist":"WH",
		"poem":"PO",
		"weather":"WD",
		"translation":"TR",
		"universal_time":"UT",
		"haomatong":"HM",
		"yyzs":"VA",
		"web_search":"WS",
		"generate":"GE",
		"retrieve":"RE",
		"default":"DF"
}


qcloud_from_to_type = {
		"poem":"问答-poem",
		"weather":"天气",
		"translation":"翻译",
		"yyzs":"历史上的今天",
		"short_qa":"问答-short",
		"web_search":"问答-ugc",
		"web_search:pesodu_census":"问答-ugc",
		"generate":"闲聊",
		"retrieve":"闲聊",
		"default":"闲聊",
}

aiplatform_result_type = {
		"whitelist":"闲聊",
		"poem":"问答",
		"weather":"天气",
		"translation":"翻译",
		"universal_time":"时间日期",
		"haomatong":"号码通",
		"web_search":"问答",
		"generate":"闲聊",
		"retrieve":"闲聊"
}



class SchedulesManager(object):
	class Schedule(object):
		pass

	def __init__(self, conf, schedule_defines, sources_to_load=None):
		self._sources_to_load = re.split(",", sources_to_load) if sources_to_load else []
		self._schedule_defines = schedule_defines 
		self._conf = conf

		# If _sources_to_load is assigned, we only load Accesors related
		# else we load all Accessors defined in the SCHEDULES 
		if not self._sources_to_load:
			detlog.info("[SchedulesManager] source_to_load empty, The whole SCHEDULES will be loaded")
			self._sources_to_load = self._schedule_defines.keys()

		# Create Accessors obj according to conf, and its resources will only be created
		# Once
		for key in self._sources_to_load:
			acc_tuples = []
			for acc_tuple in self._schedule_defines[key]["accs"]:
				if isinstance(acc_tuple[0], bytes):
					mapped_acc_tuples = ACC_GROUPS[acc_tuple[0]]
					for each in mapped_acc_tuples:
						if isinstance(each, tuple):
							acc_cls, judgemethod, timeout = each 
						else:
							acc_cls, judgemethod, timeout = each, acc_tuple[1], acc_tuple[2]
						detlog.info("[SchedulesManager] [%s] Creating accessor %s ..." % (key, acc_cls.__name__))
						acc_obj = acc_cls(self._conf)
						acc_obj.initialize()
						acc_tuples.append((acc_obj, judgemethod, timeout))
				else:
					acc_cls, judgemethod, timeout = acc_tuple
					detlog.info("[SchedulesManager] [%s] Creating accessor %s ..." % (key, acc_cls.__name__))
					acc_obj = acc_cls(self._conf)	
					acc_obj.initialize()
					acc_tuples.append((acc_obj, judgemethod, timeout))
			self._schedule_defines[key]["accs"] = acc_tuples

	def schedule(self, source):
		if source not in self._schedule_defines:
			raise ValueError("""schedule of source '%s' not initialized, please add
									it to options: sources_to_load""" % source)
		detlog.info("[SchedulesManager] create schedule package for %s ..." % source)
		sd = self._schedule_defines[source]

		# produce a schedule obj with some default values, according to given source
		s = SchedulesManager.Schedule() 
		s.use_cache = sd.get("use_cache", False)
		s.use_whitelist = sd.get("use_whitelist", True)
		s.use_blacklist = sd.get("use_blacklist", True)
		s.use_session_manager = sd.get("use_session_manager", False)
		s.use_intent = sd.get("use_intent", True)
		s.acc_tuples = sd.get("accs", [])
		return s

if __name__ == "__main__":
	from config import Config
	detlog.setLevel(logging.INFO)
	exclog.setLevel(logging.INFO)
	detlog.propagate = False
	exclog.propagate = False
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
	schedules = SchedulesManager(conf, SCHEDULES, "")
