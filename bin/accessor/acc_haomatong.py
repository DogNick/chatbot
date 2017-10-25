#!/usr/bin env python
#coding=utf8

from accessor import *
import common_method as comm


class Haomatong(Accessor):
	class Resource(Accessor.Resource):
		def init(self):
			self.no_info_answer = [
					u"这个号码我不知道哦",
					u"我没有搜到它的标记信息哦",
					u"这个号码没有被标记哦"
			]
			self.p_phone_search_intent = re.compile(u"查|搜索|找|查询|问|谁的|什么")
			self.p_phone_intent = re.compile(u"号码|电话|手机")
			self.p_mobile_phone = re.compile(r"(?:(?:\+86)|(?:86))?[\s|-]?([1][3-9]\d{9})") #+86 13612341234
			self.p_tele_phone = re.compile(r"\(?0\d{2,3}[) -]?\d{7,8}")	#010-56785678
			self.p_other_phone = re.compile(r"\d+")		#12315

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)

	def pre_process_phone_num(self, query_content):
		"""
			预处理，处理掉号码中的 -
		"""
		phone_query = comm.strQ2B(query_content).replace(u"-", "")
		return phone_query

	def get_phone_nums(self, query_content):
		"""
			从query中获取所有phone number, 返回其中一个
		"""
		phone_nums = ""
		mp_l = Haomatong.rsc().p_mobile_phone.findall(query_content)
		if len(mp_l) > 0:
			phone_nums = mp_l[0].strip()
		else:
			tp_l = Haomatong.rsc().p_tele_phone.findall(query_content)
			if len(tp_l) > 0:
				phone_nums = tp_l[0].strip()
			else:
				op_l = Haomatong.rsc().p_other_phone.findall(query_content)
				if len(op_l) > 0:
					phone_nums = op_l[0].strip()
		return phone_nums

	def is_contain_phone_intention(self, query):
		"""
			判断对话中是否含有查询电话号码的意图
		"""
		need_req = False
		formated_answer = None
		query_content = self.pre_process_phone_num(query)
		phone_nums = self.get_phone_nums(query_content)
		psi_rst = Haomatong.rsc().p_phone_search_intent.search(query_content)
		ps_rst = Haomatong.rsc().p_phone_intent.search(query_content)
		phone_intent_flag = psi_rst != None and ps_rst != None
		if phone_nums != "":
			need_req = True
			if phone_intent_flag and (len(phone_nums) > 12 or len(phone_nums) < 5):
				need_req = False
				formated_answer = u"您输入的电话号码有误哦!"
		elif phone_intent_flag:
			formated_answer = u"您还没告诉我电话号码呢，例如：您可以这样说查询号码10086"
		return need_req, formated_answer, phone_nums

	def parse_haomatong_json_info(self, phone_nums, phone_info, answer):
		title = ""
		count = 0
		hjson = json.loads(phone_info)
		if "desc" in hjson:
			if len(hjson["desc"]) == 2:
				title = hjson["desc"][0]["title"]
				count = hjson["desc"][1]["count"]
				answer = u"[%s]被[%d人]标记为[%s]" % (phone_nums.strip(), count, title)
			else:
				title = hjson["desc"][0]["title"]
				answer = u"[%s]被标记为[%s]" % (phone_nums.strip(), title)
		else:
			answer = u"[%s]%s。" % (phone_nums.strip(), random.choice(Haomatong.rsc().no_info_answer))
		return answer

	def get_haomatong_result(self, res_str, query, params, debug_info, phone_nums):
		answer = None
		debug_info["sub_type"] = "号码通"
		debug_info["result_type"] = u"号码通"
		if res_str != "" and res_str != None:
			answer = self.parse_haomatong_json_info(phone_nums, res_str, answer)
		return [(answer, debug_info)]

	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {'from':self.acc_name}
		try:
			need_req, answer, phone_nums = self.is_contain_phone_intention(query)
			if need_req == False:
				debug_info["sub_type"] = "号码通"
				debug_info["result_type"] = u"号码通"
				rets = [(answer, debug_info)]
			else:
				url = self._conf.HTTP_HAOMATONG % str(phone_nums)
				async_reqs_param = [AsyncReqsParam("GET", url, None, None)]
				results = yield parallel_async(async_reqs_param, wait_for_all=True)
				for res_str, req_info in results:
					debug_info["req_info"] = req_info
					if res_str:
						ret_list = self.get_haomatong_result(res_str, query, params, debug_info, phone_nums)
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
			query = raw_input('query:').decode("utf-8")
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
	haomatong = Haomatong(conf)
	haomatong()

