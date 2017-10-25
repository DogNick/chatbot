#coding=utf-8

'''
	author: cuiyanyan
	功能: 维秘的需求(维秘白名单 -> 工单查询 -> 维秘faq检索 -> 判断领域分类 -> 判断是否为运维问题)
'''

from __future__ import division
from ctypes import cdll, c_char_p
import pickle
try:
	import xml.etree.cElementTree as ET
except ImportError:
	import xml.etree.ElementTree as ET

from accessor import *
import common_method as comm
import tencent_segment as tc_seg
from trie import *


headers = {"Content-type": "application/x-www-form-urlencoded;charset=gbk"}
weimi_white_dir = os.path.join(curr_dir, '../../data/weimi/weimi_whitelist_json.utf8')
weimi_order_dir = os.path.join(curr_dir, '../../data/weimi/weimi_order_number.utf8')
weimi_category_dir = os.path.join(curr_dir, '../../data/weimi/weimi_category.utf8')
weimi_op_lib_dir = os.path.join(curr_dir, '../../lib/classifier/libOpQueryClassify.so')
weimi_op_data_dir = os.path.join(curr_dir, '../../data/weimi/op_classifier_svm_dir')

class Weimi(Accessor):
	class Resource(Accessor.Resource):
		def load_weimi_whitelist(self):
			"""加载维秘白名单数据
			Args:
			Returns:
			Raises:
			"""
			inputs = open(weimi_white_dir, 'r')
			white_json = json.load(inputs, encoding='utf-8')
			self.pattern_list = white_json['pattern_list']
			self.pattern_words = white_json['pattern_words']
			self.precise_words = white_json['precise_words']
			self.answer_list = white_json['answer_list']
			self.pattern_tree.add_exist_tree(pickle.loads(white_json['pattern_tree']))
			inputs.close()

		def load_weimi_inquire_data(self):
			"""加载维秘查订单相关数据
			Args:
			Returns:
			Raises:
			"""
			weimi_order_str = ''
			infile = open(weimi_order_dir, 'r')
			for line in infile:
				items = line[:-1].lower().decode('utf-8').split('\t')
				if len(items) != 2:
					continue
				weimi_order_str += items[1] + '|'
			if weimi_order_str != '':
				weimi_order_str = weimi_order_str[:-1]
				self.p_weimi_order = re.compile('(' + weimi_order_str + ')' + '(\d{12})($|\D)')
				self.p_weimi_order_weak = re.compile('(' + weimi_order_str + ')' + '(\d+)')
			infile.close()

		def load_weimi_category_tags(self):
			"""加载维秘领域分类相关数据
			Args:
			Returns:
			Raises:
			"""
			infile = open(weimi_category_dir, 'r')
			for line in infile:
				items = line[:-1].lower().decode('utf-8').split('\t')
				if len(items) != 3:
					continue
				category = items[0]
				father_category = items[1]
				tags = items[2]
				if category == father_category or category == '':
					continue
				self.category_father[category] = father_category
				self.category_tag_tree.add_tag(category)
				if tags == '':
					continue
				tag_parts = tags.split(';')
				for part in tag_parts:
					if part == '':
						continue
					self.category_tag_tree.add_tag(part)
					if part not in self.tag_category:
						self.tag_category[part] = []
					self.tag_category[part].append(category)
			infile.close()

		def init_weimi_op_classifier(self):
			"""加载维秘是否为运维问题分类器
			Args:
			Returns:
			Raises:
			"""
			self.weimi_op_lib = cdll.LoadLibrary(weimi_op_lib_dir)
			if self.weimi_op_lib.op_svm_init(weimi_op_data_dir) == -1:
				self.weimi_op_init_flag = False

		def init(self):
			begin = time.time()
			self.pattern_list = []		#(list)白名单pattern以及对应的answer_id，编码Unicode
			self.pattern_words = {}		#(dict)白名单pattern word以及对应的pattern_id，编码Unicode
			self.precise_words = {}		#(dict)白名单精准匹配词条以及对应的answer_id，编码Unicode
			self.answer_list = {}		#(dict)白名单的answer，编码Unicode
			self.pattern_tree = TagMake()
			self.p_order_intention = re.compile(u'(查|查询|查看|看|看一下|查一下|我的|我滴|roc)(.*?)(工单|单号|单子|单)')	#查询订单意图的正则表达式
			self.p_weimi_order = None			# 查询订单号标准的正则表达式
			self.p_weimi_order_weak = None		# 查询订单号非标准的正则表达式
			#查询运维负责人的正则表达式
			self.p_search_people1 = re.compile(u'(请问|我想问下|我想问问|)(.*?)(的|(这个(.*)|)|)((运维(负责人|经理|接口人|))|接口人)(((是|找)(谁|))|)')
			self.p_search_people2 = re.compile(u'(请问|我想问下|我想问问|)(.*?)((((的|)问题|有问题|我|这个(.*)|)(应该|能|可以|))|)(找谁|((是|)谁负责))')
			self.category_father = {}			#二级领域分类到一级领域分类对应关系，编码Unicode
			self.tag_category = {}				#tag到二级领域分类列表的对应关系，编码Unicode
			self.category_tag_tree = TagMake()	#trie树，包含所有二级领域分类名字和tag名字，编码Unicode
			self.weimi_op_init_flag = True
			self.weimi_op_lib = None
			try:
				self.load_weimi_whitelist()
				self.load_weimi_inquire_data()
				self.load_weimi_category_tags()
				self.init_weimi_op_classifier()
			except Exception, e:
				exclog.error('\n%s' % (traceback.format_exc(e)))
			cost = str(int(round(time.time()-begin, 3)*1000))
			detlog.info('[accessor_init] [weimi] [cost=%sms]' % (cost))

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)

	def match_weimi_whitelist_pattern(self, results):
		"""查看query命中的白名单pattern，并选出最优pattern
		Args:
			results: 原query中所有的pattern片段集合，编码Unicode，格式list的元素是元组
		Returns:
			pattern_list_id: 命中的pattern集合id，未命中返回-1
		Raises:
		"""
		pattern_list_id = -1
		max_length = -1
		max_num = -1
		patternid_pattern = {}			#命中的pattern text {list_id:{pattern}}
		all_hit = {}
		for each in results:
			pattern = each[0]
			if pattern in Weimi.rsc().pattern_words:
				for list_id in Weimi.rsc().pattern_words[pattern]:
					list_id = int(list_id)
					if list_id not in patternid_pattern:
						patternid_pattern[list_id] = dict()
					patternid_pattern[list_id][pattern] = 0
					if len(Weimi.rsc().pattern_list[list_id][0]) == len(patternid_pattern[list_id]):
						all_hit[list_id] = len(Weimi.rsc().pattern_list[list_id][0])
		for each in all_hit:
			if pattern_list_id == -1 or max_num < all_hit[each]:
				pattern_list_id = each
				max_num = all_hit[each]
				max_length = len(''.join(Weimi.rsc().pattern_list[each][0]))
			elif max_num == all_hit[each]:
				if max_length < len(''.join(Weimi.rsc().pattern_list[each][0])):
					pattern_list_id = each
					max_num = all_hit[each]
					max_length = len(''.join(Weimi.rsc().pattern_list[each][0]))
		return pattern_list_id

	def match_weimi_whitelist(self, query, params, answer, debug_info):
		"""查看query是否命中的白名单
		Args:
			query: 原query，编码Unicode
			params: query的预处理结果
			answer: answer，编码Unicode
			debug_info: debug信息
		Returns:
			rets: [(answer, debug_info)]，无结果时返回[]
		Raises:
		"""
		rets = []
		query_new = query.strip().lower()
		if query_new in Weimi.rsc().precise_words:
			answer = random.choice(Weimi.rsc().answer_list[str(Weimi.rsc().precise_words[query_new])])
			debug_info['status'] = 'precise whitelist'
			debug_info['whiteword'] = query_new.encode('utf-8')
		else:
			query_new2 = comm.get_norm_query(params['seg'])
			if query_new2 in Weimi.rsc().precise_words:
				answer = random.choice(Weimi.rsc().answer_list[str(Weimi.rsc().precise_words[query_new2])])
				debug_info['status'] = 'precise whitelist twice'
				debug_info['whiteword'] = query_new2.encode('utf-8')
			else:
				results = Weimi.rsc().pattern_tree.make_all(query_new)
				if len(results) > 0:
					pattern_list_id = self.match_weimi_whitelist_pattern(results)
					if pattern_list_id != -1:
						if float(len(''.join(Weimi.rsc().pattern_list[pattern_list_id][0]))/len(query_new)) >= 0.7:
							answer = random.choice(Weimi.rsc().answer_list[str(Weimi.rsc().pattern_list[pattern_list_id][1])])
							debug_info['status'] = 'query match whitelist pattern:' + str(pattern_list_id)
							debug_info['whiteword'] = ' '.join(Weimi.rsc().pattern_list[pattern_list_id][0])
		if answer != None and answer != '':
			answer = answer.replace('<brbr>', '\n')
			debug_info['from'] = 'weimi_whitelist'
			rets = [(answer, debug_info)]
		return rets

	def check_weimi_order(self, query, params, answer, debug_info):
		"""查看query是否是查询订单意图
		Args:
			query: 原query，编码Unicode
			params: query的预处理结果
			answer: answer，编码Unicode
			debug_info: debug信息
		Returns:
			rets: [(answer, debug_info)]，无结果时返回[]
		Raises:
		"""
		rets = []
		query_new = query.strip().lower()
		order = Weimi.rsc().p_weimi_order.search(query_new)
		order_weak = Weimi.rsc().p_weimi_order_weak.search(query_new)
		intent = Weimi.rsc().p_order_intention.search(query_new)
		if order != None:
			order_dic = {}
			new_query = query_new
			while True:
				if order != None:
					answer = order.group(1).upper() + order.group(2)
					if answer != order_weak.group(0).upper():		#order和order_weak是否对应同一个
						rets = []
						answer = u'您提供的工单号不对哦，请您检查一下。'
						debug_info['from'] = 'weimi_order'
						debug_info['status'] = 'order intention'
						rets = [(answer, debug_info)]
						break
					elif answer not in order_dic:
						debug_info['from'] = 'weimi_order'
						debug_info['status'] = 'order intention'
						rets.append((answer, debug_info))
						order_dic[answer] = 0
				else:
					if order_weak != None:
						rets = []
						category = u'您提供的工单号不对哦，请您检查一下。'
						debug_info['from'] = 'weimi_order'
						debug_info['status'] = 'order intention'
						rets = [(category, debug_info)]
					break
				new_query = new_query[new_query.find(answer.lower())+len(answer.lower()):]
				if new_query == '':
					break
				order = Weimi.rsc().p_weimi_order.search(new_query)
				order_weak = Weimi.rsc().p_weimi_order_weak.search(new_query)
		elif order_weak != None:
			answer = u'您提供的工单号不对哦，请您检查一下。'
			debug_info['from'] = 'weimi_order'
			debug_info['status'] = 'order intention'
			rets = [(answer, debug_info)]
		if rets == [] and intent != None:
			answer = 'all'
			debug_info['from'] = 'weimi_order'
			debug_info['status'] = 'order intention'
			rets = [(answer, debug_info)]
		return rets

	def check_search_people(self, query, params, answer, debug_info):
		"""查看query是否是查询运维负责人
		Args:
			query: 原query，编码Unicode
			params: query的预处理结果
			answer: answer，编码Unicode
			debug_info: debug信息
		Returns:
			rets: [(answer, debug_info)]，无结果时返回[]
		Raises:
		"""
		rets = []
		query_new = query.strip().lower()
		search1 = Weimi.rsc().p_search_people1.search(query_new)
		search2 = Weimi.rsc().p_search_people2.search(query_new)
		if search1 != None:
			answer = search1.group(2)
		elif search2 != None:
			answer = search2.group(2)
		if answer != None and answer != '':
			debug_info['from'] = 'weimi_people'
			debug_info['status'] = 'OP person'
			rets = [(answer, debug_info)]
		return rets

	def parse_weimi_category(self, query, params, answer, debug_info, low_trank_data=[]):
		"""判断query属于的领域分类
		检索前调用一次: 若query为一个英文单词时不调用
		检索后调用一次: 返回领域分类, 如果有检索到相似问题则返回
		Args:
			query: 原query，编码Unicode
			params: query的预处理结果
			answer: answer，编码Unicode
			debug_info: debug信息
			low_trank_data: low trank检索结果
		Returns:
			rets: [(answer, debug_info)]，无结果时返回[]
		Raises:
		"""
		rets = []
		if query == '' or query == None:
			return rets
		if query.lower() in Weimi.rsc().category_father:
			answer = Weimi.rsc().category_father[query.lower()] + '|' + query.lower()
			debug_info['status'] = 'precise category'
		else:
			norm_query = comm.get_norm_query(params['seg'])
			if norm_query in Weimi.rsc().category_father:
				answer = Weimi.rsc().category_father[norm_query] + '|' + norm_query
				debug_info['status'] = 'norm query is precise category'
			else:
				results = Weimi.rsc().category_tag_tree.make_all(query.lower())
				if len(results) > 0:
					suit_category = ''
					suit_tag_category = []
					for each in results:
						if each[0] in Weimi.rsc().category_father:
							if suit_category == '':
								suit_category = each[0]
							elif len(suit_category) < len(each[0]):
								suit_category = each[0]
						elif each[0] in Weimi.rsc().tag_category:
							if suit_tag_category == '':
								suit_tag_category = Weimi.rsc().tag_category[each[0]]
							elif len(suit_tag_category) < len(Weimi.rsc().tag_category[each[0]]):
								suit_tag_category = Weimi.rsc().tag_category[each[0]]
					if suit_category != '':
						answer = Weimi.rsc().category_father[suit_category] + '|' + suit_category
						debug_info['status'] = 'category'
					elif suit_tag_category != []:
						answer = Weimi.rsc().category_father[suit_tag_category[0]] + '|' + suit_tag_category[0]
						debug_info['status'] = 'tag'
		if answer != '' and answer != None:
			debug_info['from'] = 'weimi_category'
			if len(low_trank_data) != 0:
				debug_info['SQ'] = low_trank_data[0]
			rets = [(answer, debug_info)]
		return rets

	def check_weimi_op_query(self, query, params, answer, debug_info, low_trank_data=[]):
		"""判断query是否属于的运维问题
		Args:
			query: 原query，编码Unicode
			params: query的预处理结果
			answer: answer，编码Unicode
			debug_info: debug信息
			low_trank_data: low trank检索结果
		Returns:
			rets: [(answer, debug_info)]，无结果时返回[]
		Raises:
		"""
		rets = []
		if query == '' or query == None or Weimi.rsc().weimi_op_init_flag == False:
			return rets
		seg = tc_seg.seg_return_string(query)
		ret = Weimi.rsc().weimi_op_lib.op_query_classify(seg)
		if ret == 1:
			answer = 'OP'
			debug_info['status'] = 'op_classifier'
		else:
			debug_info['status'] = 'classifier result is chat'
		if answer != '' and answer != None:
			debug_info['from'] = 'weimi_category'
			if len(low_trank_data) != 0:
				debug_info['SQ'] = low_trank_data[0]
			rets.append((answer, debug_info))
		return rets

	def format_search_query(self, query, params):
		"""去掉维秘检索时无用的词语
		Args:
			query: 原query，编码Unicode
			params: query的预处理结果
		Returns:
			result: 维秘检索时的query，编码Unicode
		Raises:
		"""
		result = ''
		segs = params['seg']
		for seg in segs:
			if seg[1] == 27 or seg[1] == 34 or seg[1] == 36:
				continue
			result += seg[0]
		return result

	def get_each_weimi_faq_result(self, query, res_str):
		"""解析searchhub检索返回的xml结果
		Args:
			query: 原query，编码Unicode
			res_str: searchhub检索返回的xml结果，编码Unicode
		Returns:
			results: list形式返回所有结果，其中的每一个元素由(title, content, trank, rel, index, extraR, docId, url)组成。
		Raises:
		"""
		results = []
		if res_str == '' or res_str == None:
			return results
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
		"""通过trank和extra判断answer质量
		Args:
			query: 原query，编码Unicode
			res_str: searchhub检索返回的xml结果，编码Unicode
		Returns:
			flag: True表示answer质量较高，反之为False
			status: 过滤原因
		Raises:
		"""
		flag = True
		status = ''
		extraR = {'a':10, 'b':11, 'c':12, 'd':13, 'e':14, 'f':15}
		if float(result[2]) < 3:
			flag = False
			status = 'low trank(' + str(result[2]) + ')'
		return flag, status

	def parse_weimi_faq_result(self, res_str, query, debug_info):
		"""解析searchhub检索返回的xml结果，并选取至多两条回答
		Args:
			res_str: searchhub检索返回的xml结果，编码Unicode
			query: 原始query，编码Unicode
			debug_info: debug信息
		Returns:
			rets: [(answer, debug_info)]，无结果时返回[]
			low_trank_data: trank过低的检索结果
		Raises:
		"""
		answer = None
		rets = []
		low_trank_data = []
		results = self.get_each_weimi_faq_result(query, res_str)
		source_num = len(results)
		log_str = ''
		if len(results) == 0:
			debug_info['status'] = 'empty result list'
			log_str += '[accessor_INFO] [weimi] [faq] [query=%s] no doc\n' % (query.encode('utf-8'))
		else:
			answer_dic = {}
			log_filter = ''
			log_candidate = ''
			for result in results:
				if result[1] == '' or result[1] == None:
					log_filter += '[accessor_INFO] [weimi] [faq] [FILTER] [index=%s] [answer=%s] [query=%s] [title=%s] empty answer\n' % (str(result[4]), str(result[1]).replace('\n', '').encode('utf-8'), query.encode('utf-8'), result[0].encode('utf-8'))
					continue
				if result[1] in answer_dic:
					log_filter += '[accessor_INFO] [weimi] [faq] [FILTER] [index=%s] [answer=%s] [query=%s] [title=%s] answer exist\n' % (str(result[4]), str(result[1]).replace('\n', '').encode('utf-8'), query.encode('utf-8'), result[0].encode('utf-8'))
					continue
				qua_flag, qua_status = self.is_high_quality_answer(result, query)
				if qua_flag == False:
					log_filter += '[accessor_INFO] [weimi] [faq] [FILTER] [index=%s] [answer=%s] [query=%s] [title=%s] %s\n' % (str(result[4]), str(result[1]).replace('\n', '').encode('utf-8'), query.encode('utf-8'), result[0].encode('utf-8'), qua_status)
					if qua_status.find('low trank') != -1:
						low_trank_data.append({'title':result[0], 'answer':result[1]})
					continue
				answer = result[1]
				debug_info['from'] = 'weimi_faq'
				debug_info['title'] = result[0]
				debug_info['trank'] = result[2]
				debug_info['rel'] = result[3]
				debug_info['index'] = result[4]
				debug_info['extraR'] = result[5]
				debug_info['docID'] = result[5]
				debug_info['url'] = result[6]
				rets.append((answer, copy.deepcopy(debug_info)))
				log_candidate += '[accessor_INFO] [weimi] [faq] [result] [index=%s] [answer=%s] [query=%s] [title=%s]\n' % (str(result[4]), str(result[1]).replace('\n', '').encode('utf-8'), query.encode('utf-8'), result[0].encode('utf-8'))
				answer_dic[answer] = 0
				debug_info = {'from':'weimi_faq'}
				if len(rets) >= 2:
					break
			log_str += '***********************************************weimi faq filter***********************************************\n'
			log_str += log_filter
			log_str += '*********************************************weimi faq candidate**********************************************\n'
			log_str += log_candidate
			log_str += '**************************************************************************************************************\n'
		log_str += '[accessor_INFO] [weimi] [faq] [final] [query=%s] [search result num=%s] [final_answer_num=%s(最多2个)]' % (query.encode('utf-8'), str(source_num), str(len(rets)))
		detlog.info(log_str)
		return rets, low_trank_data

	def get_weimi_result(self, res_str, query, params, debug_info):
		answer = None
		rets = []
		if res_str == None or res_str == '':
			debug_info['status'] = 'empty search content'
			rets = [(answer, debug_info)]
			detlog.info('[accessor_INFO] [weimi] [query=%s] empty search content' % (query.encode('utf-8')))
		else:
			res_str = res_str.decode('utf-16', 'ignore')
			rets, low_trank_data = self.parse_weimi_faq_result(res_str, query, debug_info)
			if rets == []:
				rets = self.parse_weimi_category(query, params, answer, debug_info, low_trank_data)
			if rets == []:
				rets = self.check_weimi_op_query(query, params, answer, debug_info, low_trank_data)
		if rets == []:
			rets = [(None, debug_info)]
		return rets

	@gen.coroutine
	def run(self, query, params):
		rets = []
		debug_info = {"from":self.acc_name}
		try:
			answer = None
			rets = self.match_weimi_whitelist(query, params, answer, debug_info)
			if rets == []:
				rets = self.check_weimi_order(query, params, answer, debug_info)
			if rets == []:
				rets = self.check_search_people(query, params, answer, debug_info)
			if rets == []:
				if comm.no_punctuation_length(query, params['seg']) >= 2 or (len(params['seg']) == 1 and params['seg'][0][1] == 23):		#faq可能有答案
					pass
				else:
					rets = self.parse_weimi_category(query, params, answer, debug_info)
					if rets == []:
						rets = self.check_weimi_op_query(query, params, answer, debug_info)
					if rets == []:
						debug_info['status'] = 'query too short'
						rets = [(None, debug_info)]
			if rets == []:
				url = self._conf.WEIMI_FAQ_ADDR
				query_gbk = self.format_search_query(query, params).strip().lower().encode('gbk', 'ignore')
				data = 'queryFrom=web&queryType=query&queryString=%s&forceQuery=1' % (urllib.quote_plus(query_gbk))
				async_reqs_param = [AsyncReqsParam("POST", url, data, headers)]
				results = yield parallel_async(async_reqs_param, wait_for_all=True)
				for res_str, req_info in results:
					debug_info["req_info"] = req_info
					if res_str:
						ret_list = self.get_weimi_result(res_str, query, params, debug_info)
						rets.extend(ret_list)
		except Exception, e:
			debug_info["status"] = "error, " + str(e)
			exclog.error('[query=%s]\n%s' % (query.encode('utf-8'), traceback.format_exc(e)))
		if rets == []:
			rets = [(None, debug_info)]
		raise gen.Return(rets)

	@gen.coroutine
	def test(self):
		source = 'weimi'
		while True:
			print '>>>>>>>>>>>>>>>>'
			query = raw_input("query:").decode("utf-8")
			begin = time.time()
			query = get_query_correction(query, source)
			params = preprocessing(query, source)
			print json.dumps(params, ensure_ascii=False)
			results = yield self.run(query, params)
			for res in results:
				answer = res[0]
				debug_info = res[1]
				print 'answer:' + str(answer).encode('utf-8')
				print 'debug_info:' + json.dumps(debug_info, ensure_ascii=False)
			end = time.time()
			print 'cost:' + str(round((end-begin)*1000, 2)) + 'ms'
			print '\n\n'



if __name__ == '__main__':
	from preprocessing import *
	conf = Config("dev", True, "develop")
	weimi = Weimi(conf)
	weimi()

