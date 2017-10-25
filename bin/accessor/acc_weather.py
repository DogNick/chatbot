#!/usr/bin env python
#coding=utf8

import datetime
from accessor import *


this_year_2 = time.strftime('%y')
this_year_4 = time.strftime('%Y')
internal_dir = os.path.join(curr_dir, '../../data/weather/weather_internal_city.utf8')
oversea_dir = os.path.join(curr_dir, '../../data/weather/weather_oversea_city.utf8')
w_black_dir = os.path.join(curr_dir, '../../data/weather/weather_blacklist.utf8')

p_weather = re.compile(u'气温|天气|温度|下雨|有雨|暴雨|小雨|中雨|大雨|下雪|有雪|暴雪|暴风雪|小雪|中雪|大雪|雨夹雪|有风|刮风|大风|台风|几度|多少度')
p_weather_weak = re.compile(u'热|冷')
p_date_no1 = re.compile(u'昨天|昨日|昨夜|昨晚|yesterday')
p_date_no2 = re.compile(u'大后天|大后日')
p_date_no3 = re.compile(u'(未来|)(三天|四天|五天|六天|七天|一周)')
p_date1 = re.compile(u'今天|今早|今晚|下午|上午|中午|早上|晚上|傍晚|现在')
p_date2 = re.compile(u'明天|明日|明早|明晚|tomorrow')
p_date3 = re.compile(u'后天|后日')
p_date4 = re.compile(u'未来两天')
p_year = re.compile(u'(\d{4}|\d{2})年')
p_month_day = re.compile(u'(\d{2}|\d{1})月(\d{2}|\d{1})(号|日|)')
p_day = re.compile(u'(\d{2}|\d{1})(号|日)')

time_2_date_type = [
		(p_date_no1, u'not_support'),
		(p_date_no2, u'not_support'),
		(p_date_no3, u'not_support'),
		(p_date1, u'今天'),
		(p_date2, u'明天'),
		(p_date3, u'后天'),
		(p_date4, u'三天'),
]

API_STATUS_CODE = {
		'AP010001':'请求参数错误',			#API请求参数错误
		'AP010002':'没有权限',				#没有权限访问这个API接口
		'AP010003':'密钥错误',				#API密钥key错误
		'AP010004':'签名错误',				#签名错误
		'AP010005':'API不存在',				#你请求的API不存在
		'AP010006':'地点没有权限',			#没有权限访问这个地点
		'AP010007':'需使用签名',			#JSONP请求需要使用签名验证方式
		'AP010008':'没有绑定域名',			#没有绑定域名
		'AP010009':'user-agent设置',		#API请求的user-agent与你设置的不一致
		'AP010010':'地点错误',				#没有这个地点
		'AP010011':'查不到IP对应城市',		#无法查找到制定IP地址对应的城市
		'AP010012':'服务过期',				#你的服务已经过期
		'AP010013':'访问量余额不足',		#访问量余额不足
		'AP010014':'超出每小时免费访问量',	#免费用户超过了每小时访问量额度，一小时后自动恢复
		'AP010015':'不支持城市限行信息',	#暂不支持该城市的车辆限行信息
		'AP100001':'数据缺失',				#系统内部错误：数据缺失
		'AP100002':'数据错误',				#系统内部错误：数据错误
		'AP100003':'服务内部错误',			#系统内部错误：服务内部错误
}

no_position_answer = [
		u'我无法获得你的位置呢，你可以这样问我"北京',
		u'我还不知道你所在的城市，你可以这样问我"北京',
		u'哎呀，我不知道你在哪呀，你可以这样问我"北京'
]


