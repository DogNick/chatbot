#!/usr/bin/python
#coding=utf-8

import ctypes
from accessor import *


input_params = {}
input_params["type"] = 1
input_params["from_notify"] = 1
input_params["client_version"] = 9999
input_params["device"] = "uid"
input_params["uid"] = "u_123456"
input_params["eid"] = "1"
input_params["city"] = ""
headers = {"Content-Type": "application/x-www-form-urlencoded"}


class SpecialSkill(Accessor):
	class Resource(Accessor.Resource):
		def init(self):
			pass

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)

	def get_special_skill_result(self, res_str, query, params, debug_info):
		answer = None
		source = params.get("source", "")
		res_str = urllib.unquote_plus(res_str)
		#print res_str
		start = res_str.find("json=")
		end = res_str.find(" &moniter_string=")
		if start != -1 and end != -1:
			final_str = res_str[start+5:end]
			final_js = json.loads(final_str)
			multi_res = final_js["final_result"]
			for each in multi_res:
				if "description" in each:
					debug_info["sub_type"] = u"技能-" + each["description"]
				else:
					debug_info["sub_type"] = u"技能"
					debug_info["status"] = "skill matched"
				if "idioms_ret" in each:
					debug_info["idioms_ret"] = each["idioms_ret"]
				if "goalID" in each:
					debug_info["goalID"] = each["goalID"]
				idioms_intent = each.get("idioms_intent", None)
				debug_info["idioms_intent"] = idioms_intent
				answer = each["answer"]
				if debug_info["sub_type"] == u'技能-分诊' and source != 'show_medical':
					answer = None
					debug_info['status'] = 'source filter'
				detlog.info('[special_skill] [INFO] [query=%s] [answer=%s] ' % (query.encode('utf-8'), str(answer).encode('utf-8')))
				#if params["uid"] not in last_in_skill_time:
				#	last_in_skill_time[params["uid"]] = dict()
				#last_in_skill_time[params["uid"]][each["goalID"]] = time.time()
				break
		if answer == "" or answer == None:
			answer = None
			debug_info["status"] = "no skill matched"
		return [(answer, debug_info)]

	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {"from":"special_skill"}
		try:
			idx = ctypes.c_size_t(hash(params['uid'])).value % len(self._conf.HTTP_SKILL_LIST)
			url = self._conf.HTTP_SKILL_LIST[idx]
			input_params["input_str"] = query.encode("gbk", "ignore")
			data = "type=1&uid=%s&json=%s" % (params["uid"], urllib.quote_plus(json.dumps(input_params, ensure_ascii=False))+"&poi_points=116.3328727%2C39.9972206")
			detlog.info("[accessor_INFO] [special_skill] [query=%s] [uid=%s] [requests_url=%s]" % (query.encode('utf-8'), params['uid'], url))
			async_reqs_param = [AsyncReqsParam("POST", url, data, headers)]
			results = yield parallel_async(async_reqs_param, wait_for_all=True)
			for res_str, req_info in results:
				debug_info["req_info"] = req_info
				if res_str:
					ret_list = self.get_special_skill_result(res_str, query, params, debug_info)
					rets.extend(ret_list)
		except Exception, e:
			debug_info["status"] = "error, " + str(e)
			exclog.error('[query=%s]\n%s' % (query.encode('utf-8'), traceback.format_exc(e)))
		if rets == []:
			rets = [(None, debug_info)]
		raise gen.Return(rets)

	@gen.coroutine
	def test(self):
		source = ''
		while True:
			print '>>>>>>>>>>>>>>>>'
			query = raw_input("query:").decode("utf-8")
			begin = time.time()
			query = get_query_correction(query, source)
			params = preprocessing(query, source)
			print json.dumps(params, ensure_ascii=False)
			results = yield self.run(query, params)
			answer = results[0][0]
			debug_info = results[0][1]
			end = time.time()
			print 'answer:' + str(answer).encode('utf-8')
			print 'debug_info:' + json.dumps(debug_info, ensure_ascii=False)
			print 'cost:' + str(round((end-begin)*1000, 2)) + 'ms'
			print '\n\n'

if __name__ == "__main__":
	from preprocessing import *
	conf = Config("dev", True, "develop")
	#conf._env = 'nick'
	special_skill = SpecialSkill(conf)
	special_skill()
