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

c_curr_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(c_curr_dir, '../../lib'))

from trie import *
import common_method as common
import tencent_segment as tc_seg


detlog = logging.getLogger('details')
exclog = logging.getLogger('exception')


pattern_list = []
pattern_words = {}
precise_words = {}
pattern_tree = TagMake()
dirty_word_dir = os.path.join(c_curr_dir, '../../data/common_data/dirty_word.json.utf8')


def load_dirty_word():
	'''
		功能: 加载过滤answer的数据
		params:
		return:
			pattern_list: (list)pattern，编码Unicode
			pattern_words: (dict)pattern word，编码Unicode
			precise_words: (dict)精准匹配词条，编码Unicode
	'''
	global pattern_list
	global pattern_words
	global precise_words
	trieTree = TrieTree()
	try:
		inputs = open(dirty_word_dir, 'r')
		word_json = json.load(inputs, encoding='utf-8')
		if 'pattern_list' in word_json:
			pattern_list = word_json['pattern_list']
		if 'pattern_words' in word_json:
			pattern_words = word_json['pattern_words']
		if 'pattern_tree' in word_json:
			trieTree = pickle.loads(word_json['pattern_tree'])
			pattern_tree.add_exist_tree(trieTree)
		if 'precise_words' in word_json:
			precise_words = word_json['precise_words']
		inputs.close()
	except Exception, e:
		exclog.error('\n%s' % traceback.format_exc(e))
	return pattern_list, pattern_words, precise_words


# init初始化
begin = time.time()
load_dirty_word()
cost = str(int(round(time.time()-begin, 3)*1000))
detlog.info('[common_init] [check_dirty_answer] [cost=%sms]' % (cost))


def check_dirty_answer(sen):
	'''
		功能: 检查answer中是否包含需要过滤的词语
		params:
			sen: answer，编码Unicode
		return:
			flag: True: answer中有不文明词语或敏感词，否则为False
			dirty_word: 命中的不文明词语，编码Unicode
	'''
	flag = False
	dirty_word = ''
	try:
		flag, dirty_word = match_dirty_word(sen)
	except Exception, e:
		exclog.error('[query=%s]\n%s' % (sen.encode('utf-8'), traceback.format_exc(e)))
	return flag, dirty_word


def match_dirty_word(sen):
	'''
		功能: 检查answer中是否包含需要过滤的词语
		params:
			sen: answer，编码Unicode
		return:
			flag: True: answer中有不文明词语，否则为False
			dirty_word: 命中的不文明词语，编码Unicode
	'''
	flag = False
	dirty_word = ''
	sen_new = sen.strip().lower()
	if sen_new in precise_words:
		flag = True
		dirty_word = sen_new
	else:
		seg = tc_seg.seg_with_pos(sen_new)
		sen_new2 = common.get_norm_query(seg)
		if sen_new2 in precise_words:
			flag = True
			dirty_word = sen_new
		else:
			results = pattern_tree.make_all(sen_new)
			if len(results) > 0:
				pattern_list_id = match_dirty_word_pattern(results)
				if pattern_list_id != -1:
					flag = True
					dirty_word = ' '.join(pattern_list[pattern_list_id])
	return flag, dirty_word


def match_dirty_word_pattern(results):
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


	while True:
		print '>>>>>>>>>>>>>>>>>>'
		raw = raw_input('sentence:')
		b = time.time()
		sen = str(raw).decode('utf-8')
		flag, dirty_word = check_dirty_answer(sen)
		print 'flag:' + str(flag)
		print 'dirty_word:' + str(dirty_word).encode('utf-8')
		print 'cost:' + str(round((time.time()-b)*1000, 2)) + 'ms'
		print '\n\n'

