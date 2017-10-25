#coding=utf-8

from __future__ import division
from accessor import *
import common_method as comm


TOPN = 3
whitelist_dir = os.path.join(curr_dir, '../../data/whitelist/whitelist.value')

sources = {
		'yzdd_onsite':'yzdd',
		'common_show':'common_show',
		'weimi':'weimi'
}

p_title = re.compile('<title><!\[CDATA\[(.*)\]\]></title>')
p_content = re.compile('<content><!\[CDATA\[(.*)\]\]></content>')
p_tag = re.compile('post_response="([^"]+)"')
p_url = re.compile('<url><!\[CDATA\[(.*)\]\]></url>')


class Whitelist(Accessor):
	class Resource(Accessor.Resource):
		def init(self):
			begin = time.time()
			self.whitelist_value = {}
			try:
				inputs = open(whitelist_dir, 'r')
				for line in inputs:
					line = line.strip().decode('utf-8')
					items = line.split('\t')
					if len(items) != 2:
						continue
					answers = items[1].split('<br>')
					if answers[len(answers)-1] == '':
						del answers[len(answers)-1]
					self.whitelist_value[items[0]] = answers
				inputs.close()
			except Exception, e:
				exclog.error('\n%s' % (traceback.format_exc(e)))
			cost = str(int(round(time.time()-begin, 3)*1000))
			detlog.info('[accessor_init] [whitelist] [cost=%sms]' % (cost))

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)

	def print_all(self, candidates):
		for candidate in candidates:
			print ' * '.join(candidate).encode('utf-8')

	#计算title标红的部分
	def process_title(self, titles):
		simi = []
		result_title = []
		for title in titles:
			result, rel = comm.process_title_from_search_pair(title)
			simi.append(rel)
			result_title.append(result)
		return result_title, simi

	def get_resetfrank(self, query, text):
		resetfrank = []
		items = text.split('</item>')
		del items[len(items)-1]
		for item in items:
			value = '-1'
			if item.find('Nor:') != -1:
				pos1 = item.find('Nor:')
				pos2 = item.find(' ', pos1)
				if pos1 != -1 and pos2 != -1:
					value = item[pos1+4:pos2]
			elif item.find('Mul:') != -1:
				pos1 = item.find('Mul:')
				pos2 = item.find(' ', pos1)
				if pos1 != -1 and pos2 != -1:
					value = item[pos1+4:pos2]
			resetfrank.append(value)
		return resetfrank

	#获取白名单搜索结果
	def parse_search_result(self, query, res_str):
		result_title = []
		result_content = []
		result_tag = []
		result_url = []
		result_simi = []
		result_resetfrank = []
		result_title = p_title.findall(res_str)
		result_content = p_content.findall(res_str)
		result_content = map(lambda x:x.replace(u'\ue40b','').replace(u'\ue40a',''), result_content)
		result_tag = p_tag.findall(res_str)
		result_url = p_url.findall(res_str)
		result_title, result_simi = self.process_title(result_title)
		result_resetfrank = self.get_resetfrank(query, res_str)
		return zip(result_title, result_content, result_tag, result_url, result_simi, result_resetfrank)

	def judge_by_resetfrank(self, each):
		flag = False
		if int(each[5]) >= 800:
			if float(each[4]) > 0.4:
				flag = True
		elif int(each[5]) < 800 and int(each[5]) >= 500:
			if float(each[4]) > 0.5:
				flag = True
		elif int(each[5]) == -1:
			if float(each[4]) > 0.75:
				flag = True

	#0:title, 1:content, 2:tag, 3:url, 4:simi, 5:resetfrank
	def common_filter(self, candidates, query):
		#self.print_all(candidates)
		candidates = filter(lambda each:each[2] == 'post', candidates)
		candidates = filter(lambda each:self.judge_by_resetfrank(each) == True, candidates)
		if len(query) == 1 or len(query) == 2:
			candidates = filter(lambda each:float(each[4]) == 1.0, candidates)
		return candidates

	#保留传入source的数据
	def special_source_filter(self, candidates, source):
		if source == 'weimi':
			candidates = filter(lambda each:each[1].find(source) != -1, candidates)
		else:
			candidates = filter(lambda each:each[1].find(source) != -1 or each[1].find('normal') != -1, candidates)
		return candidates

	def get_all_answers(self, res_str, query, source):
		candidates = []
		candidates = self.parse_search_result(query, res_str)
		candidates = self.common_filter(candidates, query)
		candidates = self.special_source_filter(candidates, source)
		return candidates

	def get_answer_id(self, source, text):
		answer_id = ''
		normal_id = ''
		items = text.split('|')
		for item in items:
			if item.find(source) != -1:
				answer_id = item
				break
			elif item.find('normal') != -1:
				normal_id = item
		if answer_id == '' and normal_id  != '':
			answer_id = normal_id
		return answer_id

	def get_random_answer(self, answer_id, source):
		answer = random.choice(Whitelist.rsc().whitelist_value[answer_id])
		answer = comm.strQ2B(answer)
		if source.find('yzdd') == -1 and source.find('show') == -1:
			pos1 = text.find('{action:')
			pos2 = text.find('}', pos1)
			while pos1 != -1 and pos2 != -1:
				answer = answer[0:pos1] + answer[pos2+1:]
				pos1 = text.find('{action:')
				pos2 = text.find('}', pos1)
		return answer

	def get_source_format(self, source):
		if source in sources:
			source = sources[source]
		else:
			source = 'normal'
		return source

	def select_answer(self, res_str, query, source, debug_info):
		rets = []
		answer = None
		candidates = self.get_all_answers(res_str, query, source)
		#self.print_all(candidates)
		if len(candidates) > 0:
			selected = candidates[0]
			answer_id_list = selected[1]
			answer_id = self.get_answer_id(source, answer_id_list)
			answer = self.get_random_answer(answer_id, source)
			answer = answer.replace('<brbr>', '\n')
			debug_info['rel'] = selected[4]
			debug_info['score'] = float(selected[5])
			debug_info['url'] = selected[3]
			debug_info['sub_type'] = '白名单-检索'
			detlog.info('[accessor_INFO] [whitelist] [query=%s] [answer_id=%s, answer=%s]' % (query.encode('utf-8'), answer_id, answer.encode('utf-8').replace('\n', '')))
			rets.append((answer, debug_info))
		if rets == []:
			answer = None
			debug_info['status'] = 'no ans'
			rets = [(answer, debug_info)]
		return rets

	def get_whitelist_result(self, res_str, query, params, debug_info):
		answer = None
		rets = []
		if res_str == '' or res_str == None:
			debug_info['status'] = 'no ans'
			rets = [(answer, debug_info)]
		else:
			source = self.get_source_format(params.get('source', ''))
			res_str = res_str.decode('utf-16')
			rets = self.select_answer(res_str, query, source, debug_info)
		return rets

	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {"from":self.acc_name}
		try:
			url = self._conf.HTTP_WHITELIST
			data = 'parity=f1ddc0e4-57ef-4f1b-985f-b85e09c41afc&queryFrom=web&queryType=query&queryString=%s&start=0&end=100&forceQuery=1&magic=exp_flag:10' % urllib.quote_plus(query.encode('gbk', 'ignore'))
			async_reqs_param = [AsyncReqsParam("POST", url, data, None)]
			results = yield parallel_async(async_reqs_param, wait_for_all=True)
			for res_str, req_info in results:
				debug_info["req_info"] = req_info
				if res_str:
					ret_list = self.get_whitelist_result(res_str, query, params, debug_info)
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


if __name__ == '__main__':
	from preprocessing import *
	conf = Config("bj", True, "develop")
	whitelist = Whitelist(conf)
	whitelist()
