#coding=utf-8

from accessor import *
import check_dirty_answer as dirty


class Generate(Accessor):
	class Resource(Accessor.Resource):
		def init(self):
			self.killpatterns = []
			self.blacklist = {u"你是":"", u"你是？":"", u"你是我的":"", u"我也是":""}

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)

	def get_generate_result(self, res_str, query, params, debug_info):
		obj = json.loads(res_str)
		results = obj.get("result", "")
		if not results:
			debug_info["status"] = "none"
			return [(None, debug_info)]
		else:
			multi_results = []
			for each in results:
				debug_info.update(each["debug_info"])
				debug_info["sub_type"] = "闲聊-生成"
				ans = each["answer"]
				if not ans:
					ans = None
					debug_info["err"] = "empty string from generate server, maybe deprecated by it"
				elif ans.find("_UNK") != -1:
					ans = None
					debug_info["err"] = "_UNK found, deprecated"
				elif ans in Generate.rsc().blacklist:
					ans = None
					debug_info["err"] = "ans in blacklist"
				else:
					dirty_flag, dirty_word = dirty.check_dirty_answer(ans)
					if dirty_flag:
						ans = None
						debug_info["err"] = "ans in blacklist2[" + dirty_word.encode('utf-8') + ']'
				for each in Generate.rsc().killpatterns:
					if ans.find(each) != -1:
						ans = None
				multi_results.append((ans, debug_info))
			return multi_results

	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {"from":self.acc_name}
		try:
			url = self._conf.HTTP_GENERATE + "?query=" + urllib.quote(query.encode("utf-8"))
			async_reqs_param = [AsyncReqsParam("GET", url, None, None)]
			results = yield parallel_async(async_reqs_param, wait_for_all=True)
			for res_str, req_info in results:
				debug_info["req_info"] = req_info
				if res_str:
					ret_list = self.get_generate_result(res_str, query, params, debug_info)
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
	generate = Generate(conf)
	generate()
