#coding=utf-8

from __future__ import division
import pickle
try:
	import xml.etree.cElementTree as ET
except ImportError:
	import xml.etree.ElementTree as ET

from accessor import *
import common_method as comm
from trie import *


time_format = '%Y-%m-%d %H:%M:%S'
headers = {"Content-type": "application/x-www-form-urlencoded;charset=gbk"}
tsinghua_qa_file = os.path.join(curr_dir, '../../data/tsinghua_qa/tsinghua_json.utf8')
tsinghua_image_file = os.path.join(curr_dir, '../../data/tsinghua_qa/image_map.txt')
tsinghua_default_qa_file = os.path.join(curr_dir, '../../data/tsinghua_qa/tsinghua_pattern_json.utf8')
text_dir = os.path.join(curr_dir, '../../data/tsinghua_qa/text/')

random_image = [
		'dalitang.jpg',
		'erxiaomen.jpg',
		'gongziting.jpg',
		'guyuetang.jpg',
		'jinchunyuan.jpg',
		'kexueguan.jpg',
		'liujiao.jpg',
		'lixueyuanlou.jpg',
		'meishuxueyuan.jpg',
		'qinghualu.jpg',
		'qinghuaxiaoshi.jpg',
		'qinghuaxuetang.jpg',
		'qixiangtai.jpg',
		'shuimuqinghua.jpg',
		'tushuguan.jpg',
		'wentingzhongsheng.jpg',
		'xitiyuguan.jpg',
		'yuanlin.jpg',
		'zhulou.jpg',
		'zijingongyuqu.jpg',
]


