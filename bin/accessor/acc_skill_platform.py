#coding=utf-8

from accessor import *


class SkillPlatform(Accessor):
	class Resource(Accessor.Resource):
		def init(self):
			pass

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)
		self.acc_name = "skill_platform"

	def get_skill_platform_result(self, res_str, query, params, debug_info):
		answer = None
		debug_info["sub_type"] = u"技能平台"
		debug_info["result_type"] = u"技能平台"
		results = []
		#detlog.info('>>>>>>>>>>skill_result:' + res_str)
		ret = json.loads(res_str)
		if ret["success"]:
			answer = ret["text"]
			a_json = json.loads(answer)
			if "answer" in a_json:
				answer = a_json["answer"]
			if "sunrise_time" in a_json:
				debug_info["sub_type"] = "日出日落"
			if "sunset_time" in a_json:
				debug_info["sub_type"] = "日出日落"
			debug_info.update(a_json)
			results = [(answer, debug_info)]
		elif "status" in ret and ret["status"] != "NotSkillRequest":
			debug_info["error_status"] = ret["status"]
			#results = [("这个技能好像有问题", debug_info)]
			results = [(None, debug_info)]
		else:
			results = [(None, debug_info)]
		return results

	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {"from":self.acc_name}
		try:
			url = self._conf.SKILL_PLATFORM_URL
			params = {"userId":params.get("uid", "wangzai"), "query": query}
			if "skillId" in params and params["skillId"] != None:		#广东移动skill
				params['skillId'] = acc_params["skillId"]
				url = 'http://10.144.103.187:9999/query'
			async_reqs_param = [AsyncReqsParam("POST", url, json.dumps(params, ensure_ascii=False), None)]
			results = yield parallel_async(async_reqs_param, wait_for_all=True)
			for res_str, req_info in results:
				debug_info["req_info"] = req_info
				if res_str:
					ret_list = self.get_skill_platform_result(res_str, query, params, debug_info)
					rets.extend(ret_list)
		except Exception, e:
			debug_info["status"] = "error, " + str(e)
			exclog.error('[query=%s]\n%s' % (query.encode('utf-8'), traceback.format_exc(e)))
		if rets == []:
			rets = [(None, debug_info)]
		raise gen.Return(rets)

	@gen.coroutine
	def test(self):
		source = ""
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
	skill_platform = SkillPlatform(conf)
	skill_platform()
