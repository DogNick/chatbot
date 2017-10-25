#!/usr/bin/env python
#coding=utf8

from accessor import *
import common_method as comm


time_format = '%Y-%m-%d %H:%M:%S'
all_time_format = '%Y年%m月%d日 %A %H:%M:%S'
headers = {'User-Agent':'Mozilla/5.0 (Windows; U; Windows NT 6.1; en-US; rv:1.9.1.6) Gecko/20091201 Firefox/3.5.6'}
capital_dir = os.path.join(curr_dir, '../../data/universal_time/country_capital.utf8')
city_dir = os.path.join(curr_dir, '../../data/universal_time/universal_city.utf8')

p_blacklist1 = re.compile(u'升起|降落|开门|营业|打烊|流星雨|日全食|日出|日落|多久|多长时间|起止|起始|截止|建军|纪念|开始|结束|爆发|战争|发现')
p_time_strong= re.compile(u'几点|(到(早上|中午|晚上|)(0|1|2|3|4|5|6|7|8|9|10|11|12|13|14|15|16|17|18|19|20|21|22|23|24|零|一|两|二|三|四|五|六|七|八|九|十|十一|十二|十三|十四|十五|十六|十七|十八|十九|二十|二十一|二十二|二十三|二十四)点)|((到|离|)(天黑|天亮)(.*?)(了吗|了么|了吧|多久|多长时间))')
p_time_weak = re.compile(u'时间')
p_time_answer = re.compile(u'(\d{4}年\d{2}月\d{2}日) (星期(一|二|三|四|五|六|七|日|天)) (\d{2}:\d{2}:\d{2})')