class TsinghuaQa(Accessor):
	class Resource(Accessor.Resource):
		def tsinghua_qa_init(self):
			'''加载清华入学小助手qa数据
			'''
			inputs = open(tsinghua_qa_file, 'r')
			data = json.load(inputs, encoding='utf-8')
			self.precise_query = data['query']
			self.answer_list = data['answer']
			self.pattern_list = data['pattern']
			self.pattern_words = data['pattern_words']
			self.file_dict = data['file_dict']
			TsinghuaQa.rsc().pattern_tree.add_exist_tree(pickle.loads(data['pattern_tree']))
			inputs.close()
			self.file_update_time[0] = os.stat(tsinghua_qa_file).st_mtime

		def init_image_map(self):
			'''加载清华入学小助手图片信息
			'''
			inputs = open(tsinghua_image_file, 'r')
			for line in inputs:
				items = line.strip().split('\t')
				if len(items) != 2:
					continue
				self.image_map[items[0]] = items[1]
			inputs.close()
			self.file_update_time[1] = os.stat(tsinghua_image_file).st_mtime

		def tsinghua_default_qa_init(self):
			'''加载清华入学小助手qa兜底数据
			'''
			inputs = open(tsinghua_default_qa_file, 'r')
			data = json.load(inputs, encoding='utf-8')
			self.default_answer_list = data['answer']
			self.default_pattern_list = data['pattern']
			self.default_pattern_words = data['pattern_words']
			self.default_file_dict = data['file_dict']
			self.default_pattern_tree.add_exist_tree(pickle.loads(data['pattern_tree']))
			inputs.close()
			self.file_update_time[2] = os.stat(tsinghua_default_qa_file).st_mtime

		def init(self):
			begin = time.time()
			self.file_update_time = [0.0, 0.0, 0.0]		#文件最新编辑时间, 第一个是qa_file, 第二个是image_file, 第三个是default_qa
			self.precise_query = {}			#query和norm_query以及对应的answer_id, 编码Unicode, {precise_query:[note, answer_id], ...}
			self.answer_list = {}			#answer_id到answer的映射, 编码Unicode, {answer_id:{content:[], ...}, ...}
			self.pattern_list = []			#pattern集合以及对应的answer_id, 编码Unicode, [[pattern, answer_id, pattern_id], ...]
			self.pattern_words = {}			#pattern词以及在pattern_list的位置, 编码Unicode, {pattern_word:{pattern_id:'', ...}, ,,,}
			self.file_dict = {}				#文章对应列表，文章名对应标题和图片, {file_name:{title, image}}
			self.pattern_tree = TagMake()	#pattern词对应的trie树, 编码Unicode
			self.image_map = {}				#清华入学小助手图片映射信息
			self.default_answer_list = {}			#answer_id到answer的映射, 编码Unicode, {answer_id:{content:[], ...}, ...}
			self.default_pattern_list = []			#pattern集合以及对应的answer_id, 编码Unicode, [[pattern, answer_id, pattern_id], ...]
			self.default_pattern_words = {}			#pattern词以及对应pattern_list的id, 编码Unicode, {pattern_word:{pattern_id:'', ...}, ,,,}
			self.default_file_dict = {}				#文章对应列表，文章名对应标题和图片, {file_name:{title, image}}
			self.default_pattern_tree = TagMake()	#pattern词对应的trie树, 编码Unicode
			try:
				self.tsinghua_qa_init()
				self.init_image_map()
				self.tsinghua_default_qa_init()
			except Exception, e:
				exclog.error('\n%s' % (traceback.format_exc(e)))
			edit_time = time.strftime(time_format, time.localtime(self.file_update_time[0])) + '|' + time.strftime(time_format, time.localtime(self.file_update_time[1])) + '|' + time.strftime(time_format, time.localtime(self.file_update_time[2]))
			cost = str(int(round(time.time()-begin, 3)*1000))
			detlog.info('[accessor_init] [tsinghua_qa] [file_edit_time=%s] [cost=%sms]' % (edit_time, cost))

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)

	def check_file_is_update(self):
		begin = time.time()
		if TsinghuaQa.rsc().file_update_time[0] != os.stat(tsinghua_qa_file).st_mtime:
			#self.tsinghua_qa_init()
			cost = str(int(round(time.time()-begin, 3)*1000))
			edit_time = time.strftime(time_format, time.localtime(TsinghuaQa.rsc().file_update_time[0]))
			detlog.info('[accessor_reload] [tsinghua_qa] [qa_file_edit_time=%s] [cost=%sms]' % (edit_time, cost))
		if TsinghuaQa.rsc().file_update_time[1] != os.stat(tsinghua_image_file).st_mtime:
			#self.init_image_map()
			cost = str(int(round(time.time()-begin, 3)*1000))
			edit_time = time.strftime(time_format, time.localtime(TsinghuaQa.rsc().file_update_time[1]))
			detlog.info('[accessor_reload] [tsinghua_qa] [image_file_edit_time=%s] [cost=%sms]' % (edit_time, cost))
		if TsinghuaQa.rsc().file_update_time[2] != os.stat(tsinghua_default_qa_file).st_mtime:
			#self.tsinghua_default_qa_init()
			cost = str(int(round(time.time()-begin, 3)*1000))
			edit_time = time.strftime(time_format, time.localtime(TsinghuaQa.rsc().file_update_time[2]))
			detlog.info('[accessor_reload] [tsinghua_qa] [qa_file_edit_time=%s] [cost=%sms]' % (edit_time, cost))

	def answer_process(self, answer_id, answer, debug_info, answer_list):
		'''每次随机选取一个answer, 并处理answer中包含的模板信息
		Args:
			answer_id: query对应的answer_id
			answer: answer, 编码Unicode
			debug_info: debug信息
			answer_list: 存放answer的dict
		Returns:
			answer: answer, 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		answer = random.choice(answer_list[str(answer_id)]['content']).replace('<brbr>', '\n')
		debug_info['answer_id'] = answer_id
		if 'command' in answer_list[str(answer_id)]:
			command = answer_list[str(answer_id)]['command']
			debug_info['card'] = {}
			debug_info['card']['tmpl'] = comm.get_between(command, '<tmpl>', '</tmpl>')
			if debug_info['card']['tmpl'] == 'map_list':
				debug_info['card']['cardTitle'] = comm.get_between(command, '<cardTitle>', '</cardTitle>')
			debug_info['card']['data'] = []
			_, results = comm.get_between_all(command, '<data>', '</data>')
			types = comm.get_between(command, '<type>', '</type>')
			for each in results:
				title = comm.get_between(each, '<title>', '</title>')
				image = comm.get_between(each, '<image>', '</image>')
				point = comm.get_between(each, '<point>', '</point>')
				content = comm.get_between(each, '<content>', '</content>').replace('<brbr>', '\n')
				if image in TsinghuaQa.rsc().image_map:
					image = TsinghuaQa.rsc().image_map[image].replace('http', 'https')
				if content.find('|') != -1:
					items = content.split('|')
					for item in items:
						detail = {}
						detail['title'] = title
						detail['image'] = image
						detail['content'] = item
						debug_info['card']['data'].append(detail)
				else:
					detail = {}
					detail['title'] = title
					if image == '' and debug_info['card']['tmpl'] == 'article_single':
						image = random.choice(random_image)
						if image in TsinghuaQa.rsc().image_map:
							image = TsinghuaQa.rsc().image_map[image].replace('http', 'https')
					detail['image'] = image
					if point != '':
						pos = point.find(',')
						if pos != -1:
							detail['longitude'] = point[0:pos]
							detail['latitude'] = point[pos+1:]
					if types != '':
						detail['type'] = types
					if content.find('.txt') != -1:
						detail['content'] = ''
						detail['fileName'] = content
					else:
						detail['content'] = content
					debug_info['card']['data'].append(detail)
		return answer, debug_info

	def get_file_content(self, file_name, answer, debug_info):
		'''读取文章内容
		Args:
			file_name: 读取的文章名
			answer: answer, 编码Unicode
			debug_info: debug信息
		Returns:
			answer: answer, 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		if os.path.isfile(text_dir + file_name) == False:
			return None, debug_info
		answer = 'read_file'
		debug_info['card'] = {}
		debug_info['card']['tmpl'] = ''
		debug_info['card']['data'] = []
		detail = {}
		detail['title'] = TsinghuaQa.rsc().file_dict[file_name]['title']
		detail['image'] = TsinghuaQa.rsc().file_dict[file_name]['image']
		if detail['image'] in TsinghuaQa.rsc().image_map:
			detail['image'] = TsinghuaQa.rsc().image_map[detail['image']].replace('http', 'https')
		detail['content'] = open(text_dir + file_name, 'r').read()
		debug_info['card']['data'].append(detail)
		return answer, debug_info

	def is_precise_qa_query(self, query, params, answer, debug_info):
		'''是否是qa精准query
		Args:
			query: 原始query, 编码Unicode
			params: query相关信息
			answer: answer, 编码Unicode
			debug_info: debug信息
		Returns:
			answer: answer, 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		query = query.replace('\t', '').replace(' ', '')
		if query in TsinghuaQa.rsc().precise_query:
			answer_id = TsinghuaQa.rsc().precise_query[query]
			answer, debug_info = self.answer_process(answer_id, answer, debug_info, TsinghuaQa.rsc().answer_list)
		if answer == None:
			norm_query = comm.get_norm_query(params['seg'])
			if norm_query in TsinghuaQa.rsc().precise_query:
				answer_id = TsinghuaQa.rsc().precise_query[norm_query]
				answer, debug_info = self.answer_process(answer_id, answer, debug_info, TsinghuaQa.rsc().answer_list)
		if answer != None:
			detlog.info('[accessor_INFO] [tsinghua_qa] [query=%s] [answer_id=%s] precise query' % (query.encode('utf-8'), debug_info['answer_id']))
		return answer, debug_info

	def choose_match_best_pattern(self, results, query, answer, debug_info):
		'''选择最优pattern
		Args:
			results: trie树结果
			query: 原始query, 编码Unicode
			answer: answer, 编码Unicode
			debug_info: debug信息
		Returns:
			answer: answer, 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		pattern_id = -1
		max_length = -1
		max_num = -1
		patternid_pattern = {}			#命中的pattern text {pattern_id:{pattern}}
		all_hit = {}					#命中所有pattern的list {pattern_id:}
		log_str = '[accessor_INFO] [tsinghua_qa] [query=%s] [patterns=' % (query.encode('utf-8'))
		for each in results:
			pattern = each[0]
			if pattern in TsinghuaQa.rsc().pattern_words:
				for list_id in TsinghuaQa.rsc().pattern_words[pattern]:
					list_id = int(list_id)
					if list_id not in patternid_pattern:
						patternid_pattern[list_id] = dict()
					patternid_pattern[list_id][pattern] = 0
					if len(TsinghuaQa.rsc().pattern_list[list_id][0]) == len(patternid_pattern[list_id]):
						all_hit[list_id] = len(TsinghuaQa.rsc().pattern_list[list_id][0])
		for each in all_hit:
			log_str += ' (' + str(each) + ':' + ' '.join(TsinghuaQa.rsc().pattern_list[each][0]) + ':' + str(TsinghuaQa.rsc().pattern_list[each][1]) + ')'
			if pattern_id == -1:
				pattern_id = each
				max_num = all_hit[each]
				max_length = len(''.join(TsinghuaQa.rsc().pattern_list[each][0]))
			elif max_num < all_hit[each]:
				pattern_id = each
				max_num = all_hit[each]
				max_length = len(''.join(TsinghuaQa.rsc().pattern_list[each][0]))
			elif max_num == all_hit[each]:
				if max_length < len(''.join(TsinghuaQa.rsc().pattern_list[each][0])):
					pattern_id = each
					max_num = all_hit[each]
					max_length = len(''.join(TsinghuaQa.rsc().pattern_list[each][0]))
		log_str += ' ]'
		if pattern_id != -1:
			answer_id = TsinghuaQa.rsc().pattern_list[pattern_id][1]
			answer, debug_info = self.answer_process(answer_id, answer, debug_info, TsinghuaQa.rsc().answer_list)
		if answer != None:
			debug_info['pattern_id'] = pattern_id
			debug_info['status'] = 'from pattern'
			log_str += ' [answer_id=%s] pattern' % str(debug_info['answer_id'])
		detlog.info(log_str)
		return answer, debug_info

	def is_match_qa_pattern(self, query, params, answer, debug_info):
		'''是否命中qa的pattern
		Args:
			query: 原始query, 编码Unicode
			params: query相关信息
			answer: answer, 编码Unicode
			debug_info: debug信息
		Returns:
			answer: answer, 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		result = self.pattern_tree.make_all(query)
		if len(result) == 0:
			debug_info['status'] = 'not match tsinghua qa query and pattern'
			detlog.info('[accessor_INFO] [tsinghua_qa] [query=%s] not match' % (query.encode('utf-8')))
		else:
			detlog.info('[accessor_INFO] [tsinghua_qa] [query=%s] [patterns=%s]' % (query.encode('utf-8'), ' '.join(each[0] for each in result)))
			answer, debug_info = self.choose_match_best_pattern(result, query, answer, debug_info)
		return answer, debug_info

	def match_process(self, query, params, answer, debug_info):
		'''匹配qa数据
		Args:
			query: 原始query, 编码Unicode
			params: query相关信息
			answer: answer, 编码Unicode
			debug_info: debug信息
		Returns:
			answer: answer, 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		answer = None
		answer, debug_info = self.is_precise_qa_query(query, params, answer, debug_info)
		if answer == None:
			answer, debug_info = self.is_match_qa_pattern(query, params, answer, debug_info)
		return answer, debug_info

	def format_search_query(self, query, params):
		'''去掉维秘检索时无用的词语
		Args:
			query: 原始query，编码Unicode
			params: query的预处理结果
		Returns:
			result: 维秘检索时的query，编码Unicode
		Raises:
		'''
		result = ''
		segs = params['seg']
		for seg in segs:
			if seg[1] == 27 or seg[1] == 34 or seg[1] == 36:
				continue
			result += seg[0]
		return result

	def get_each_tsinghua_qa_result(self, query, res_str):
		'''解析searchhub检索返回的xml结果
		Args:
			query: 原始query，编码Unicode
			res_str: searchhub检索返回的xml结果，编码Unicode
		Returns:
			results: list形式返回所有结果，其中的每一个元素由(title, content, trank, rel, index, extraR, docId, url)组成。
		Raises:
		'''
		results = []
		res_str = comm.get_between_longest(res_str, '<doc', '</doc>')
		if res_str == '' or res_str == None:
			return results
		items = res_str.split('<doc')
		for (index, item) in enumerate(items):
			if item.find('docId') != -1:
				docId = comm.get_between(item, 'docId="', '">')
			if item.find('<rank') != -1:
				part = '<rank' + comm.get_between(item, '<rank', '</rank>') + '</rank>'
				root = ET.fromstring(part)
				trank = root.attrib['TRank']
				extraR = root.attrib['ExtraR']
			if item.find('<url>') != -1:
				url = comm.get_between(item, '<url><![CDATA[', ']]></url>')
			if item.find('<title>') != -1:
				title = comm.get_between(item, '<title><![CDATA[', ']]></title>')
				title = title.replace(u'\uff00', '')
				title, rel = comm.process_title_from_search_pair(title)
				title = comm.strQ2B(title)
			if item.find('<content>') != -1:
				content = comm.get_between(item, '<content><![CDATA[', ']]></content>')
				content = comm.strQ2B(content.replace(u'\ue40b','').replace(u'\ue40a','').replace(u'\uff00', ''))
			results.append((title, content, trank, rel, index, extraR, docId, url))
		return results

	def is_high_quality_answer(self, result, query):
		'''通过trank和extra判断answer质量
		Args:
			result: 一条结果的所有解析内容
			query: 原始query，编码Unicode
		Returns:
			flag: True表示answer质量较高，反之为False
			status: 过滤原因
		Raises:
		'''
		flag = True
		status = ''
		extra = -1
		if float(result[2]) < 3:
			flag = False
			status = 'low trank(' + str(result[2]) + ')'
		else:
			try:
				extra = int(result[5][4:6], 16)
			except:
				extra = -1
			if extra < 5:
				flag = False
				status = 'low extraR(' + result[5] + ')'
		return flag, status, extra

	def parse_tsinghua_qa_result(self, res_str, query, answer, debug_info):
		'''解析searchhub检索返回的xml结果，并选取一条回答
		Args:
			res_str: searchhub检索返回的xml结果，编码Unicode
			query: 原始query，编码Unicode
			answer: answer, 编码Unicode
			debug_info: debug信息
		Returns:
			answer: answer, 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		results = self.get_each_tsinghua_qa_result(query, res_str)
		source_num = len(results)
		log_str = ''
		if len(results) == 0:
			debug_info['status'] = 'empty result list'
			log_str += '[accessor_INFO] [tsinghua_qa] [query=%s] no doc\n' % (query.encode('utf-8'))
		else:
			log_filter = ''
			#log_candidate = ''
			for result in results:
				if result[1] == '' or result[1] == None:
					log_filter += '[accessor_INFO] [tsinghua_qa] [FILTER] [index=%s] [answer=%s] [query=%s] [title=%s] empty answer\n' % (str(result[4]), str(result[1]).replace('\n', '').encode('utf-8'), query.encode('utf-8'), result[0].encode('utf-8'))
					continue
				qua_flag, qua_status, extra = self.is_high_quality_answer(result, query)
				if qua_flag == False:
					log_filter += '[accessor_INFO] [tsinghua_qa] [FILTER] [index=%s] [answer=%s] [query=%s] [title=%s] %s\n' % (str(result[4]), str(result[1]).replace('\n', '').encode('utf-8'), query.encode('utf-8'), result[0].encode('utf-8'), qua_status)
					continue
				answer_id = result[1][12:]
				answer, debug_info = self.answer_process(answer_id, answer, debug_info, TsinghuaQa.rsc().answer_list)
				debug_info['title'] = result[0]
				debug_info['trank'] = result[2]
				debug_info['rel'] = result[3]
				debug_info['index'] = result[4]
				debug_info['extraR'] = result[5]
				debug_info['docID'] = result[6]
				debug_info['url'] = result[7]
				debug_info['extra'] = extra
				debug_info['answer_id'] = answer_id
				#log_candidate += '[accessor_INFO] [tsinghua_qa] [candidate] [index=%s] [answer=%s] [query=%s] [title=%s]\n' % (str(result[4]), str(result[1]).replace('\n', '').encode('utf-8'), query.encode('utf-8'), result[0].encode('utf-8'))
				break
			log_str += '***********************************************tsinghua qa filter***********************************************\n'
			log_str += log_filter
			#log_str += '*********************************************tsinghua qa candidate**********************************************\n'
			#log_str += log_candidate
			log_str += '****************************************************************************************************************\n'
		log_str += '[accessor_INFO] [tsinghua_qa] [final] [query=%s] [answer_id=%s]' % (query.encode('utf-8'), debug_info.get('answer_id', 'no'))
		detlog.info(log_str)
		return answer, debug_info


	def choose_default_match_best_pattern(self, results, query, answer, debug_info):
		'''选择最优pattern
		Args:
			results: trie树结果
			query: 原始query, 编码Unicode
			answer: answer, 编码Unicode
			debug_info: debug信息
		Returns:
			answer: answer, 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		pattern_id = -1
		max_length = -1
		max_num = -1
		patternid_pattern = {}			#命中的pattern text {pattern_id:{pattern}}
		all_hit = {}					#命中所有pattern的list {pattern_id:}
		log_str = '[accessor_INFO] [tsinghua_qa] [query=%s] [patterns=' % (query.encode('utf-8'))
		for each in results:
			pattern = each[0]
			if pattern in TsinghuaQa.rsc().default_pattern_words:
				for list_id in TsinghuaQa.rsc().default_pattern_words[pattern]:
					list_id = int(list_id)
					if list_id not in patternid_pattern:
						patternid_pattern[list_id] = dict()
					patternid_pattern[list_id][pattern] = 0
					if len(TsinghuaQa.rsc().default_pattern_list[list_id][0]) == len(patternid_pattern[list_id]):
						all_hit[list_id] = len(TsinghuaQa.rsc().default_pattern_list[list_id][0])
		for each in all_hit:
			log_str += ' (' + str(each) + ':' + ' '.join(TsinghuaQa.rsc().default_pattern_list[each][0]) + ':' + str(TsinghuaQa.rsc().default_pattern_list[each][1]) + ')'
			if pattern_id == -1:
				pattern_id = each
				max_num = all_hit[each]
				max_length = len(''.join(TsinghuaQa.rsc().default_pattern_list[each][0]))
			elif max_num < all_hit[each]:
				pattern_id = each
				max_num = all_hit[each]
				max_length = len(''.join(TsinghuaQa.rsc().default_pattern_list[each][0]))
			elif max_num == all_hit[each]:
				if max_length < len(''.join(TsinghuaQa.rsc().default_pattern_list[each][0])):
					pattern_id = each
					max_num = all_hit[each]
					max_length = len(''.join(TsinghuaQa.rsc().default_pattern_list[each][0]))
		log_str += ' ]'
		if pattern_id != -1:
			answer_id = TsinghuaQa.rsc().default_pattern_list[pattern_id][1]
			answer, debug_info = self.answer_process(answer_id, answer, debug_info, TsinghuaQa.rsc().default_answer_list)
		if answer != None:
			debug_info['pattern_id'] = pattern_id
			debug_info['status'] = 'from pattern'
			log_str += ' [answer_id=%s] default pattern' % str(debug_info['answer_id'])
		detlog.info(log_str)
		return answer, debug_info

	def is_match_default_qa_pattern(self, query, params, answer, debug_info):
		'''是否命中qa的pattern
		Args:
			query: 原始query, 编码Unicode
			params: query相关信息
			answer: answer, 编码Unicode
			debug_info: debug信息
		Returns:
			answer: answer, 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		result = TsinghuaQa.rsc().default_pattern_tree.make_all(query)
		if len(result) == 0:
			debug_info['status'] = 'not match default tsinghua qa query and pattern'
			detlog.info('[accessor_INFO] [tsinghua_qa] [query=%s] not match' % (query.encode('utf-8')))
		else:
			answer, debug_info = self.choose_default_match_best_pattern(result, query, answer, debug_info)
		return answer, debug_info

	def get_tsinghua_qa_result(self, res_str, query, params, debug_info):
		rets = []
		answer = None
		if res_str == None or res_str == '':
			debug_info['status'] = 'empty search content'
			detlog.info('[accessor_INFO] [tsinghua_qa] [query=%s] empty search content' % (query.encode('utf-8')))
		else:
			res_str = res_str.decode('utf-16', 'ignore')
			answer, debug_info = self.parse_tsinghua_qa_result(res_str, query, answer, debug_info)
		if answer == None:
			answer, debug_info = self.is_match_default_qa_pattern(query, params, answer, debug_info)
		rets = [(answer, debug_info)]
		return rets

	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {"from":self.acc_name}
		try:
			answer = None
			debug_info['sub_type'] = u'清华-问答'
			#self.check_file_is_update()
			if query.find('.txt') != -1 and query.find('.txt') + 4 == len(query) and params.get('tsinghua_querytype', '') == 'article':
				answer, debug_info = self.get_file_content(query, answer, debug_info)
			if answer == None:
				answer, debug_info = self.match_process(query, params, answer, debug_info)
			if answer == None or answer == '':
				url = self._conf.TSINGHUA_QA_ADDR
				query_gbk = self.format_search_query(query, params).strip().lower().encode('gbk', 'ignore')
				data = 'queryFrom=web&queryType=query&queryString=%s&forceQuery=1' % (urllib.quote_plus(query_gbk))
				async_reqs_param = [AsyncReqsParam("POST", url, data, headers)]
				results = yield parallel_async(async_reqs_param, wait_for_all=True)
				for res_str, req_info in results:
					debug_info["req_info"] = req_info
					if res_str:
						ret_list = self.get_tsinghua_qa_result(res_str, query, params, debug_info)
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
		source = 'tsinghua_robot'
		querytype = 'article'
		while True:
			print '>>>>>>>>>>>>>>>>'
			query = raw_input("query:").decode("utf-8")
			begin = time.time()
			query = get_query_correction(query, source, querytype)
			params = preprocessing(query, source)
			params['tsinghua_querytype'] = querytype
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
	tsinghua_qa = TsinghuaQa(conf)
	tsinghua_qa()
