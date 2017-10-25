#coding=utf-8

from accessor import *
import common_method as comm
import string_process as str_judge


en2cn_file = os.path.join(curr_dir, '../../data/translation/en2cn')
cn2en_file = os.path.join(curr_dir, '../../data/translation/cn2en')
translate_black = os.path.join(curr_dir, '../../data/translation/translation_blacklist.utf8')

need_default = {
		'wechat':0,
		'qqgroup':0,
		'yzdd_onsite':0,
		'common_show':0,
		'tsinghua_robot':0,
}

default_translation_answer = [
		u'我现在只会英汉互译，等我再长大点吧！',
		u'你说的这个语言我还不会呢，给你点个赞。',
		u'你懂好多语言哦，请收下我的膝盖吧。'
]

suoxie = u'缩写|缩略词'
other_language = u'阿拉伯语|波兰语|朝鲜语|丹麦语|德语|德文|俄语|俄文|法语|法文|芬兰语|荷兰语|捷克语|克罗地亚语|拉脱维亚语|立陶宛语|罗马尼亚语|马耳他语|马来语|挪威语|日语|日文|瑞典语|塞尔维亚语|斯洛伐克语|泰语|泰文|土耳其语|威尔士语|乌克兰语|西班牙语|希腊语|匈牙利语|意大利语|印地语|印度尼西亚语|印度话|越南语|越南话|韩语|韩文|韩国话'
language = u'(英文|英语|english|中文|汉语|chinese)'
pronoun = u'(这句话|这个句子|这段话|这段句子|这段文本|这个词语|这个单词|这个词|这句|这段|这个)'
pronoun_optional = pronoun[:-1] + u'|)'
prep = '(的|得|地|滴|)'
modal_particle = '(吧|好吧|吗|好吗|啊|啦|么|呢|呀|吖|)'
should = u'(应该|应当|该|)'
how_to = u'(怎么|怎样|如何|怎么样|咋)'
translate1 = u'(讲|说|翻译)'
translate1_phrase = translate1 + u'(一下|下|)'
translate2 = u'(翻译成|翻译|译成)'

p_suoxie = re.compile(suoxie)
p_other_lang = re.compile(other_language)
p_translation1 = re.compile(u'^(请|)用' + language + should + how_to + translate1_phrase + u'(.*?)' + pronoun)
p_translation2 = re.compile(u'^(请|)用' + language + should + how_to + translate1_phrase + pronoun_optional + u'(.*)')
p_translation3 = re.compile(u'^(请|)用' + language + translate1_phrase + pronoun_optional + u'(.*?)' + pronoun_optional + should + how_to + translate1)
p_translation4 = re.compile(u'^(请|)用' + language + translate1_phrase + pronoun_optional + u'(.*)')
p_translation5 = re.compile(u'(.*?)' + pronoun_optional + u'用' + language + should + how_to + translate1)
p_translation6 = re.compile(u'(.*?)' + pronoun_optional + translate2 + language + should + u'((是(什么|怎样的))|(' + how_to + translate1 + u'))')
p_translation7 = re.compile(u'(.*?)' + pronoun_optional + should + how_to + translate2 + language)
p_translation8 = re.compile(u'^' + translate2 + language + u'(.*)')
p_translation9 = re.compile(u'(把|)(.*?)' + pronoun_optional + translate2 + language)
p_translation10 = re.compile(u'(把|)(.*?)' + pronoun_optional + u'用' + language + translate1_phrase)
p_translation11 = re.compile(u'(请|)' + translate1_phrase + pronoun + language + '(.*)')
p_translation12 = re.compile(u'(请' + translate1_phrase + u'|)(.*?)' + pronoun_optional + u'(用|)' + prep + language + u'(含义|意思|)')
p_translation13 = re.compile(u'(.*?)' + pronoun_optional + '是(什么|啥)(含义|意思)')
p_translation14 = re.compile(u'(.*?)' + pronoun_optional + prep + u'(含义|意思)')
p_translation15 = re.compile(u'^(请|麻烦|)翻译(下|一下|)(.*?) + pronoun')
p_translation16 = re.compile(u'^(请|麻烦|)翻译(下|一下|)(.*)')
p_translation17 = re.compile(u'^' + should + how_to + translate1 + u'(.*?)' + pronoun)
p_translation18 = re.compile(u'^' + should + how_to + translate1 + pronoun_optional + u'(.*)')
p_translation19 = re.compile(u'(.*?)' + pronoun_optional + should + how_to + u'翻译')

