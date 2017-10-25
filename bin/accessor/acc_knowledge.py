#coding=utf-8

from __future__ import division
import pickle

from accessor import *
from trie import *
import common_method as comm


time_format = '%Y-%m-%d %H:%M:%S'
knowledge_file = os.path.join(curr_dir, '../../data/knowledge/knowledge_json.utf8')


class Knowledge(Accessor):
	class Resource(Accessor.Resource):
		def init(self):
			self.file_update_time = 0.0			#文件最新编辑时间
			self.precise_query = {}				#query和norm_query对应的answer_id, 编码Unicode, {precise_query:[note, answer_id], ...}
			self.answer_list = {}				#answer_id到answer的映射, 编码Unicode, {answer_id:{content:[], ...}, ...}
			self.pattern_list = []				#pattern集合以及对应的answer_id, 编码Unicode, [[pattern, answer_id, pattern_id], ...]
			self.pattern_words = {}				#pattern词以及在pattern_list的位置, 编码Unicode, {pattern_word:{pattern_id:'', ...}, ,,,}
			self.pattern_tree = TagMake()		#pattern词对应的trie树, 编码Unicode
			self.word_idf = {}					#pattern_word的idf值
			begin = time.time()
			try:
				inputs = open(knowledge_file, 'r')
				data = json.load(inputs, encoding='utf-8')
				self.precise_query = data['query']
				self.answer_list = data['answer']
				self.pattern_list = data['pattern']
				self.pattern_words = data['pattern_words']
				self.word_idf = data['word_idf']
				self.pattern_tree.add_exist_tree(pickle.loads(data['pattern_tree']))
				inputs.close()
				self.file_update_time = os.stat(knowledge_file).st_mtime
			except Exception, e:
				exclog.error('\n%s' % (traceback.format_exc(e)))
			edit_time = time.strftime(time_format, time.localtime(self.file_update_time))
			cost = str(int(round(time.time()-begin, 3)*1000))
			detlog.info('[accessor_init] [knowledge] [file_edit_time=%s] [cost=%sms]' % (edit_time, cost))

	def __init__(self, conf):
		super(self.__class__, self).__init__(conf)

	def knowledge_file_update(self):
		if Knowledge.rsc().file_update_time != os.stat(knowledge_file).st_mtime:
			begin = time.time()
			#self.initialize()
			cost = str(int(round(time.time()-begin, 3)*1000))
			edit_time = time.strftime(time_format, time.localtime(Knowledge.rsc().file_update_time))
			detlog.info('[accessor_reload] [knowledge] [knowledge_file_edit_time=%s] [cost=%sms]' % (edit_time, cost))

	def answer_process(self, answer_id, answer, debug_info):
		'''每次随机选取一个answer, 并处理answer中包含的模板信息
		Args:
			answer_id: query对应的answer_id
			answer: answer, 编码Unicode
			debug_info: debug信息
		Returns:
			answer: answer, 编码Unicode
			debug_info: debug信息
		Raises:
		'''
		answer = random.choice(Knowledge.rsc().answer_list[str(answer_id)]['content']).replace('<brbr>', '\n')
		debug_info['answer_id'] = answer_id
		return answer, debug_info

	def is_precise_query(self, query, params, answer, debug_info):
		'''query精准匹配
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
		if query in Knowledge.rsc().precise_query:
			answer_id = Knowledge.rsc().precise_query[query]
			answer, debug_info = self.answer_process(answer_id, answer, debug_info)
		if answer == None:
			norm_query = comm.get_norm_query(params.get('seg', []))
			if norm_query in Knowledge.rsc().precise_query:
				answer_id = Knowledge.rsc().precise_query[norm_query]
				answer, debug_info = self.answer_process(answer_id, answer, debug_info)
		if answer != None:
			detlog.info('[accessor_INFO] [knowledge] [query=%s] [answer_id=%s] precise query' % (query.encode('utf-8'), debug_info['answer_id']))
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
		log_str = '[accessor_INFO] [knowledge] [query=%s] [all_hit_groups=' % (query.encode('utf-8'))
		#b = time.time()
		i = 0
		#print str(results)
		while i < len(results):
			j = i + 1
			while j < len(results):
				if Knowledge.rsc().word_idf[results[j][0]] > Knowledge.rsc().word_idf[results[i][0]]:
					tmp = results[i]
					results[i] = results[j]
					results[j] = tmp
				j += 1
			i += 1
		#print json.dumps(results, ensure_ascii=False)
		for (i, each) in enumerate(results):
			pattern = each[0]
			#print pattern
			if i == 0 and len(patternid_pattern) == 0 and Knowledge.rsc().word_idf[results[i][0]] < 2:
				break
			if Knowledge.rsc().word_idf[pattern] >= 4 or len(patternid_pattern) == 0:#temp
				#print 1
				if pattern in Knowledge.rsc().pattern_words:
					for list_id in Knowledge.rsc().pattern_words[pattern]:
						list_id = int(list_id)
						if list_id not in patternid_pattern:
							patternid_pattern[list_id] = dict()
						patternid_pattern[list_id][pattern] = 0
						if len(Knowledge.rsc().pattern_list[list_id][0]) == len(patternid_pattern[list_id]):
							all_hit[list_id] = len(Knowledge.rsc().pattern_list[list_id][0])
			else:
				for list_id in patternid_pattern:
					if str(list_id) in Knowledge.rsc().pattern_words[pattern]:
						patternid_pattern[list_id][pattern] = 0
					if len(Knowledge.rsc().pattern_list[list_id][0]) == len(patternid_pattern[list_id]):
						all_hit[list_id] = len(Knowledge.rsc().pattern_list[list_id][0])
		#print 'all_pattern:', time.time()-b
		#b = time.time()
		for each in all_hit:
			log_str += ' (' + str(each) + ':' + ' '.join(Knowledge.rsc().pattern_list[each][0]) + ':' + str(Knowledge.rsc().pattern_list[each][1]) + ')'
			if pattern_id == -1 or max_num < all_hit[each]:
				pattern_id = each
				max_num = all_hit[each]
				max_length = len(''.join(Knowledge.rsc().pattern_list[each][0]))
			elif max_num == all_hit[each]:
				if max_length < len(''.join(Knowledge.rsc().pattern_list[each][0])):
					pattern_id = each
					max_num = all_hit[each]
					max_length = len(''.join(Knowledge.rsc().pattern_list[each][0]))
		#print 'one_pattern:', time.time()-b
		log_str += ' ]'
		if pattern_id != -1:
			answer_id = Knowledge.rsc().pattern_list[pattern_id][1]
			answer, debug_info = self.answer_process(answer_id, answer, debug_info)
		if answer != None:
			debug_info['pattern_id'] = pattern_id
			debug_info['status'] = 'from pattern'
			log_str += ' [answer_id=%s] pattern' % str(debug_info['answer_id'])
		detlog.info(log_str)
		return answer, debug_info

	def is_match_pattern(self, query, params, answer, debug_info):
		'''是否命中pattern
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
		#b = time.time()
		result = Knowledge.rsc().pattern_tree.make_all(query)
		#print 'pattern tree:', time.time()-b
		if len(result) == 0:
			debug_info['status'] = 'not match knowledge query and pattern'
			detlog.info('[accessor_INFO] [knowledge] [query=%s] not match' % (query.encode('utf-8')))
		else:
			#b = time.time()
			detlog.info('[accessor_INFO] [knowledge] [query=%s] [patterns=%s]' % (query.encode('utf-8'), ' '.join(each[0] for each in result)))
			answer, debug_info = self.choose_match_best_pattern(result, query, answer, debug_info)
			#print 'choose:', time.time()-b
		return answer, debug_info

	def match_process(self, query, params, answer, debug_info):
		'''匹配数据
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
		#b = time.time()
		answer, debug_info = self.is_precise_query(query, params, answer, debug_info)
		#print 'precise:', time.time()-b
		if answer == None:
			#b = time.time()
			answer, debug_info = self.is_match_pattern(query, params, answer, debug_info)
			#print 'pattern:', time.time()-b
		return answer, debug_info

	@gen.coroutine
	def run(self, query, params):
		rets = []
		answer = None
		debug_info = {'from':self.acc_name, 'sub_type':u'知识库', 'result_type':u'知识库'}
		try:
			#self.knowledge_file_update()
			answer, debug_info = self.match_process(query, params, answer, debug_info)
		except Exception, e:
			debug_info['status'] = 'error, ' + str(e)
			exclog.error('[query=%s]\n%s' % (query.encode('utf-8'), traceback.format_exc(e)))
		rets = [(answer, debug_info)]
		raise gen.Return(rets)

	@gen.coroutine
	def test(self):
		while True:
			source = ""
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


if __name__ == '__main__':
	from preprocessing import *
	conf = Config("dev", True, "develop")
	knowledge = Knowledge(conf)
	knowledge()

