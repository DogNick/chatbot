#coding=utf8

from accessor import *


class Poem(Accessor):
	class Resource(Accessor.Resource):
		def init(self):
			pass

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)

	def get_poem_result(self, res_str, query, params, debug_info):
		answer = None
		if res_str != '' and res_str != None:
			obj = json.loads(res_str)
			answer = obj['result']
			if answer != '' and answer != None:
				answer = answer.decode('utf-8')
				debug_info['sub_type'] = u'问答-诗词'
		if answer == "":
			answer = None
		return [(answer, debug_info)]

	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {"from":self.acc_name}
		try:
			url = self._conf.HTTP_POEM + '?query=' + urllib.quote_plus(query.encode('utf-8'))
			async_reqs_param = [AsyncReqsParam("GET", url, None, None)]
			results = yield parallel_async(async_reqs_param, wait_for_all=True)
			for res_str, req_info in results:
				debug_info["req_info"] = req_info
				if res_str:
					ret_list = self.get_poem_result(res_str, query, params, debug_info)
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


if __name__ == '__main__':
	from preprocessing import *
	conf = Config("dev", True, "develop")
	poem = Poem(conf)
	poem()