# 判断意图优先级[(正则匹配公式, 匹配公式id, 翻译文本index, 翻译语言index, 翻译语言是否相反)]
match_priority = [
		(p_translation1, 1, 7, 2, 'normal'),
		(p_translation2, 2, 8, 2, 'normal'),
		(p_translation3, 3, 6, 2, 'normal'),
		(p_translation4, 4, 6, 2, 'normal'),
		(p_translation5, 5, 1, 3, 'normal'),
		(p_translation6, 5, 1, 4, 'normal'),
		(p_translation7, 7, 1, 6, 'normal'),
		(p_translation8, 8, 3, 2, 'normal'),
		(p_translation9, 9, 2, 5, 'normal'),
		(p_translation10, 10, 2, 4, 'normal'),
		(p_translation11, 11, 6, 5, 'reverse'),
		(p_translation12, 12, 4, 8, 'normal'),
		(p_translation13, 13, 1, None, 'normal'),
		(p_translation14, 14, 1, None, 'normal'),
		(p_translation15, 15, 3, None, 'normal'),
		(p_translation16, 16, 3, None, 'normal'),
		(p_translation17, 17, 4, None, 'normal'),
		(p_translation18, 18, 5, None, 'normal'),
		(p_translation19, 19, 1, None, 'normal'),
]


