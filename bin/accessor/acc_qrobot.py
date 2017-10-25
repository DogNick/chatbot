#coding=utf-8

from accessor import *
import common_method as comm


class Qrobot(Accessor):
	class Resource(Accessor.Resource):
		def init(self):
			pass

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)

	def get_qrobot_result(self, res_str, query, params, debug_info):
		answer = None
		debug_info["sub_type"] = "问答-qrobot"
		multi_results = []
		ret = json.loads(res_str)
		if not ret["content"]:
			debug_info["status"] = "no obj from qrobot server"
			return [(answer, debug_info)]
		elif ret["result_type"] == u"世界之最":
			answer = ret["content"]
			debug_info["sub_type_id"] = "world_best"
			debug_info["sub_type"] = "问答-qrobot_世界之最"
			debug_info["result_type"] = ret["result_type"]
			debug_info["level"] = 1
			multi_results = [(answer, debug_info)]
		elif ret["result_type"] == u"新闻":
			tmp = random.choice(ret["content_list"])
			answer = tmp["title"]
			debug_info["url"] = tmp["url"]
			debug_info["sub_type_id"] = "news"
			debug_info["sub_type"] = "问答-qrobot_新闻"
			debug_info["result_type"] = ret["result_type"]
			debug_info["level"] = 2
			multi_results = [(answer, debug_info)]
		elif ret["result_type"] == u"问答":
			answer = comm.strQ2B(ret["content"])
			debug_info["is_ugc"] = True
			debug_info["sub_type_id"] = "wenda"
			debug_info["sub_type"] = u"问答-qrobot_ugc"
			debug_info["result_type"] = u"问答-ugc"
			debug_info["level"] = 4
			if len(query) <= 4:
				answer = None
				debug_info['status'] = 'wenda query too short'
			multi_results = [(answer, debug_info)]
		if not multi_results:
			debug_info["status"] = "ret result list is empty"
			multi_results = [(answer, debug_info)]
		return multi_results

	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {"from":self.acc_name}
		try:
			if query.find(u"农历") != -1 and query.find(u"现在") != -1:
				query = query.replace(u"现在", u"今天")
			url = self._conf.QROBOT_URL % urllib.quote(query.encode("utf-8"))
			async_reqs_param = [AsyncReqsParam("GET", url, None, None)]
			results = yield parallel_async(async_reqs_param, wait_for_all=True)
			for res_str, req_info in results:
				debug_info["req_info"] = req_info
				if res_str:
					ret_list = self.get_qrobot_result(res_str, query, params, debug_info)
					rets.extend(ret_list)
		except Exception, e:
			debug_info["status"] = 'error, ' + str(e)
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
	qrobot = Qrobot(conf)
	qrobot()
