#coding=utf-8

from accessor import *


class Retrieve(Accessor):
	class Resource(Accessor.Resource):
		def init(self):
			pass

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)

	def get_retrieve_result(self, res_str, query, params, debug_info):
		answer = None
		multi_results = []
		if res_str == None or res_str == '':
			debug_info['status'] = 'no res_str'
			multi_results = [(None, debug_info)]
		else:
			ret = json.loads(res_str)
			debug_info["sub_type"] = "闲聊-检索"
			debug_info["intend"] = params["query_classify"]["query_type_name"]
			if not ret["result"]:
				debug_info["title"] = "NULL"
				debug_info["orig_order"] = -1
				#debug_info["dnn2"] = -1
				debug_info["err"] = "no obj from retrieve server"
				multi_results = [(None, debug_info)]
			else:
				for i in range(3):
					if i == len(ret["result"]):
						break
					res_tuple = ret["result"][i]
					answer = res_tuple[1].encode("utf-8")
					web_info = res_tuple[2]
					debug_info["title"] = res_tuple[0].encode("utf-8")
					#debug_info["orig_order"] = res_tuple[-1]
					#debug_info["dnn2"] = web_info["dnn2"]
					multi_results.append((answer, debug_info))
		if not multi_results:
			debug_info["err"] = "ret result list is empty"
			multi_results = [(None, debug_info)]
		return multi_results

	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {"from":self.acc_name}
		try:
			strategy = "normal"
			url = "%s?query=%s&strategy=%s" % (self._conf.HTTP_RETRIEVE, urllib.quote(query.encode("utf-8")), strategy)
			async_reqs_param = [AsyncReqsParam("GET", url, None, None)]
			results = yield parallel_async(async_reqs_param, wait_for_all=True)
			for res_str, req_info in results:
				debug_info["req_info"] = req_info
				if res_str:
					ret_list = self.get_retrieve_result(res_str, query, params, debug_info)
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
	retrieve = Retrieve(conf)
	retrieve()