class Translation(Accessor):
	class Resource(Accessor.Resource):
		def load_translation_blacklist(self):
			'''加载翻译黑名单
			Args:
			Returns:
			Raises:
			'''
			inputs = open(translate_black, 'r')
			for line in inputs:
				line = line.strip().decode('utf-8')
				if line == '':
					continue
				if line.find('#') == 0:
					continue
				self.blacklist[line] = 0
			inputs.close()

		def load_translation_dictionary(self, paths):
			'''加载英译汉、汉译英词典
			Args:
				paths: 词典路径
			Returns:
				dic: 词典，编码Unicode
			Raises:
			'''
			dic = {}
			inputs = open(paths, 'r')
			for line in inputs:
				line = line.strip().decode('utf-8')
				items = line.split('\t')
				dic[items[0]] = items[1]
			inputs.close()
			return dic

		def init(self):
			begin = time.time()
			self.en_2_zh = {}		#词典，英译汉
			self.zh_2_en = {}		#词典，汉译英
			self.blacklist = {}
			try:
				self.load_translation_blacklist()
				self.en_2_zh = self.load_translation_dictionary(en2cn_file)
				self.zh_2_en = self.load_translation_dictionary(cn2en_file)
			except Exception, e:
				exclog.error('\n%s' % (traceback.format_exc(e)))
			cost = str(int(round(time.time()-begin, 3)*1000))
			detlog.info('[accessor_init] [translation] [cost=%sms]' % cost)

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)

	def translation_intention_filter(self, query, params, debug_info):
		'''过滤非翻译意图或者非英译汉、汉译英意图
		Args:
			query: 原始query，编码Unicode
			params: query的预处理信息
			debug_info: debug信息
		Returns:
			trans_flag: 需要翻译的语言, en: 翻译成英文, zh: 翻译成中文, other: 其他语言, no: 没有翻译意图, 其他返回None
			debug_info: debug信息
		Raise:
		'''
		trans_flag = None
		norm_query = comm.get_norm_query(params.get('seg', []))
		if norm_query in Translation.rsc().blacklist:
			trans_flag = 'no'
			debug_info['trans_flag'] = trans_flag
			debug_info['status'] = 'norm query in blacklist'
		elif p_suoxie.search(query) != None:
			trans_flag = 'no'
			debug_info['trans_flag'] = trans_flag
			debug_info['status'] = u'缩写'
		elif p_other_lang.search(query) != None:
			trans_flag = 'other'
			debug_info['trans_flag'] = trans_flag
			debug_info['status'] = u'其他语言'
		return trans_flag, debug_info

	def get_translation_query(self, match, index):
		'''返回需要翻译的文本
		Args:
			match: 命中的pattern
			index: 正则匹配的group index
		Returns:
			trans_content: 需要翻译的文本，编码Unicode
		Raises:
		'''
		trans_content = match.group(index)
		return trans_content

	def get_translation_lang(self, match, index, segs):
		'''得到需要翻译成的语言
		Args::
			match: 命中的pattern
			index: 正则匹配的group index
			seg: 分词结果
		Returns:
			trans_flag: 返回需要翻译成的语言，翻译成英文返回en，翻译成中文返回zh，其他返回None
		Raises:
		'''
		trans_flag = None
		if index != None:
			if match.group(index) == u'英文' or match.group(index) == u'英语' or match.group(index) == u'english':
				trans_flag = 'en'
			elif match.group(index) == u'中文' or match.group(index) == u'汉语' or match.group(index) == u'chinese':
				trans_flag = 'zh'
			for (i, seg) in enumerate(segs):
				if seg[0].find(match.group(index)) != -1 and seg[0] != match.group(index) and seg[1] >= 17 and seg[1] <= 22:
					trans_flag = None
					break
				elif seg[0] == match.group(index) and i > 0 and (segs[i-1][0] == u'学' or segs[i-1][0] == u'学习'):
					trans_flag = None
					break
		return trans_flag

	def judge_translation_lang(self, trans_content, pattern_type):
		'''判断需要翻译的文本是英文还是中文
		Args:
			trans_content: 需要翻译的文本，编码是Unicode
			pattern_type: 匹配的正则表达式编号
		Returns:
			trans_flag: 返回需要翻译成的语言，翻译成英文返回en，翻译成中文返回zh，其他返回None
		Raises:
		'''
		zh_flag = True
		en_flag = True
		trans_flag = None
		trans_content = comm.strQ2B(trans_content)
		for ch in trans_content:
			#if str_judge.is_digital(ch) or str_judge.is_english_punctuation(ch) or str_judge.is_chinese_punctuation(ch):
			#	continue
			if str_judge.is_alphabet(ch):
				zh_flag = False
				continue
			elif str_judge.is_chinese(ch):
				en_flag = False
				continue
		if zh_flag and en_flag == False and pattern_type > 13:
			trans_flag = 'en'
		elif en_flag and zh_flag == False:
			trans_flag = 'zh'
		return trans_flag

	def parse_regular_expression(self, each, query, params, debug_info):
		'''解析正则匹配结果，获取翻译文本和语言
		Args:
			each: 每个正则表达式的解析规则
			query: 原始query，编码Unicode
			params: query的预处理信息
			debug_info: debug信息
		Returns:
			trans_flag: 需要翻译的语言, en: 翻译成英文, zh: 翻译成中文, other: 其他语言, no: 没有翻译意图, 其他返回None
			trans_content: 需要翻译的文本，编码为Unicode
			debug_info: debug信息
		Raises:
		'''
		trans_flag = None
		trans_content = None
		p_exp, exp_id, content_index, lang_index, lang_style = each
		match = p_exp.search(query)
		if match != None:
			debug_info['pattern_type'] = exp_id
			trans_content = self.get_translation_query(match, content_index)
			trans_flag = self.get_translation_lang(match, lang_index, params.get('seg', []))
		if lang_style == 'reverse':
			if trans_flag == 'en':
				trans_flag = 'zh'
			elif trans_flag == 'zh':
				trans_flag = 'en'
		if trans_flag == None and trans_content != '' and trans_content != None:
			trans_flag = self.judge_translation_lang(trans_content, exp_id)
			if trans_flag == None:
				debug_info['status'] = 'trans flag is None'
		if trans_content == '' or trans_content == None:
			trans_flag = None
			debug_info['status'] = 'trans content is None'
		return trans_flag, trans_content, debug_info

	def judge_translation_intention(self, query, params, debug_info):
		'''判断翻译的意图和解析需要翻译的文本
		Args:
			query: 原始query，编码Unicode
			params: query的预处理信息
			debug_info: debug信息
		Returns:
			trans_flag: 需要翻译的语言, en: 翻译成英文, zh: 翻译成中文, other: 其他语言, no: 没有翻译意图, 其他返回None
			trans_content: 需要翻译的文本，编码为Unicode
			debug_info: debug信息
		Raises:
		'''
		trans_flag = None
		trans_content = ''
		query = query.lower()
		trans_flag, debug_info = self.translation_intention_filter(query, params, debug_info)
		if trans_flag == None:
			for each in match_priority:
				trans_flag, trans_content, debug_info = self.parse_regular_expression(each, query, params, debug_info)
				debug_info['trans_flag'] = trans_flag
				debug_info['trans_content'] = trans_content
				if trans_flag != None or trans_content != None:
					break
		return trans_flag, trans_content, debug_info

	def translation_from_dictionary(self, trans_content, trans_flag):
		'''判断是否为单词查询，查找字典
		Args:
			trans_content: 需要翻译的content，编码Unicode
			trans_flag: 需要翻译成的语言
		Returns:
			answer: 查找字典的结果，编码Unicode，未找到为None
		Raises:
		'''
		answer = None
		if trans_flag == 'en':
			if trans_content in Translation.rsc().zh_2_en:
				answer = Translation.rsc().zh_2_en[trans_content]
		elif trans_flag == 'zh':
			if trans_content in Translation.rsc().en_2_zh:
				answer = Translation.rsc().en_2_zh[trans_content]
		return answer

	def translation_preprocess(self, query, params, debug_info):
		'''判断翻译的意图和解析需要翻译的文本, 是否为词典查询
		Args:
			query: 原始query，编码Unicode
			params: query的预处理信息
			debug_info: debug信息
		Returns:
			trans_flag: 需要翻译的语言, en: 翻译成英文, zh: 翻译成中文, other: 其他语言, no: 没有翻译意图, 其他返回None
			answer: answer，编码为Unicode
			debug_info: debug信息
		Raises:
		'''
		answer = None
		debug_info['sub_type'] = u'翻译'
		debug_info['result_type'] = u'翻译'
		trans_flag, trans_content, debug_info = self.judge_translation_intention(query, params, debug_info)
		if trans_flag == 'other':
			if source in need_default:
				answer = random.choice(default_translation_answer)
				debug_info['status'] = 'other language use default answer'
		elif trans_flag != None:
			answer = self.translation_from_dictionary(trans_content, trans_flag)
			if answer != None:
				debug_info['status'] = 'result from dictionary'
		detlog.info("[accessor_INFO] [translation] [query=%s] [trans_flag=%s] [trans_content=%s]" % (query.encode('utf-8'), str(trans_flag), str(trans_content).encode('utf-8')))
		return trans_flag, answer, debug_info

	def get_translation_request_data(self, trans_flag, trans_content, params):
		'''生成请求翻译request时的data数据
		Args:
			trans_flag: 翻译语言
			trans_content: 翻译query，编码Unicode
			params: query的预处理信息
		Returns:
			data: json格式字符串
		Raises:
		'''
		data_json = {}
		data_json["uuid"] = params.get("uid", "wangzai")
		data_json["trans_frag"] = []
		text_tr = {}
		text_tr["id"] = "doc1"
		text_tr["text"] = trans_content.encode('utf-8')
		text_tr["sendback"] = "1"
		data_json["trans_frag"].append(text_tr)
		if trans_flag == "en":
			data_json["from_lang"] = "zh-CHS"
			data_json["to_lang"] = "en"
		elif trans_flag == "zh":
			data_json["from_lang"] = "en"
			data_json["to_lang"] = "zh-CHS"
		data = json.dumps(data_json)
		return data

	def get_translation_result(self, res_str, query, params, debug_info):
		answer = None
		multi_results = []
		result_json = json.loads(res_str)
		answer = result_json["trans_result"][0]["trans_text"].decode('utf-8')
		if query.find(answer) != -1:
			answer = None
			debug_info['status'] = 'lang wrong'
		else:
			debug_info['status'] = 'result from translation server'
		multi_results = [(answer, debug_info)]
		return multi_results

	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {"from":self.acc_name}
		try:
			trans_flag, answer, debug_info = self.translation_preprocess(query, params, debug_info)
			if answer == None and (trans_flag == 'en' or trans_flag == 'zh'):
				url = self._conf.HTTP_TRANSLATE
				data = self.get_translation_request_data(trans_flag, debug_info["trans_content"], params)
				async_reqs_param = [AsyncReqsParam("POST", url, data, None)]
				results = yield parallel_async(async_reqs_param, wait_for_all=True)
				for res_str, req_info in results:
					debug_info["req_info"] = req_info
					if res_str:
						ret_list = self.get_translation_result(res_str, query, params, debug_info)
						rets.extend(ret_list)
			else:
				rets = [(answer, debug_info)]
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
	conf = Config("dev", True, "develop")
	translation = Translation(conf)
	translation()

	querys = [
			u'怎么说话呢',
			u'用英语怎么翻译',
			u'一带一路是什么意思',
			u'你好用英语怎么说',
			u'你吃饭了么翻译成英语应该怎么说',
			u'How old are you怎么翻译成中文',
			u'把吃饭翻译成英文',
			u'把dinner用中文翻译一下',
			u'lunch的中文意思',
			u'翻译成中文i like you',
			u'i like you的意思',
			u'怎么翻译你好这句话',
			u'hello是什么意思',
			u'我想你用英语咋说',
			u'用英语怎么翻译今天下大雨这句话',
	]
