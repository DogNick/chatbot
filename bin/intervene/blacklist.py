#coding=utf-8

from __future__ import division
import os
import re
import sys
import pdb
import json
import time
import pickle
import random
import logging
import traceback
import itertools

curr_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(curr_dir, '../common'))
sys.path.append(os.path.join(curr_dir, '../../lib'))
sys.path.append(os.path.join(curr_dir, '../'))

from trie import *
from preprocessing import *


detlog = logging.getLogger('details')
exclog = logging.getLogger('exception')


sub_type = '黑名单'
result_type = '黑名单'
from_name = 'blacklist'
time_format = '%Y-%m-%d %H:%M:%S'

pattern_tree = TagMake()
adult_tree = TagMake()		#成人话题
black_dir = os.path.join(curr_dir, '../../data/blacklist/blacklist.json.utf8')
adult_dir = os.path.join(curr_dir, '../../data/blacklist/adult_topic.utf8')


source_blacklist_process = {
		'aiplatform_teemo':'adult',
}

p_weimi = re.compile(u'vpn')

def load_blacklist():
	'''
		功能: 加载黑名单数据
		params:
		return:
			pattern_list: (list)黑名单pattern，编码Unicode
			pattern_words: (dict)黑名单pattern word，编码Unicode
			precise_words: (dict)黑名单精准匹配词条，编码Unicode
			black_answer: (list)命中黑名单的默认answer，编码Unicode
	'''
	pattern_list = []
	pattern_words = {}
	precise_words = {}
	black_answer = []
	trieTree = TrieTree()
	try:
		inputs = open(black_dir, 'r')
		black_json = json.load(inputs, encoding='utf-8')
		pattern_list = black_json['pattern_list']
		pattern_words = black_json['pattern_words']
		trieTree = pickle.loads(black_json['pattern_tree'])
		pattern_tree.add_exist_tree(trieTree)
		precise_words = black_json['precise_words']
		black_answer = black_json['black_answer']
		inputs.close()
		#temp
		inputs = open(adult_dir, 'r')
		for line in inputs:
			line = line.strip()
			if line == '':
				continue
			adult_tree.add_tag(line.lower().decode('utf-8'))
		inputs.close()
	except Exception, e:
		exclog.error('\n%s' % (traceback.format_exc(e)))
	return pattern_list, pattern_words, precise_words, black_answer


# init初始化
begin = time.time()
pattern_list, pattern_words, precise_words, black_answer = load_blacklist()
cost = str(int(round(time.time()-begin, 3)*1000))
detlog.info('[intervene_init] [blacklist] [pattern_items=%d] [precise_items=%d] [cost=%sms]' % (len(pattern_list), len(precise_words), cost))



def match_blacklist_pattern(results):
	pattern_list_id = -1
	patternid_pattern = {}			#命中的pattern text {list_id:{pattern}}
	for each in results:
		pattern = each[0]
		if pattern in pattern_words:
			for list_id in pattern_words[pattern]:
				list_id = int(list_id)
				if list_id not in patternid_pattern:
					patternid_pattern[list_id] = dict()
				patternid_pattern[list_id][pattern] = 0
				if len(pattern_list[list_id]) == len(patternid_pattern[list_id]):
					pattern_list_id = list_id
					break
	return pattern_list_id


def match_blacklist(query, source, acc_params, answer, debug_info):
	query_new = query.strip().lower()
	if query_new in precise_words:
		answer = random.choice(black_answer)
		debug_info['status'] = 'precise blacklist'
		debug_info['blackword'] = query_new.encode('utf-8')
	else:
		query_new2 = query_new.replace(' ', '')
		if query_new2 in precise_words:
			answer = random.choice(black_answer)
			debug_info['status'] = 'precise blacklist twice'
			debug_info['blackword'] = query_new2.encode('utf-8')
		else:
			results = pattern_tree.make_all(query_new)
			if len(results) > 0:
				pattern_list_id = match_blacklist_pattern(results)
				if pattern_list_id != -1:
					answer = random.choice(black_answer)
					debug_info['status'] = 'query match blacklist pattern:' + str(pattern_list_id)
					debug_info['blackword'] = ' '.join(pattern_list[pattern_list_id])
	if (answer == None or answer == '') or source == 'aiplatform_teemo':
		results = adult_tree.make_all(query_new)
		if len(results) > 0:
			answer = u'这个问题有点辣眼睛'
			debug_info['status'] = 'adult'
			debug_info['blackword'] = results[0][0]
	return answer, debug_info


def need_req(query, source='', acc_params={}):
	begin = time.time()
	answer = None
	debug_info = {'from':from_name, 'sub_type':sub_type, 'result_type':result_type}
	try:
		answer, debug_info = match_blacklist(query, source, acc_params, answer, debug_info)
		if answer == '':
			answer = None
		if source == 'weimi' and p_weimi.search(query) != None:
			answer = None
	except Exception, e:
		exclog.error('[query=%s]\n%s' % (query.encode('utf-8'), traceback.format_exc(e)))
	debug_info['cost'] = str(round((time.time()-begin)*1000, 2)) + 'ms'
	return False, [(answer, debug_info)]


def req_params(query, acc_params={}):
	return None, None, None, None


def on_response(res_str, query='', source='', acc_params={}):
	answer = None
	debug_info = {'from':from_name, 'sub_type':sub_type, 'result_type':result_type}
	try:
		pass
	except Exception, e:
		exclog.error('[query=%s]\n%s' % (query.encode('utf-8'), traceback.format_exc(e)))
	return [(answer, debug_info)]


# 本地测试接口
def get_blacklist(query, source='', acc_params={}):
	flag, default_ret = need_req(query, source, acc_params)
	return default_ret


if __name__ == '__main__':
	# 配置logging
	detlog.setLevel(logging.INFO)
	exclog.setLevel(logging.INFO)
	sh1 = logging.StreamHandler(stream=None)
	sh2 = logging.StreamHandler(stream=None)
	sh1.setLevel(logging.INFO)
	sh2.setLevel(logging.INFO)
	formatter1 = logging.Formatter('[pid=%(process)d] [%(asctime)s] [%(filename)s:%(lineno)d] %(message)s')
	formatter2 = logging.Formatter('[pid=%(process)d] [%(asctime)s] [%(filename)s:%(lineno)d] [%(funcName)s] %(message)s')
	sh1.setFormatter(formatter1)
	sh2.setFormatter(formatter2)
	detlog.addHandler(sh1)
	exclog.addHandler(sh2)


	source = 'wechat'
	while True:
		print '>>>>>>>>>>>>>>>>>>'
		raw = raw_input('query:')
		b = time.time()
		query = str(raw).decode('utf-8')
		query = get_query_correction(query, source)
		acc_params = preprocessing(query, source)
		default_ret = get_blacklist(query, source, acc_params)
		answer = str(default_ret[0][0])
		debug_info = default_ret[0][1]
		print 'query:' + query.encode('utf-8')
		print 'answer:' + answer.encode('utf-8')
		print 'debug:' + json.dumps(debug_info, ensure_ascii=False)
		print 'cost:' + str(round((time.time()-b)*1000, 2)) + 'ms'
		print '\n\n'