class UniversalTime(Accessor):
	class Resource(Accessor.Resource):
		def load_capital_words(self):
			inputs = open(capital_dir, 'r')
			for line in inputs:
				items = line.strip().decode('utf-8').split('\t')
				country = items[0]
				city = items[1]
				if country not in self.country_capital:
					self.country_capital[country] = city

		def load_city_words(self):
			city_str = ''
			island_str = ''
			country_str = ''
			inputs = open(city_dir, 'r')
			for line in inputs:
				line = line.strip().decode('utf-8')
				items = line.split('\t')
				if len(items) != 4:
					continue
				island = items[0]
				country = items[1]
				city = items[2]
				city_id = items[3]
				if city_id == '':
					continue
				if island != '' and island not in self.island_country:
					self.island_country[island] = dict()
					island_str += island + '|'
				if country != '' and country not in self.island_country[island]:
					self.island_country[island][country] = 0
					country_str += country + '|'
				if city != '':
					if city not in self.city_cityID:
						self.city_cityID[city] = dict()
						city_str += city + '|'
					self.city_cityID[city][country] = city_id
				if city_id != '':
					new_city = []
					new_city.append(city_id)
					if city_id.find('-') != -1:
						new_city.append(city_id.replace('-', ' '))
						pos = city_id.rfind('-')
						if pos + 2 == len(city_id)-1:
							new_city.append(city_id[0:pos].replace('-', ' '))
					for each in new_city:
						if each == '':
							continue
						if each not in self.city_cityID:
							self.city_cityID[each] = dict()
							city_str += each + '|'
						self.city_cityID[each][country] = city_id
			if island_str != '':
				self.p_island = re.compile(island_str[:-1])
			if country_str != '':
				self.p_country = re.compile(country_str[:-1])
			if city_str != -1:
				self.p_city = re.compile(city_str[:-1])

		def init(self):
			begin = time.time()
			self.country_capital = {}		#{国家:首都}, Unicode
			self.city_cityID = {}			#{city:{country:{city_id}}},city有可能重名,一个city可能对应一个或多个country到city_id的映射
			self.island_country = {}		#{island:{country}},洲到国家的映射
			self.p_city = None				#所有城市的正则表达式
			self.p_island = None
			self.p_country = None
			try:
				self.load_capital_words()
				self.load_city_words()
			except Exception, e:
				exclog.error('\n%s' % (traceback.format_exc(e)))
			cost = str(int(round(time.time()-begin, 3)*1000))
			detlog.info('[accessor_init] [universal_time] [cost=%sms]' % (cost))

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)
		self.acc_name = 'universal_time'

	def is_contain_word(self, query, p_tmp):
		m = p_tmp.search(query)
		if m == None:
			return None
		return m.group(0)

	def get_city_id(self, query, debug_info):
		city_id = ''
		city = debug_info['city']
		country = debug_info['country']
		island = debug_info['island']
		if city != None:
			if country != None:
				city_id = UniversalTime.rsc().city_cityID[city][country]
			else:
				for each in UniversalTime.rsc().city_cityID[city]:
					city_id = UniversalTime.rsc().city_cityID[city][each]
					break
		elif country != None:
			city = UniversalTime.rsc().country_capital[country]
			city_id = UniversalTime.rsc().city_cityID[city][country]
		elif island != None:
			for key in UniversalTime.rsc().island_country:
				country = UniversalTime.rsc().island_country[key]
				break
			city = UniversalTime.rsc().country_capital[country]
			city_id = UniversalTime.rsc().city_cityID[city][country]
		return city_id

	def extract_time_intention(self, query, params, debug_info):
		if self.is_contain_word(query, p_time_strong) != None:
			debug_info['time_flag'] = 'strong'
			debug_info['time_word'] = self.is_contain_word(query, p_time_strong)
		elif self.is_contain_word(query, p_time_weak) != None:
			debug_info['time_flag'] = 'weak'
			debug_info['time_word'] = self.is_contain_word(query, p_time_weak)
		else:
			debug_info['time_flag'] = None
			debug_info['time_word'] = None
			debug_info['status'] = 'no time word'
		return debug_info

	def extract_place_words(self, query, params, debug_info):
		debug_info['city'] = self.is_contain_word(query, UniversalTime.rsc().p_city)
		debug_info['country'] = self.is_contain_word(query, UniversalTime.rsc().p_country)
		debug_info['island'] = self.is_contain_word(query, UniversalTime.rsc().p_island)
		if debug_info['city'] == None and debug_info['country'] == None and debug_info['island'] == None:
			debug_info['city_flag'] = None
		else:
			debug_info['city_flag'] = 'single'
			if debug_info['city'] != None:
				other_city =  UniversalTime.rsc().p_city.search(query, query.find(debug_info['city'])+len(debug_info['city']))
				if other_city != None:
					debug_info['city_flag'] = 'multi'
					debug_info['status'] = 'too many city'
		debug_info['city_id'] = self.get_city_id(query, debug_info)
		return debug_info

	def time_intention_judgement(self, query, params, debug_info):
		answer = None
		if len(query) < 4:
			debug_info['status'] = 'query too short'
			return False, answer, debug_info
		if p_blacklist1.search(query) != None:
			debug_info['status'] = 'query has time blacklist word[' + p_blacklist1.search(query).group(1) + ']'
			return False, answer, debug_info
		debug_info = self.extract_time_intention(query, params, debug_info)
		if debug_info['time_flag'] == None:
			return False, answer, debug_info
		debug_info = self.extract_place_words(query, params, debug_info)
		if debug_info['city_flag'] == 'multi':
			return False, answer, debug_info
		if debug_info['time_flag'] == 'weak' and debug_info['city_flag'] == None:
			debug_info['status'] = 'weak time flag, no location'
			return False, answer, debug_info
		if debug_info['time_flag'] == 'weak' and debug_info['city_flag'] == 'single':
			pos_b = -1
			pos_e = query.find(debug_info['time_word'])
			if debug_info['city'] != None:
				pos_b = query.find(debug_info['city']) + len(debug_info['city'])
			elif debug_info['country'] != None:
				pos_b = query.find(debug_info['country']) + len(debug_info['country'])
			elif debug_info['island'] != None:
				pos_b = query.find(debug_info['island']) + len(debug_info['island'])
			if pos_e - pos_b > 2:
				debug_info['status'] = 'weak time flag, city distance is too far'
				return False, answer, debug_info
		if debug_info['time_flag'] == 'strong' and debug_info['city_flag'] == None:
			if params.get('source', '') == 'qcloud':
				struct_time = time.localtime()
				answer = u'现在是北京时间: ' + str(struct_time[3]) + u'点'
				if int(struct_time[4]) > 0:
					answer += u'%02d分' % int(struct_time[4])
			else:
				answer = u'现在是北京时间: ' + time.strftime(time_format)
			debug_info['sub_type'] = debug_info['result_type'] = u'世界时间'
			return False, answer, debug_info
		return True, answer, debug_info

	def get_universal_time_result(self, res_str, query, params, debug_info):
		answer = None
		if res_str != '' and res_str != None:
			res_str = res_str.decode('gbk', 'ignore')
			debug_info['sub_type'] = debug_info['result_type'] = u'世界时间'
			if res_str.find(u'<div class="qh_left_s"><h4>') != -1:
				debug_info['place'] = comm.get_between(res_str, u'<div class="qh_left_s"><h4>', u'</h4></div>')
				items = debug_info['place'].split(' ')
				if len(items) == 4:
					debug_info['place'] = items[0] + items[2]
			if res_str.find(u'<li><b>当地时间</b><p id="clock" class="time">') != -1:
				answer = comm.get_between(res_str, u'<li><b>当地时间</b><p id="clock" class="time">', u'</p></li>')
				if params.get('source', '') == 'qcloud':
					match = p_time_answer.search(answer)
					if match != None:
						struct_time = time.strptime(match.group(1)+' '+match.group(4), u'%Y年%m月%d日 %H:%M:%S')
						answer = str(struct_time[1]) + u'月' + str(struct_time[2]) + u'日' + str(struct_time[3]) + u'点'
						if int(struct_time[4]) > 0:
							answer += u'%02d分' % int(struct_time[4])
				answer = debug_info['place'] + u'现在时间是: ' + answer
			if res_str.find(u'<li><b>所处时区</b><p>') != -1:
				debug_info['time_zone'] = comm.get_between(res_str, u'<li><b>所处时区</b><p>', '</p></li>').replace('<br>','')
			if res_str.find(u'<li><b>和北京时差</b><p>') != -1:
				debug_info['jet_lag'] = comm.get_between(res_str, u'<li><b>和北京时差</b><p>', '</p></li>').replace('<br>','')
			if res_str.find(u'<li><b>天气情况</b><p>') != -1:
				debug_info['weather'] = comm.get_between(res_str, u'<li><b>天气情况</b><p>', '</p></li>').replace('<br>','')
			if res_str.find(u'<li><b>电话区号</b><p>') != -1:
				debug_info['area_code'] = comm.get_between(res_str, u'<li><b>电话区号</b><p>', '</p></li>').replace('<br>','')
			if res_str.find(u'<li><b>日出日落</b><p>') != -1:
				debug_info['sunrise_sunset'] = comm.get_between(res_str, u'<li><b>日出日落</b><p>', '</p></li>')
			if res_str.find(u'<li><b>经纬度坐标</b><p>') != -1:
				debug_info['coordinate'] = comm.get_between(res_str, u'<li><b>经纬度坐标</b><p>', '</p></li>')
		return [(answer, debug_info)]

	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {"from":self.acc_name}
		try:
			intent_flag, answer ,debug_info = self.time_intention_judgement(query, params, debug_info)
			if intent_flag:
				url = self._conf.UNIVERSAL_TIME_URL + debug_info['city_id'] + '/'
				async_reqs_param = [AsyncReqsParam("GET", str(url), None, headers)]
				results = yield parallel_async(async_reqs_param, wait_for_all=True)
				for res_str, req_info in results:
					debug_info["req_info"] = req_info
					if res_str:
						ret_list = self.get_universal_time_result(res_str, query, params, debug_info)
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
		source = 'qcloud'
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
	conf = Config("dev",  True, "develop")
	universal_time = UniversalTime(conf)
	universal_time()
	querys = [u'北京时间', u'巴黎时间', u'美国时间', u'迪拜现在几点了', u'澳洲现在是几点', u'澳洲时间']
