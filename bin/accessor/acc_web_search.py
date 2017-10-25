#coding=utf-8

'''
	数据来源: 线上网页搜索(search)和线下问答检索(原yaoting)
'''

from __future__ import division
from accessor import *
import common_method as comm
import string_process as str_judge
import web_search_parse_lizhi as lizhi
import web_search_parse_vr as vr
import web_search_answer_quality_judgement as ans_judge


headers = {"Content-type": "application/x-www-form-urlencoded;charset=gbk"}
filter_pattern_dir = os.path.join(curr_dir, '../../data/web_search/filter_pattern')
html_symbol_dir = os.path.join(curr_dir, '../../data/web_search/html_symbol')
baike_item_dir = os.path.join(curr_dir, '../../data/web_search/baike_item.utf8')
baike_click_log_dir = os.path.join(curr_dir, '../../data/web_search/baike_click_log.utf8')

QUERY_TYPE_FILTER = True		#是否按query类型过滤
ANSWER_PRIORITY = {
		'lizhi':(1, 'precise', 'text', u'问答-WEB-立知'),				#lizhi
		'VR':(2, 'precise', 'text', u'问答-WEB-VR'),					#VR文本数据, 排名前3位, index <= 3
		'VR_map_1':(3, 'precise', 'link', u'问答-WEB-地图VR'),			#地图VR, query_type==7, e.g."怎么去五道口"
		'VR_url':(4, 'precise', 'link', u'问答-WEB-VR'),				#包含url的VR
		'VR_afanti':(4, 'precise', 'text', u'问答-WEB-VR'),				#【糖猫】服务专用，成语解释
		'baike':(5, 'precise', 'text', u'问答-WEB-百科'),				#百科, 排名前4位, index <= 4
		'zhinan':(6, 'ugc', 'text', u'问答-WEB-指南'),					#搜狗指南, 百度经验
		'lizhi_support':(7, 'ugc', 'text', u'问答-WEB-立知'),			#lizhi支持文本
		'lizhi_census':(8, 'ugc', 'text', u'问答-WEB-立知-观点'),		#lizhi观点类
		'lizhi_ugc':(9, 'ugc', 'text', u'问答-WEB-立知-ugc'),			#lizhi_ugc
		'long_list':(10, 'ugc', 'text', u'问答-WEB-长答案'),			#长答案, 列表类
		'VR_video':(11, 'precise', 'link', u'问答-WEB-视频VR'),			#视频VR, 视频播放类
		'VR_rank':(12, 'precise', 'text', u'问答-WEB-弱VR'),			#排序比较靠后
		'VR_map_2':(13, 'precise', 'link', u'问答-WEB-地图VR'),			#地图VR, query_type!=7, e.g."泰山在哪里"
		'lizhi_other':(14, 'other', 'other', u'问答-WEB-立知其他'),		#lizhi其他情况
		'VR_other':(15, 'other', 'other', u'问答-WEB-VR其他'),			#VR其他情况
		'baike_other':(16, 'precise', 'text', u'问答-WEB-弱百科'),		#百科, 排名第五位以后, index >= 5
		'wenda':(17, 'ugc', 'text', u'问答-线下-ugc'),					#线下问答结果(原yaoting)
		'qa':(18, 'ugc', 'text', u'问答-WEB-ugc'),						#问答文本, 如知道、问问等
}


