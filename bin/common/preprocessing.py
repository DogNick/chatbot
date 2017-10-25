#coding=utf8

'''
	author: cuiyanyan

	预处理:
		1、调用分词
		2、问题类型分类
'''

from __future__ import division
import os
import re
import sys
import pdb
import copy
import json
import time

reload(sys)
sys.setdefaultencoding('utf-8')
c_curr_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(c_curr_dir, '../lib'))

from tencent_segment import *
from query_classifier import *


p_name = re.compile(u'wangzai|旺仔|王宰|王仔|汪载|王载|汪宰')


def get_query_correction(query, source, types=''):
	'''
		功能: query纠错模块
		params:
			query: 原始query，编码Unicode
			source: 请求source
		return:
			result: 纠错后的query，编码Unicode
	'''
	result = ''
	if source == 'yzdd_onsite' or source == 'common_show':
		query = query.replace(' ', '')
	if types == '':
		query = query.lower()
	match = p_name.search(query)
	if match:
		if match.group(0) == u'旺仔' and query.find(u'旺仔牛奶') != -1:
			result = query
		else:
			pos = query.find(match.group(0))
			result = query[0:pos] + u'汪仔' + query[pos+len(match.group(0)):]
	else:
		result = query
	return result


def preprocessing(query, source, ip='127.0.0.1', uid='wangzai_test', end_flag=True):
	'''
		功能: 预处理模块，返回分词、问题类型、[意图识别--todo]等结果
		params:
			query: 原始query，编码Unicode
		return:
			params_json: 处理结果，json格式，字符编码为Unicode
	'''
	params_json = {}
	params_json['ip'] = ip
	params_json['uid'] = uid
	params_json['source'] = source
	params_json['end_flag'] = end_flag
	params_json['seg'] = seg_with_pos(query)
	query_type, tag1, tag2 = get_query_type_and_tag(query)
	query_type_name = get_query_type_name(query_type)
	params_json['query_classify'] = dict()
	params_json['query_classify']['query_type'] = query_type
	params_json['query_classify']['query_type_name'] = query_type_name
	params_json['query_classify']['tag'] = [tag1, tag2]
	return params_json


if __name__ == '__main__':
	querys = [u'李白是哪一年生的']
	for query in querys:
		params_json = preprocessing(query, 'wechat')
		print '**************'
		print 'query:' + query.encode('utf-8')
		print 'result:' + json.dumps(params_json, ensure_ascii=False)
		print '\n\n'