class Weather(Accessor):
	class Resource(Accessor.Resource):
		def load_city_words(self):
			"""加载城市名字
			Args:
			Returns:
			Raises:
			"""
			words_str = ''
			with open(internal_dir, 'r') as inputs:
				for line in inputs:
					items = line.strip().decode('utf-8').split('\t')
					if len(items) != 2:
						continue
					city1 = items[0]
					city2 = items[1]
					words_str += city1 + '|'
					if city1 not in self.city_dict:
						self.city_dict[city1] = city2
			if words_str != '':
				self.p_city = re.compile(words_str[:-1])

		def load_country_words(self):
			"""加载无法获取天气的国家地区名字
			Args:
			Returns:
			Raises:
			"""
			words_str = ''
			inputs = open(oversea_dir, 'r')
			for line in inputs:
				line = line.strip().decode('utf-8')
				words_str += line + '|'
			if words_str != '':
				self.p_oversea = re.compile(words_str[:-1])

		def load_weather_blacklist(self):
			"""加载天气blacklist
			Args:
			Returns:
			Raises:
			"""
			words_str = ''
			inputs = open(w_black_dir, 'r')
			for line in inputs:
				if line.find('#') == 0:
					continue
				line = line.strip().decode('utf-8')
				words_str += line + '|'
			if words_str != '':
				self.p_weather_black = re.compile(words_str[:-1])

		def init(self):
			begin = time.time()
			self.city_dict = {}					#原city -> 请求city，编码Unicode
			self.p_city = None					#包含所有城市的正则表达式，编码Unicode
			self.p_oversea = None				#包含国家名字的正则表达式，编码Unicode
			self.p_weather_black = None			#包含天气blacklist的正则表达式，编码Unicode
			try:
				self.load_city_words()
				self.load_country_words()
				self.load_weather_blacklist()
			except Exception, e:
				exclog.error('\n%s' % (traceback.format_exc(e)))
			cost = str(int(round(time.time()-begin, 3)*1000))
			detlog.info('[accessor_init] [weather] [cost=%sms]' % (cost))

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)
		Weather.rsc().city_weather_cache = {}		#天气缓存

	def is_contain_word(self, query, p_tmp):
		"""正则匹配，匹配不成功，返回None，匹配成功，返回匹配到的字符串
		Args:
			query: 原始query，编码Unicode
			p_tmp: 正则表达式，编码Unicode
		Returns:
			result: 匹配到的字符串，匹配不成功，返回None，编码Unicode
		Raises:
		"""
		result = None
		m = p_tmp.search(query)
		if m != None:
			result = m.group(0)
		return result

	def is_weather_intention(self, query, params, debug_info):
		"""判断是否有天气的意图
		Args:
			query: 原始query，编码Unicode
			params: query的预处理结果
			debug_info: debug信息
		Returns:
			intent_flag: 是否有天气意图
			debug_info: debug信息
		Raises:
		"""
		intent_flag = True
		match1 = self.is_contain_word(query, p_weather)
		match2 = self.is_contain_word(query, p_weather_weak)
		if match1 == None and match2 == None:
			intent_flag = False
			debug_info['intent_word'] = None
			debug_info['status'] = 'no weather intent'
		elif match1 != None:
			debug_info['intent_word'] = match1
		else:
			intent_word = match2 + u'吗'
			for seg in params['seg']:
				if seg[0].find(match2) != -1 and seg[0] != match2:
					intent_flag = False
					debug_info['intent_word'] = None
					debug_info['status'] = '[' + match2 + '] in [' + seg[0] + ']'
					break
		return intent_flag, debug_info

	def parse_regular_expression(self, each, query, params, debug_info):
		"""解析正则匹配结果，获取时间词
		Args:
			each: 每个正则表达式的解析规则
			query: 原始query，编码Unicode
			params: query的预处理信息
			debug_info: debug信息
		Returns:
			date_type: 时间词
		Raises:
		"""
		date_type = None
		if self.is_contain_word(query, each[0]) != None:
			date_type = each[1]
		return date_type

	def set_date_time_and_type(self, debug_info):
		"""对给定的real_date设定date_type, 对给定date_type设定real_date
		Args:
			debug_info: debug信息
		Returns:
			debug_info: debug信息
		Raises:
		"""
		real_data = debug_info['real_date']
		date_type = debug_info['date_type']
		if real_data != None and data_type == None:
			real_data = datetime.datetime.strptime(real_data, '%Y-%m-%d')
			if real_data == str(datetime.date.today()):
				debug_info['date_type'] = u'今天'
			elif real_data == str(datetime.date.today() + datetime.timedelta(days=1)):
				debug_info['date_type'] = u'明天'
			elif real_data == str(datetime.date.today() + datetime.timedelta(days=2)):
				debug_info['date_type'] = u'后天'
			else:
				debug_info['date_type'] = u'not_support'
		elif real_data == None:
			if date_type == None:
				date_type = debug_info['date_type'] = u'今天'
			if date_type == u'今天' or date_type == u'三天':
				debug_info['real_date'] = datetime.date.today().strftime('%Y-%m-%d')
			elif date_type == u'明天':
				debug_info['real_date'] = (datetime.date.today() + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
			elif date_type == u'后天':
				debug_info['real_date'] = (datetime.date.today() + datetime.timedelta(days=2)).strftime('%Y-%m-%d')
		return debug_info

	def extract_weather_date(self, query, params, debug_info):
		"""抽取查询天气的日期
		Args:
			query: 原始query，编码Unicode
			params: query的预处理结果
			debug_info: debug信息
		Returns:
			debug_info: debug信息
		Raises:
		"""
		debug_info['date_type'] = None
		debug_info['real_date'] = None
		for each in time_2_date_type:
			debug_info['date_type'] = self.parse_regular_expression(each, query, params, debug_info)
			if debug_info['date_type'] != None:
				break
		if debug_info['date_type'] == None:
			year = self.is_contain_word(query, p_year)
			day = self.is_contain_word(query, p_day)
			month_day = p_month_day.search(query)
			if month_day != None and int(month_day.group(1)) <= 12:
				if year != None and year != this_year_2 and year != this_year_4:
					debug_info['date_type'] = u'not_support'
				if debug_info['date_type'] == None:
					debug_info['real_date'] = '%s-%02d-%02d' % (time.strftime('%Y'), int(month_day.group(1)), int(month_day.group(2)))
			elif day != None and int(day) <= 31:
				debug_info['real_date'] = '%s-%02d' % (time.strftime('%Y-%m'), int(day))
		debug_info = self.set_date_time_and_type(debug_info)
		return debug_info

	def extract_weather_city(self, query, params, debug_info):
		"""判断查询天气的地点
		Args:
			query: 原始query，编码Unicode
			params: query的预处理结果
			debug_info: debug信息
		Returns:
			debug_info: debug信息
		Raises:
		"""
		debug_info['city'] = None
		debug_info['city_flag'] = True
		foreign_city = self.is_contain_word(query, Weather.rsc().p_oversea)
		city = self.is_contain_word(query, Weather.rsc().p_city)
		if foreign_city != None:
			debug_info['city'] = foreign_city
			debug_info['city_flag'] = False
			debug_info['status'] = 'foreign city[' + foreign_city + ']'
		elif city != None:
			debug_info['city'] = city
			debug_info['standard_city'] = Weather.rsc().city_dict[city]		#可查询的location
		else:
			debug_info['city_flag'] = False
			debug_info['status'] = 'no location'
		return debug_info

	def check_weather_cache(self, answer, debug_info):
		"""查询cache中有无缓存结果，若有结果，直接返回，不需要再请求API，如果已经跨天，清缓存
		Arss:
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		"""
		city = debug_info['standard_city']
		real_date = debug_info['real_date']
		date_type = debug_info['date_type']
		if city in Weather.rsc().city_weather_cache and real_date != None:
			if date_type in Weather.rsc().city_weather_cache[city]:
				if Weather.rsc().city_weather_cache[city][date_type][0][0] == real_date:
					answer = city + Weather.rsc().city_weather_cache[city][date_type][0][1]
					debug_info['status'] = 'answer from weather cache'
				else:
					Weather.rsc().city_weather_cache[city] = {}
		return answer, debug_info

	def weather_intention_judgement(self, query, params, debug_info):
		"""综合判断天气意图，包括时间、地点、天气关键词
		Args:
			query: 原始query，编码Unicode
			params: query的预处理结果
			debug_info: debug信息
		Returns:
			intent_flag: 是否需要请求API，False表示不需要
			answer: 回复，编码Unicode
			debug_info: debug信息
		Raises:
		"""
		answer = None
		intent_flag = True		#是否需要请求API
		query_type = params['query_classify']['query_type']
		if query_type == 0 or query_type == 5 or query_type == 7:
			intent_flag = False
			debug_info['status'] = 'query type error'
			return intent_flag, answer, debug_info
		if len(query) < 4 or len(query) > 15:		#todo: 去掉英文、拼音，标点
			intent_flag = False
			debug_info['status'] = 'query length(' + str(len(query)) + ')'
			return intent_flag, answer, debug_info
		if self.is_contain_word(query, Weather.rsc().p_weather_black) != None:
			intent_flag = False
			debug_info['status'] = 'query contain black word[' + self.is_contain_word(query, Weather.rsc().p_weather_black) + ']'
			return intent_flag, answer, debug_info
		if query == u'天气' or query == u'天气预报':
			intent_flag = False
			answer = random.choice(no_position_answer) + u'"天气。'
			debug_info['status'] = 'no location, no date'
			debug_info['sub_type'] = debug_info['result_type'] = u'天气'
			return intent_flag, answer, debug_info
		intent_flag, debug_info = self.is_weather_intention(query, params, debug_info)
		if intent_flag == False:
			return intent_flag, answer, debug_info
		debug_info = self.extract_weather_date(query, params, debug_info)
		if debug_info['date_type'] == u'not_support':
			intent_flag = False
			answer = u'您查询的日期暂不支持哦，我暂时只能查询三天以内的天气'
			debug_info['status'] = 'date not support'
			debug_info['sub_type'] = debug_info['result_type'] = u'天气'
			return intent_flag, answer, debug_info
		debug_info = self.extract_weather_city(query, params, debug_info)
		if debug_info['city_flag'] == False:
			intent_flag = False
			if debug_info['city'] == None and debug_info['date_type'] != None and debug_info['date_type'] != u'not_support':
				answer = random.choice(no_position_answer) + debug_info['date_type'] + debug_info['intent_word'] + u'"。'
				debug_info['sub_type'] = debug_info['result_type'] = u'天气'
			return intent_flag, answer, debug_info
		answer, debug_info = self.check_weather_cache(answer, debug_info)
		if answer != None:
			intent_flag = False
			debug_info['sub_type'] = debug_info['result_type'] = u'天气'
			return intent_flag, answer, debug_info
		return intent_flag, answer, debug_info

	def generte_weather_text(self, result, date_type):
		"""根据API的结果生成回答
		Args:
			result: 某一天的天气结果，API的json结果，
			date_type: 时间类型，编码Unicode
		Returns:
			text: 根据某一天的API的结果生成回答，编码Unicode
		Raises:
		"""
		text = date_type + u'(' + result['date'] + u')最低气温' +  result['low'] + u'度，最高气温' + result['high'] + u'度，'	#温度
		if result['text_day'] == result['text_night']:		#天气现象
			text += result['text_day'] + u'，'
		else:
			text += result['text_day'] + u'转' + result['text_night'] + u'，'
		if result['wind_direction'] != u'无持续风向':
			text += result['wind_direction'] + u'风' + result['wind_scale'] + u'级。'
		else:
			text += result['wind_direction'] + u'。'
		if result['precip'] == '':
			pass
		elif result['precip'] == '0':
			text += u'降水概率为0。'
		else:
			text += u'降水概率为' + result['precip'] + '%。'
		if int(result['high']) < 0:
			text += u'天气寒冷，建议着厚外套加毛衣等服装，要注意预防感冒哦。'
		elif int(result['high']) < 15:
			text += u'感觉有点凉，室外活动适当增加衣物哦。'
		elif int(result['high']) < 25:
			text += u'气温适宜。'
		elif int(result['high']) < 35:
			text += u'温度有点高，注意多喝水呀。'
		else:
			text += u'天气炎热，要预防中暑。'
		return text

	def write_weather_cache(self, res_json, answer, debug_info):
		"""将查询到的天气结果写入缓存中，并返回用户查询日期的天气结果
		Args:
			res_json: API的json结果
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		"""
		city = debug_info['standard_city']
		Weather.rsc().city_weather_cache[city] = {}
		all_text = ''
		for i in range(len(res_json['results'][0]['daily'])):
			if i == 0:
				text = self.generte_weather_text(res_json['results'][0]['daily'][i], u'今天')
				all_text += text
				Weather.rsc().city_weather_cache[city][u'今天'] = []
				Weather.rsc().city_weather_cache[city][u'今天'].append((res_json['results'][0]['daily'][i]["date"], text))
			if i == 1:
				text = self.generte_weather_text(res_json['results'][0]['daily'][i], u'明天')
				all_text += text
				Weather.rsc().city_weather_cache[city][u'明天'] = []
				Weather.rsc().city_weather_cache[city][u'明天'].append((res_json['results'][0]['daily'][i]["date"], text))
			if i == 2:
				text = self.generte_weather_text(res_json['results'][0]['daily'][i], u'后天')
				all_text += text
				Weather.rsc().city_weather_cache[city][u'后天'] = []
				Weather.rsc().city_weather_cache[city][u'多天'] = []
				Weather.rsc().city_weather_cache[city][u'后天'].append((res_json['results'][0]['daily'][i]["date"], text))
				Weather.rsc().city_weather_cache[city][u'多天'].append((res_json['results'][0]['daily'][i]["date"], text))
			if debug_info['real_date'] == res_json['results'][0]['daily'][i]["date"]:
				answer = city + text
		return answer, debug_info

	def get_weather_result(self, res_str, query, params, debug_info):
		"""解析API结果，并返回用户查询日期的天气结果
		Args:
			res_str: API结果，json格式的字符串
			query: 原始query，编码Unicode
			params: query的预处理结果
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		Raises:
		"""
		answer = None
		if res_str != '' and res_str != None:
			res_json = json.loads(res_str)
			debug_info['sub_type'] = debug_info['result_type'] = u'天气'
			if 'status_code' in res_json and 'status_code' in API_STATUS_CODE:
				debug_info['status'] = API_STATUS_CODE['status_code']
			else:
				answer, debug_info = self.write_weather_cache(res_json, answer, debug_info)
		return [(answer, debug_info)]

	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {"from":self.acc_name}
		try:
			if query == 'flushweatherapi':
				Weather.rsc().city_weather_cache = {}
			intent_flag, answer, debug_info = self.weather_intention_judgement(query, params, debug_info)
			if intent_flag:
				url = '%s?key=caftgjiqz5uqfmru&location=%s&language=zh-Hans&unit=c&start=0&days=3' % (self._conf.HTTP_WEATHER, urllib.quote_plus(debug_info['standard_city'].encode('utf-8')))
				async_reqs_param = [AsyncReqsParam("GET", url, None, None)]
				results = yield parallel_async(async_reqs_param, wait_for_all=True)
				for res_str, req_info in results:
					debug_info["req_info"] = req_info
					if res_str:
						ret_list = self.get_weather_result(res_str, query, params, debug_info)
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
	weather = Weather(conf)
	weather()
	querys = [u'北京天气', u'博鳌天气', u'海南热吗', u'这个', u'今天天气']
	querys = [u'32号你等着', u'13月12号天气']
	querys = [u'北京天气', u'北京明天天气', u'海淀多少度', u'18号北京天气', u'5月17北京天气', u'5月19北京天气', u'2017年5月13北京天气', u'帮我查查今天的天气', u'天气', u'2018年7月17号天气']