class WebSearch(Accessor):
	class Resource(Accessor.Resource):
		def load_filter_pattern(self):
			"""加载需要过滤或截取的pattern
			Args:
			Returns:
			Raises:
			"""
			answer_pattern = ''
			title_cut_pattern = ''
			inputs = open(filter_pattern_dir, 'r')
			for line in inputs:
				if line.find('#') == 0:
					continue
				line = line.strip().decode('utf-8')
				items = line.split('\t')
				if len(items) == 2:
					if items[1] == 'title':
						self.query_filter[items[0]] = 0
					elif items[1] == 'answer':
						answer_pattern += items[0] + '|'
					elif items[1] == 'title_cut':
						title_cut_pattern += items[0] + '|'
			answer_pattern = answer_pattern[0:len(answer_pattern)-1]
			title_cut_pattern = title_cut_pattern[0:len(title_cut_pattern)-1]
			self.p_answer_filter = re.compile(answer_pattern)
			self.p_title_cut_down = re.compile(title_cut_pattern)
			inputs.close()

		def load_html_symbol(self):
			"""加载需要替换的HTML的标记
			Args:
			Returns:
			Raises:
			"""
			inputs = open(html_symbol_dir, 'r')
			for line in inputs:
				line = line[:-1].decode('utf-8')
				items = line.split('\t')
				self.html_symbol[items[0]] = items[1]
			inputs.close()

		def load_baike_related_information(self):
			"""加载百科词条名, 百科点击日志
			Args:
			Returns:
			Raises:
			"""
			inputs = open(baike_item_dir, 'r')
			for line in inputs:
				line = line.strip().decode('utf-8')
				self.baike_item[line] = '1'
			inputs.close()
			inputs = open(baike_click_log_dir, 'r')
			for i, line in enumerate(inputs):
				line = line[:-1].decode('utf-8')
				self.baike_click_log[line] = '1'
			inputs.close()

		def init(self):
			begin = time.time()
			self.query_filter = {}				#query过滤词表, Unicode
			self.p_answer_filter = None			#answer过滤正则表达式, Unicode
			self.p_title_cut_down = None		#检索到的title标注的来源, 用于截取title, Unicode
			self.html_symbol = {}				#需要替换的html标签, Unicode
			self.baike_item = {}				#百科词条名, Unicode
			self.baike_click_log = {}			#百科点击日志, 字典结构，(key:百科query，value:百科点击率)，编码utf-8
			try:
				self.load_filter_pattern()
				self.load_html_symbol()
				self.load_baike_related_information()
			except Exception, e:
				exclog.error('\n%s' % (traceback.format_exc(e)))
			cost = str(int(round(time.time()-begin, 3)*1000))
			detlog.info('[accessor_init] [web_search] [cost=%sms]' % (cost))

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)
		self.acc_name = 'web_search'

	def query_initial_judge(self, query, params, debug_info):
		"""query初始判断, 过滤表情以及包含某些词语的query
		Args:
			query: 编码Unicode
			params: query相关处理结果
			debug_info: debug信息
		Returns:
			req_flag: 是否需要请求搜索
			debug_info: debug信息
		Raises:
		"""
		req_flag = True
		# 过滤表情query
		if query.find('[') == 0 and query.find(']') == len(query)-1:
			req_flag = False
			debug_info['status'] = 'query may be emoji'
		else:
			# 过滤包含某些词语的query
			for seg in params.get('seg', []):
				if seg[0] in WebSearch.rsc().query_filter:
					req_flag = False
					debug_info['status'] = 'title filter(' + seg[0] + ')'
					break
		return req_flag, debug_info

	def get_baike_weight(self, line):
		"""获取线上检索结果的baikeinfos的weight值
		Args:
			line: searchhub结果
		Returns:
			baike_weight: 获取检索结果的TRank值，未找到返回0.0
		"""
		baike_weight = 0.0
		tmp = comm.get_between(line, '<baikeinfos><weight value="', '"/></baikeinfos>')
		if tmp != '':
			baike_weight = float(tmp)
		return baike_weight

	def get_rank_infos(self, line):
		"""获取检索结果的TRank值
		Args:
			line: rank信息
		Returns:
			trank: 获取检索结果的TRank值，未找到返回0.0
			extraR: 获取检索结果的ExtraR值，未找到返回''
		Raises:
		"""
		trank = 0.0
		extraR = ''
		extra_dic = {'a':10, 'b':11, 'c':12, 'd':13, 'e':14, 'f':15}
		tmp = comm.get_between(line, 'TRank="', '"')
		if tmp != '':
			trank = float(tmp)
		tmp = comm.get_between(line, 'ExtraR="', '"')
		if tmp != '':
			extraR = tmp[4:6]
		return trank, extraR

	def get_wenda_feature(self, item):
		"""获取检索结果的wendaF值
		Args:
			item: 检索的debug信息
		Returns:
			wendaF: 获取检索结果的wendaF值，未找到返回0
		Raises:
		"""
		wendaF = 0
		if item.find('wendaF0') != -1:
			wendaF += 1
		if item.find('wendaF1') != -1:
			wendaF += 2
		if item.find('wendaF2') != -1:
			wendaF += 4
		return wendaF

	def get_sub_type_id(self, url):
		'''根据url得到站点的名字
		Args:
			url: 落地页url
		Returns:
			sub_type_id: answer站点的名字
		Raises:
		'''
		sub_type_id = ''
		p_sub_type = re.compile('(((http|https)://)|)(www\.|)(.*?)(\.com|\.cn|\.net)')
		match = p_sub_type.search(url)
		if match != None:
			sub_type_id = match.group(5)
		return sub_type_id

	def get_title(self, content):
		"""处理检索到的title，并计算相似度
		Args:
			content: 检索到的title，编码Unicode
		Returns:
			title: 处理后的title，编码Unicode
			rel: 相似度
		Raises:
		"""
		title = ''
		rel = 0.0
		if content != '' and content != None:
			content = comm.strQ2B(content)
			match = WebSearch.rsc().p_title_cut_down.search(content)
			if match:
				pos = content.find(match.group(0))
				if pos != -1:
					content = content[0:pos]
			title, rel = comm.process_title_from_search_pair(content)
		return title, rel

	def replace_html_symbol(self, answer):
		"""替换answer中的HTML标记
		Args:
			content: 检索到的answer，编码Unicode
		Returns:
			answer: 处理后的answer，编码Unicode
		Raises:
		"""
		pos1 = answer.find('&')
		pos2 = answer.find(';', pos1)
		while pos1 != -1 and pos2 != -1:
			tmp = answer[pos1:pos2+1]
			if tmp in WebSearch.rsc().html_symbol:
				answer = answer.replace(tmp, WebSearch.rsc().html_symbol[tmp])
			else:
				break
			pos1 = answer.find('&')
			pos2 = answer.find(';', pos1)
		return answer

	def get_answer(self, content):
		"""处理检索到的answer，替换HTML标记和标红信息
		Args:
			content: 检索到的answer，编码Unicode
		Returns:
			answer: 处理后的answer，编码Unicode
		Raises:
		"""
		answer = ''
		answer = comm.strQ2B(content.strip())
		answer = answer.replace(u'\u3000', '').replace(u'\ue40a', '').replace(u'\ue40b', '')
		answer = answer.replace(u'<em>', '').replace(u'</em>', '')
		if answer.find(u'&') != -1:
			answer = self.replace_html_symbol(content)
		return answer

	def get_answer_final(self, answer, debug_info):
		"""处理answer中的标红信息，判断answer是否完整
		Args:
			answer: 编码Unicode
			debug_info: 每条数据的debug信息
		Returns:
			answer: 编码Unicode
			debug_info: 每条数据的debug信息
		Raises:
		"""
		if answer != '' and answer != None:
			answer = self.get_answer(answer)
			if 'orig' not in debug_info:
				debug_info['orig'] = answer
			flag, answer = str_judge.get_complete_sentence(answer)
			debug_info['details'] = flag
		return answer, debug_info

	def extract_basic_infos(self, data, debug_info):
		"""解析检索通用的一些字段
		Args:
			data: 每条数据的xml数据，编码Unicode
			debug_info: debug信息
		Returns:
			debug_info: debug信息
		Raises:
		"""
		debug_info['trank'], debug_info['extraR'] = self.get_rank_infos(comm.get_between(data, u'<rank', '>'))
		debug_info['wendaF'] = self.get_wenda_feature(comm.get_between(data, u'<debug', '>'))
		debug_info['tplid'] = comm.get_between(data, '<tplid>', '</tplid>')
		debug_info['url'] = comm.get_between(data, '<url><![CDATA[', ']]></url>')
		debug_info['sub_type_id'] = self.get_sub_type_id(debug_info['url'])
		debug_info['title'] = comm.get_between(data, '<title><![CDATA[', ']]></title>')
		debug_info['title'], debug_info['rel'] = self.get_title(debug_info['title'])
		return debug_info

	def parse_baike(self, data, query, params, answer, debug_info):
		"""解析百科类型的xml数据
		Args:
			data: 每条数据的xml数据，编码Unicode
			query: query，编码Unicode
			params: query预处理信息
			answer: 编码Unicode
			debug_info: 每条数据的debug信息
		Returns:
			answer: 编码Unicode
			debug_info: 每条数据的debug信息
		Raises:
		"""
		answer = comm.get_between(data, '<content161><![CDATA[', ']]></content161>')
		debug_info['baike_image'] = comm.get_between(data, '<cardimage><![CDATA[', ']]></cardimage>')
		debug_info['orig'] = answer
		# 人名地名
		if query in WebSearch.rsc().baike_item or comm.get_norm_query(params['seg']) in WebSearch.rsc().baike_item:
			debug_info['details_baike'] = 'query in baike item'
		elif debug_info['title'].strip() in WebSearch.rsc().baike_item:
			debug_info['details_baike'] = 'title in baike item'
		elif answer.find(u'歌曲') != -1 or answer.find(u'连载') != -1:
			answer = None
			debug_info['details_baike'] = 'baike type filter'
		elif len(query) == 1:
			answer = None
			debug_info['details_baike'] = 'query length is 1'
		elif len(query) == len(params['seg']):
			answer = None
			debug_info['details_baike'] = 'query length is equal to seg number'
		elif len(params['seg']) == 1 and (acc_params['seg'][0][1] < 17 or acc_params['seg'][0][1] > 22):
			answer = None
			debug_info['details_baike'] = 'one word pos(' + str(acc_params['seg'][0][1]) + ')'
		elif debug_info['baike_weight'] < 0.8:
			answer = None
			debug_info['details_baike'] = 'low baike weight'
		elif query in WebSearch.rsc().baike_click_log and debug_info['baike_weight'] < 0.9:
			answer = None
			debug_info['details_baike'] = 'low baike click'
		# 云小微接口只出明确百科意图的数据
		if params['source'] == 'qcloud' and debug_info['title'].find(query) != -1:
			answer = None
			debug_info['details_baike'] = 'qcloud baike filter'
		if debug_info['index'] <= 4:
			debug_info['priority_id'] = 'baike'
		else:
			debug_info['priority_id'] = 'baike_other'
		return answer, debug_info

	def parse_jingyan_or_zhinan(self, data, answer, debug_info):
		"""解析经验或指南的xml数据
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug_info信息
		Returns:
			answer: 编码Unicode
			debug_info: debug_info信息
		Raises:
		"""
		answer = ''
		answer2 = ''
		debug_info['priority_id'] = 'zhinan'
		answerlist = comm.get_between(data, '<answerlist>', '</answerlist>')
		flag, items = comm.get_between_all(answerlist, '<![CDATA[', ']]>')
		flag2, itemlinks = comm.get_between_all(data, '<itemlink>', '</itemlink>')
		if flag:
			for (i, item) in enumerate(items):
				item = self.get_answer(item)
				flag, new_answer = str_judge.get_complete_sentence(item)
				if new_answer != '':
					answer += str(i+1) + '. ' + new_answer + '\n'
		if flag2:
			for (i, item) in enumerate(itemlinks):
				each = comm.get_between(item, '<content><![CDATA[', ']]></content>')
				each = self.get_answer(each)
				flag, new_answer = str_judge.get_complete_sentence(each)
				if new_answer == '':
					answer2 = ''
					break
				else:
					answer2 += str(i+1) + '. ' + new_answer + '\n'
		if answer2 != '' and len(itemlinks) > len(items):
			answer = answer2
		if answer != '':
			debug_info['orig'] = answer
			if debug_info['query_type'] == 0 or debug_info['query_type'] == 1:
				answer = None
				debug_info['details_zhinan'] = 'query type(' + str(debug_info['query_type']) + ')'
		debug_info['orig'] = answer
		return answer, debug_info

	def parse_long_list_answer(self, data, answer, debug_info):
		"""
			功能: 解析长答案或列表性答案的xml数据
		Args:
			data: 每条数据的xml数据，编码Unicode
			answer: 编码Unicode
			debug_info: debug_info信息
		Returns:
			answer: 编码Unicode
			debug_info: debug_info信息
		Raises:
		"""
		answer = ''
		debug_info['priority_id'] = 'long_list'
		content = comm.get_between(data, '<answer><![CDATA[', ']]></answer>')
		answerlist = content.split('<p>')
		for each in answerlist:
			each = self.get_answer(each)
			flag, new_answer = str_judge.get_complete_sentence(each)
			if new_answer == '':
				answer += each + '\n'
			else:
				answer += new_answer + '\n'
		debug_info['orig'] = answer
		return answer, debug_info

	def parse_online_ugc_answer(self, data, query, params, answer, debug_info):
		'''解析线上检索问答类型的xml数据
		qab=1时，answer=youzhicontent
		isContentBestAnswer=-1时，answer=None
		Args:
			data: 每条数据的xml数据，编码Unicode
			query: query，编码Unicode
			params: query预处理信息
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			answer: 编码Unicode
			debug_info: debug信息
		'''
		answer = comm.get_between(data, u'<content><![CDATA[', u']]></content>')
		debug_info['qab'] = comm.get_between(data, '<qab>', '</qab>')
		debug_info['youzhicontent'] = comm.get_between(data, u'<youzhiContent><![CDATA[', u']]></youzhiContent>')
		debug_info['isContentBestAnswer'] = comm.get_between(data, u'<isContentBestAnswer><![CDATA[', u']]></isContentBestAnswer>')
		debug_info['orig'] = answer
		debug_info['priority_id'] = 'qa'
		if debug_info['isContentBestAnswer'] == '-1':
			answer = None
			debug_info['details_ugc'] = 'isContentBestAnswer is -1'
		elif debug_info['qab'] == '1' and debug_info['youzhicontent'] != '':
			answer = debug_info['youzhicontent']
			debug_info['details_ugc'] = 'use youzhicontent'
		return answer, debug_info

	def parse_each_content_online(self, data, query, params, debug_info):
		"""解析每条xml数据
		Args:
			data: 每条数据的xml数据，编码Unicode
			query_utf8: query，编码Unicode
			params: query预处理信息
			debug_info: 每条数据的debug信息
		Returns:
			answer: 编码Unicode
			debug_info: 每条数据的debug信息
		Raises:
		"""
		answer = None
		source = params.get('source', '')
		if debug_info['index'] == 0:
			answer, debug_info = lizhi.parse_lizhi_answer(data, query, answer, debug_info)
			debug_info['title'], debug_info['rel'] = self.get_title(debug_info['title'])
			answer, debug_info = self.get_answer_final(answer, debug_info)
		elif data.find('classid') != -1 and data.find('classtag') != -1:
			answer, debug_info = vr.parse_vr_answer(data, query, answer, debug_info)
			debug_info['title'], debug_info['rel'] = self.get_title(debug_info['title'])
			answer, debug_info = self.get_answer_final(answer, debug_info)
		else:
			debug_info = self.extract_basic_infos(data, debug_info)
			if debug_info['sub_type_id'].find(u'baike') != -1:
				answer, debug_info = self.parse_baike(data, query, params, answer, debug_info)
				answer, debug_info = self.get_answer_final(answer, debug_info)
			elif debug_info['sub_type_id'] == 'zhinan.sogou' or debug_info['sub_type_id'] == 'jingyan.baidu':
				answer, debug_info = self.parse_jingyan_or_zhinan(data, answer, debug_info)
			elif debug_info['tplid'] == '5003' or debug_info['tplid'] == '5009':
				answer, debug_info = self.parse_long_list_answer(data, answer, debug_info)
			else:
				answer, debug_info = self.parse_online_ugc_answer(data, query, params, answer, debug_info)
				answer, debug_info = self.get_answer_final(answer, debug_info)
		debug_info['result_type'] = u'问答-' + debug_info['priority_id']
		debug_info['priority'] = ANSWER_PRIORITY[debug_info['priority_id']][0]
		debug_info['sub_type'] = ANSWER_PRIORITY[debug_info['priority_id']][3]
		if ANSWER_PRIORITY[debug_info['priority_id']][1] == 'precise':
			debug_info['is_ugc'] = False
		# 糖猫希望多出指南类数据
		if debug_info['priority_id'] == 'zhinan' and (source == 'aiplatform_qa' or source == 'aiplatform_teemo'):
			debug_info['is_ugc'] = False
		return answer, debug_info

	def init_re_list_by_priority(self, n):
		re_list = []
		for i in range(n):
			re_list.append((i+1, []))
		return re_list

	def parse_content_online(self, res_str, query, params, final_debug_info):
		"""解析线上检索返回的每条数据并判断质量
		Args:
			res_str: 检索xml数据，编码Unicode
			query: 编码Unicode
			params: query相关信息
			final_debug_info: debug信息
		Returns:
			rets: list [(answer, debug_info)], answer编码Unicode, debug_info是字典结构
		Raises:
		"""
		rets = []
		final_answer = None
		final_debug_info['baike_weight'] = self.get_baike_weight(res_str)
		final_debug_info['query_type'] = params.get('query_classify', {}).get('query_type', -1)
		re_list = self.init_re_list_by_priority(len(ANSWER_PRIORITY))		#按答案优先级存放每一条结果
		flag, items = comm.get_between_all(comm.get_between(res_str, '', '<tupudoc>'), '<doc docId=', '</doc>')
		items.insert(0, comm.get_between(res_str, '<tupudoc>', '</tupudoc>'))
		log_str = '[accessor_DEBUG] [web_search] [online] [query=%s]\n' % (query.encode('utf-8'))
		log_filter = ''
		log_candidate = ''
		default = {'extraR':'', 'rel':-1.0, 'trank':-1.0, 'wendaF':-1, 'priority':100, 'is_ugc':True, 'status':'has result'}
		for (index, item) in enumerate(items):
			answer = None
			debug_info = {}
			debug_info['index'] = index
			debug_info['use_ugc_conf'] = self._conf.SEARCH_USE_UGC_ANSWER
			debug_info['q_type_filter'] = QUERY_TYPE_FILTER
			debug_info.update(default)
			debug_info.update(final_debug_info)
			answer, debug_info = self.parse_each_content_online(item, query, params, debug_info)
			answer, debug_info = ans_judge.judge_online_answer_quality(query, params, answer, debug_info, WebSearch.rsc().p_answer_filter)
			re_list[debug_info['priority']-1][1].append((answer, debug_info))
			if answer != None and debug_info['status'] == 'has result':
				if 'orig' in debug_info:
					del debug_info['orig']
				if final_answer == None or final_debug_info['priority'] > debug_info['priority']:
					final_answer = answer
					final_debug_info = debug_info
			if debug_info['status'] == 'has result':
				log_candidate += '[web_search_online] [CANDIDATE] [index=%s] [answer=%s] [debug=%s]\n' % (
					str(debug_info['index']), str(answer).replace('\n', ''), json.dumps(debug_info, ensure_ascii=False, sort_keys=True))
			else:
				log_filter += '[web_search_online] [FILTER] [index=%s] [answer=%s] [debug=%s]\n' % (
					str(debug_info['index']), str(answer).replace('\n', ''), json.dumps(debug_info, ensure_ascii=False, sort_keys=True))
		log_str += '*******************************************************************************************\n'
		log_str += log_filter
		log_str += '*******************************************************************************************\n'
		log_str += log_candidate
		log_str += '*******************************************************************************************\n'
		log_str += '[accessor_INFO] [web_search] [online] [query=%s] [answer=%s] [debug=%s]\n' % (
			query.encode('utf-8'), str(final_answer).replace('\n', ''), json.dumps(final_debug_info, ensure_ascii=False, sort_keys=True))
		if self._conf._verbose:
			detlog.info(log_str)
		rets = [(final_answer, final_debug_info)]
		if self._conf.SEARCH_DEBUG_FLAG == True:
			for each in re_list:
				for item in each[1]:
					if final_debug_info.get('index', '') == item[1]['index']:
						continue
					rets.append(item)
		return rets

	def parse_content_wenda(self, res_str, query, params, debug_info):
		"""解析线下问答检索(原yaoting)
		Args:
			res_str: 检索xml数据，编码Unicode
			query: 编码Unicode
			params: query相关信息
			debug_info: debug信息
		Returns:
			rets: list [(answer, debug_info)], answer编码Unicode, debug_info是字典结构
		Raises:
		"""
		return []

	def get_web_search_result(self, res_str, query, params, debug_info):
		"""解析检索结果，包含线上检索和线下问答检索(原yaoting)
		Args:
			res_str: 检索xml数据，编码Unicode
			query: 编码Unicode
			params: query相关信息
			debug_info: debug信息
		Returns:
			rets: list [(answer, debug_info)], answer编码Unicode, debug_info是字典结构
		Raises:
		"""
		answer = None
		rets = []
		if res_str != '' and res_str != None:
			res_str = res_str.decode('utf-16', 'ignore')
			if debug_info['req_info']['id'] == 0:
				debug_info['origin'] = 'online'
				rets = self.parse_content_online(res_str, query, params, debug_info)
			elif debug_info['req_info']['id'] == 1:
				debug_info['origin'] = 'wenda'
				rets = self.parse_content_wenda(res_str, query, params, debug_info)
		else:
			debug_info['status'] = 'empty res_str'
			rets = [(answer, debug_info)]
		return rets

	def select_viewpoint_query_tag(self, params, answer, debug_info):
		"""返回观点类问题的随机tag
		Args:
			params: query相关信息
			answer: 编码Unicode
			debug_info: debug信息
		Returns:
			rets: list [(answer, debug_info)], answer编码Unicode, debug_info是字典结构
		Raises:
		"""
		answers = [
				u'？我猜的对不对？',
				u'？我随便选一个吧。',
				u'？我随便说哒，我不会对这个答案负责的。',
				u'？我猜的，我其实还不太懂。'
		]
		query_type = params.get('query_classify', {}).get('query_type', -1)
		if query_type == 2 or query_type == 3 or query_type == 13:		#是观点类问题
			answer = random.choice(params['query_classify']['tag'])
			if answer != '' and answer != None:
				answer += random.choice(answers)
				debug_info['sub_type_id'] = 'query classify'
				debug_info['sub_type'] = u'问答-WEB-分类'
				debug_info['result_type'] = u'问答-ugc'
				debug_info['is_ugc'] = True
			else:
				answer = None
		return [(answer, debug_info)]

	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {"from":self.acc_name}
		try:
			req_flag, debug_info = self.query_initial_judge(query, params, debug_info)
			if req_flag:
				url_1 = self._conf.HTTP_WEB_SEARCH
				url_2 = self._conf.HTTP_YAOTING
				req_query = urllib.quote_plus(query.strip().lower().encode('gbk', 'ignore'))
				data_1 = 'queryFrom=web&queryType=query&tupu=1&start=0&end=10&queryString=%s' % req_query
				data_2 = 'queryFrom=web&queryType=query&forceQuery=1&start=0&end=10&magic=exp_id:64,exp_flag:exp_QueryIsWangZaiWenDa=1&queryString=%s' % req_query
				detlog.info('[accessor_INFO] [web_search] [requests_params] [url=%s] [data=%s]' % (url_1, data_1))
				detlog.info('[accessor_INFO] [web_search] [requests_params] [url=%s] [data=%s]' % (url_2, data_2))
				async_reqs_param = [AsyncReqsParam("POST", url_1, data_1, headers), AsyncReqsParam("POST", url_2, data_2, headers)]
				results = yield parallel_async(async_reqs_param, wait_for_all=True)
				for res_str, req_info in results:
					debug_info["req_info"] = req_info
					if res_str:
						ret_list = self.get_web_search_result(res_str, query, params, debug_info)
						rets.extend(ret_list)
			else:
				detlog.info('[accessor_INFO] [web_search] [query=%s] [status=%s]' % (query.encode('utf-8'), debug_info['status'].encode('utf-8')))
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
	conf._verbose = 1
	conf.SEARCH_DEBUG_FLAG = False
	conf.SEARCH_USE_UGC_ANSWER = True
	web_search = WebSearch(conf)
	web_search()

