#!/usr/bin/python
#coding=utf-8

from bs4 import BeautifulSoup
from accessor import *


input_params = {}
input_params["type"] = 1
input_params["from_notify"] = 1
input_params["client_version"] = 9999
input_params["device"] = "uid"
input_params["uid"] = "u_123456"
input_params["eid"] = "1"
input_params["city"] = ""
headers1 = {"Content-Type": "application/x-www-form-urlencoded"}
headers2 = {'user-agent':'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'}

class Yyzs(Accessor):
	class Resource(Accessor.Resource):
		def init(self):
			pass

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)

	def get_request_query_gbk(self, query):
		if query.find(u"农历") != -1 and query.find(u"现在") != -1:
			query = query.replace(u"现在", u"今天")
		query_gbk = query.encode("gbk", "ignore")
		return query_gbk

	def parse_yyzs_result(self, final_js, query, source, answer, debug_info):
		debug_info["description"] = "no vertical matched"
		for each in final_js["final_result"]:
			if "description" not in each:
				continue
			#history of today, goalID == 305, 需要再次请求
			if "goalID" in each and each["goalID"] == 305 and "search_url" in each:
				debug_info["goalID"] = each["goalID"]
				debug_info["search_url"] = each["search_url"]
				debug_info["description"] = each["description"][each["description"].find("-")+1:]
				debug_info["result_type"] = debug_info["description"]
				debug_info["sub_type"] = u'问答-' + debug_info["description"]
				break
			debug_info["description"] = each["description"]
			if debug_info["description"].find(u"计算器") != -1 or debug_info["description"].find(u"笑话") != -1 or debug_info["description"].find(u"时间日期") != -1:
				debug_info["sub_type"] = debug_info["description"][0:debug_info["description"].find("-")]
				debug_info["result_type"] = debug_info["sub_type"]
				answer = re.split("\t+",  each["answer"])[0] # use first seg
				if "math_exp" in each:
					debug_info["math_exp"] = each["math_exp"]
				break
		if debug_info["description"].find(u"计算器") != -1:
			idx = answer.find("结果:")
			if idx != -1:
				answer = answer[idx+len(u"结果:"):]
				if answer.find('.') != -1:
					answer = str(round(float(answer), 4))
		if source == "samsung" and debug_info["description"].find(u"时间日期") != -1:
			answer = None
			debug_info["description"] += ", samsung filter"
		return answer, debug_info

	def get_yyzs_result(self, res_str, query, params, debug_info):
		answer = None
		multi_res = []
		source = params.get("source", "")
		res_str = urllib.unquote_plus(res_str)
		start = res_str.find("json=")
		end = res_str.find(" &moniter_string=")
		if start != -1 and end != -1:
			final_str = res_str[start+5:end]
			final_js = json.loads(final_str)
			answer, debug_info = self.parse_yyzs_result(final_js, query, source, answer, debug_info)
		multi_res = [(answer, debug_info)]
		return multi_res

	def get_today_hitory(self, res_str, answer, debug_info):
		soup = BeautifulSoup(res_str, "lxml")
		box = soup.find_all("div", class_="history-today-box")
		if len(box) > 0:
			years = [x.contents[0] for x in box[0].find_all("span")]
			titles = [x.contents[0] for x in box[0].find_all("div", class_="inner")]
			if len(years) == len(titles):
				year_title = [(y,t) for (y,t) in zip(years, titles) if t.find(u"大屠杀") == -1]
				idx = random.randint(0, len(year_title) - 1)
				answer = ("%s,%s" % (year_title[idx][0], year_title[idx][1]))
		return (answer, debug_info)

	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {"from":self.acc_name}
		try:
			url = self._conf.HTTP_YYZS
			input_params["input_str"] = self.get_request_query_gbk(query)
			data = "type=1&uid=%s&json=%s" % (params.get("uid", "wangzai"), urllib.quote_plus(json.dumps(input_params, ensure_ascii=False))+"&poi_points=116.3328727%2C39.9972206")
			async_reqs_param = [AsyncReqsParam("POST", url, data, headers1)]
			results = yield parallel_async(async_reqs_param, wait_for_all=True)
			for res_str, req_info in results:
				if res_str:
					ret_list = self.get_yyzs_result(res_str, query, params, debug_info)
				for i, r in enumerate(ret_list):
					r[1]["req_info"] = req_info
				rets.extend(ret_list)
			if rets[0][0] == None and "goalID" in rets[0][1] and rets[0][1]["goalID"] == 305:
				async_reqs_param = [AsyncReqsParam("GET", str(rets[0][1]["search_url"]), None, headers2)]
				results = yield parallel_async(async_reqs_param, wait_for_all=True)
				rets[0] = self.get_today_hitory(results[0][0], rets[0][0], rets[0][1])
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
			results = yield self.run(query, params)
			answer = results[0][0]
			debug_info = results[0][1]
			end = time.time()
			print json.dumps(params, ensure_ascii=False)
			print 'answer:' + str(answer).encode('utf-8')
			print 'debug_info:' + json.dumps(debug_info, ensure_ascii=False)
			print 'cost:' + str(round((end-begin)*1000, 2)) + 'ms'
			print '\n\n'


if __name__ == "__main__":
	from preprocessing import *
	conf = Config("bj", True, "online")
	yyzs = Yyzs(conf)
	yyzs()
