#!/usr/bin/env python
#coding=utf8

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


'''
	author: cuiyanyan

	通用方法:
		cmfunc1: 全角转半角
		cmfunc2: 半角转全角
		cmfunc3: 获取两个字符串中间的内容(返回1个)
		cmfunc4: 从字符串最后开始往前找，返回最后一个str1和str2之间的内容(返回1个)
		cmfunc5: 获取两个字符串中间的内容(最长，返回1个)
		cmfunc6: 获取两个字符串中间的内容(返回多个)
		cmfunc7: 判断字符串是否包含url
		cmfunc8: 获得normalized query(去掉句子末尾标点和语气词)
		cmfunc9: 获取不包含标点的句子字数(英文单词算1，去掉括号内的内容)

	检索结果处理(主要用于白名单检索和faq检索):
		refunc1: 处理检索结果title
'''

def strQ2B(str_uni):
	'''
		cmfunc1
		功能: 全角字符串转半角
		params:
			str_uni: 需要转换的字符串，编码Unicode
		return:
			result_uni: 转换完的字符串，编码为Unicode
	'''
	result_uni = ''
	for ch in str_uni:
		inside_code = ord(ch)
		if inside_code == 12288:
			inside_code = 32
		elif (inside_code >= 65281 and inside_code <= 65374):
			inside_code -= 65248
		result_uni += unichr(inside_code)
	return result_uni


def strB2Q(str_uni):
	'''
		cmfunc2
		功能: 半角字符串转全角
		params:
			str_uni: 需要转换的字符串，编码Unicode
		return:
			result_uni: 转换完的字符串，编码为Unicode
	'''
	result_uni = ''
	for ch in str_uni:
		inside_code = ord(ch)
		if inside_code == 32:
			inside_code = 12288
		elif (inside_code >= 32 and inside_code <= 126):
			inside_code += 65248
		result_uni += unichr(inside_code)
	return result_uni


def get_between(source, str1, str2, pos=0):
	'''
		cmfunc3
		功能: 从指定位置(默认pos=0)，返回两个字符串中间的内容
		params:
			source: 原字符串
			str1: 起始字符串
			str2: 结束字符串
			pos: 起始位置，默认为0
		return:
			result: str1和str2之间的字符串，若无返回空串
	'''
	result = ''
	if source == '' or source == None:
		return result
	if (str1 == '' or str1 == None) and (str2 == '' or str2 == None):
		return result
	elif str1 != '' and str1 != None and str2 != '' and str2 != None:
		pos1 = source.find(str1, pos)
		pos2 = source.find(str2, pos1+len(str1))
		if pos1 != -1 and pos2 != -1:
			result = source[pos1+len(str1):pos2]
	elif str1 == '' or str1 == None:
		pos2 = source.find(str2, pos)
		if pos2 != -1:
			result = source[:pos2]
	elif str2 == '' or str2 == None:
		pos1 = source.find(str1, pos)
		if pos1 != -1:
			result = source[pos1+len(str1):]
	return result


def get_between_last(source, str1, str2):
	'''
		cmfunc4
		功能: 从字符串最后开始往前找，返回最后一个str1和str2之间的内容
		params:
			source: 原字符串
			str1: 起始字符串，不允许为空
			str2: 结束字符串，可以为空
		return:
			result: str1和str2之间的字符串，若无返回空串
	'''
	result = ''
	if source == '' or source == None or str1 == '' or str1 == None:
		return result
	pos1 = source.rfind(str1)
	if pos1 != -1:
		if str2 == '' or str2 == None:
			result = source[pos1+len(str1):]
		else:
			pos2 = source.find(str2, pos1+len(str1))
			if pos2 != -1:
				result = source[pos1+len(str1):pos2]
	return result


def get_between_longest(source, str1, str2, pos=0):
	'''
		cmfunc5
		功能: 返回从指定位置(默认pos=0)的第一个str1到最后一个str2之间的内容
		params:
			source: 原字符串
			str1: 起始字符串
			str2: 结束字符串
			pos: 起始位置，默认为0
		return:
			result: str1和最后一个str2之间的字符串，若无返回空串
	'''
	result = ''
	if source == '' or source == None:
		return result
	if (str1 == '' or str1 == None) and (str2 == '' or str2 == None):
		return result
	elif str1 != '' and str1 != None and str2 != '' and str2 != None:
		pos1 = source.find(str1, pos)
		pos2 = source.rfind(str2)
		if pos1 != -1 and pos2 != -1 and pos1 <= pos2:
			result = source[pos1+len(str1):pos2]
	elif str1 == '' or str1 == None:
		pos2 = source.rfind(str2)
		if pos2 != -1 and pos <= pos2:
			result = source[:pos2]
	elif str2 == '' or str2 == None:
		pos1 = source.find(str1, pos)
		if pos1 != -1:
			result = source[pos1+len(str1):]
	return result


def get_between_all(source, str1, str2, pos=0, ret=0):
	'''
		cmfunc6
		功能: 从指定位置(默认pos=0)，返回N个(默认ret=0，返回所有的)两个字符串中间的内容
		params:
			source: 原字符串
			str1: 起始字符串
			str2: 结束字符串
			pos: 起始位置，默认为0
			ret: 返回个数，要求>=1，默认为0
		return:
			ret_flag: 是否找到字符串，找到为True，未找到为False
			result: 结果字符串列表
	'''
	index = 0
	result = []
	ret_flag = False
	if source == '' or source == None:
		return ret_flag, result
	if (str1 == '' or str1 == None) and (str2 == '' or str2 == None):
		return ret_flag, result
	elif str1 != '' and str1 != None and str2 != '' and str2 != None:
		pos1 = source.find(str1, pos)
		pos2 = source.find(str2, pos1+len(str1))
		while pos1 != -1 and pos2 != -1:
			result.append(source[pos1+len(str1):pos2])
			index += 1
			if index >= ret and ret != 0:
				break
			pos1 = source.find(str1, pos2)
			pos2 = source.find(str2, pos1+len(str1))
	elif str1 == '' or str1 == None:
		pos2 = source.find(str2, pos)
		if pos2 != -1:
			result.append(source[:pos2])
	elif str2 == '' or str2 == None:
		pos1 = source.find(str1, pos)
		if pos1 != -1:
			result.append(source[pos1+len(str1):])
	if len(result) > 0:
		ret_flag = True
	return ret_flag, result


def is_contain_url(content, segs=[]):
	'''
		cmfunc7
		功能: 判断字符串是否包含url
		params:
			content: 字符串，编码utf-8
			segs: answer的分词结果
		return:
			flag: False表示不包含url，True表示包含url
	'''
	p_url = re.compile('(http|www)(.*)(com|cn|net)(.*)')
	if p_url.search(content) != None:
		return True
	for seg in segs:
		if seg[1] == 50:
			return True
	return False


def get_norm_query(segs=[]):
	'''
		cmfunc8
		功能: 获得normalized query(去掉句子末尾标点和语气词)
		params:
			segs: 分词结果，编码Unicode
		return:
			norm_query: 去掉无意义字符的query，编码Unicode
	'''
	norm_query = ''
	n = len(segs)
	if n == 0:
		return norm_query
	elif n == 1:
		norm_query = segs[0][0]
		return norm_query
	i = n-1
	while i >= 0:
		if segs[i][1] != 34 and segs[i][1] != 36:
			norm_query = segs[i][0] + norm_query
		elif i == 0 and norm_query == '':
			norm_query = segs[i][0]
		i -= 1
	return norm_query


def no_punctuation_length(sen, segs=[]):
	'''
		cmfunc9
		功能: 获取不包含标点的句子字数(英文单词算1，去掉括号内的内容)
		params:
			sen: 原query，编码Unicode
			segs: 分词结果，编码Unicode
		return:
			lens: 不包含标点的句子字数
	'''
	lens = 0
	flag = False		#True:是括号内的内容; False:不是括号内的内容
	for each in segs:
		if each[1] == 23 and flag == False:
			lens += 1
		elif each[1] == 34:
			if each[0] == u'(':
				flag = True
			elif each[0] == u')':
				flag = False
			continue
		elif flag == False:
			lens += len(each[0])
	return lens


def process_title_from_search_pair(title):
	'''
		refunc1
		功能: 处理检索库检索得到的title
		params:
			titles: 检索得到的title，编码是Unicode
		return:
			result: 返回去掉标红字符的title，编码Unicode
			rel: float类型，返回标红字符在整个字符串的占比
	'''
	rel = 0.0
	result = ''
	red = 0
	source = 0
	flag, tmp = get_between_all(title, u'\ue40a', u'\ue40b')
	result = title.replace(u'\ue40b','').replace(u'\ue40a','')
	source = len(result)
	for t in tmp:
		red += len(t)
	if source != 0:
		rel = float(red/source)
	return result, rel


def test_strQ2B():
	print '-----------------'
	print 'strQ2B test:'
	querys = [u'你好', u'你好a', u'你好 Ａ']
	for query in querys:
		print query.encode('utf-8') + '\t' + strQ2B(query).encode('utf-8')
	print '\n\n'


def test_strB2Q():
	print '-----------------'
	print 'strB2Q test:'
	querys = [u'你好', u'你好a', u'你好 Ａ']
	for query in querys:
		print query.encode('utf-8') + '\t' + strB2Q(query).encode('utf-8')
	print '\n\n'


def test_get_between():
	print '-----------------'
	print 'get_between test:'
	querys = [('你吃了吗', '你', '吗', 0), ('', 'a', 'b', 1), ('abdcf', 'a', '', 0), ('abdcf', '', '', 0), ('abdcgf', 'a', 'c', 1)]
	for item in querys:
		print '%s %s %s %d --- %s' % (item[0], item[1], item[2], item[3], get_between(item[0], item[1], item[2], item[3]))
	print '\n\n'


def test_get_between_all():
	print '-----------------'
	print 'get_between_all test:'
	querys = [('你吃了吗', '你', '吗', 0, 2), ('', 'a', 'b', 1, 0), ('abdcf', 'a', '', 0, 2), ('abdcf', '', '', 0, 0), ('abdcgf', 'a', 'c', 1, 2), ('adfafags', 'a', 'f', 0, 3)]
	for item in querys:
		flag, result = get_between_all(item[0], item[1], item[2], item[3], item[4])
		if flag:
			line = str(result)
		else:
			line = ''
		print '%s %s %s %d %d --- %s' % (item[0], item[1], item[2], item[3], item[4], line)
	print '\n\n'


if __name__ == '__main__':
	#test_strQ2B()
	#test_strB2Q()
	#test_get_between()
	#test_get_between_all()
	print 'test common method'

