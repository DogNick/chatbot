#coding=utf-8

'''
	author: cuiyanyan
	功能: 问题类型分类器
'''

import os
import re
import sys
import time
import logging
import traceback

reload(sys)
sys.setdefaultencoding('utf-8')
c_curr_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(c_curr_dir, '../../lib'))
sys.path.append(os.path.join(c_curr_dir, '../'))

from ctypes import cdll, c_char_p

detlog = logging.getLogger('details')
exclog = logging.getLogger('exception')


p_which = re.compile('u^(.+?)(和|与|跟)(.+?)(比 起来)?(到底|究竟)?(谁|谁的|哪个)(会)?(更|更加|更加的|比较|比较的|最|最为)?(.+?)(一些|些|点|一点)?(啊|呀|呢)?')
query_classify_lib_dir = os.path.join(c_curr_dir, '../../lib/classifier/libQueryClassify.so')
query_classify_seg_dir = os.path.join(c_curr_dir, '../../data/query_classify_data')
query_classify_svm_dir = os.path.join(c_curr_dir, '../../data/query_classify_data/svm_dir')


INTEND = {
		-1:u'ERROR',
		0:u'否定句(NO)',
		1:u'肯定句(DEC)',
		2:u'是否问(YON)',
		3:u'选择问(ALT)',
		4:u'时间(WHEN)',
		5:u'原因(WHY)',
		6:u'数量(HOWMANY)',
		7:u'方式(HOWTO)',
		8:u'哪个(WHICH)',
		9:u'什么(WHAT)',
		10:u'地点(WHERE)',
		11:u'谁(WHO)',
		12:u'一般疑问句(DOUB)',
		13:u'评价(EVAL)'
}


def init_query_classifier():
	'''
		功能: 初始化问题类型分类器，若初始化失败，判断query类型均返回-1
		params:
		return:
			query_init_flag: 问题类型分类器初始化是否成功
			lib: 分类器lib
	'''
	query_init_flag = True
	lib = None
	try:
		lib = cdll.LoadLibrary(query_classify_lib_dir)
		lib.query_init(query_classify_seg_dir, query_classify_svm_dir)
	except Exception, e:
		query_init_flag = False
		exclog.error('\n%s' % traceback.format_exc(e))
	return query_init_flag, lib

#init
begin = time.time()
query_init_flag, query_lib = init_query_classifier()
cost = str(int(round(time.time()-begin, 3)*1000))
detlog.info('[common_init] [query_classifier] [init_flag=%s] [cost=%sms]' % (str(query_init_flag), cost))


def get_query_type(query):
	'''
		功能: 根据query判断query类型
		params:
			query: 原始query，编码Unicode
		return:
			ret: 问题类型，失败返回-1
	'''
	ret = -1
	if query_init_flag == False or query == '':
		return ret
	try:
		ret, _, _ = get_query_classify_results(query.encode('gbk', 'ignore'))
		if ret < -1 or ret > 13:
			ret = -1
	except Exception, e:
		exclog.error('\n%s' % traceback.format_exc(e))
	return ret


def get_query_type_and_tag(query):
	'''
		功能: 根据query判断query类型，并返回指定类型的答案tag
		params:
			query: 原始query，编码Unicode
		return:
			ret: 问题类型，失败返回-1
			tag1: 答案tag，编码Unicode，默认为空
			tag2: 答案tag，编码Unicode，默认为空
	'''
	ret = -1
	tag1 = ''
	tag2 = ''
	if query_init_flag == False or query == '':
		return ret, tag1, tag2
	try:
		ret, c_tag1, c_tag2 = get_query_classify_results(query.encode('gbk', 'ignore'))
		if ret < -1 or ret > 13:
			ret = -1
		if ret != 2 and ret != 3 and ret != 13:
			return ret, tag1, tag2
		match = p_which.search(query)
		if match != None:
			tag1 = match.group(1)
			tag2 =  match.group(3)
		else:
			tag1 = c_tag1
			tag2 = c_tag2
	except Exception, e:
		exclog.error('\n%s' % traceback.format_exc(e))
	return ret, tag1, tag2


def get_query_type_name(ret):
	'''
		功能: 返回问题类型名字
		params:
			ret: 问题类型id
		return:
			name: 问题类型名字，编码Unicode
	'''
	name = ''
	if ret not in INTEND:
		ret = -1
	name = INTEND[ret]
	return name


def get_query_classify_results(query_gbk):
	'''
		功能: 调用问题类型分类接口，返回问题类型及答案tag
		params:
			query_gbk: 原始query，编码gbk
		return:
			ret: 问题类型，失败返回-1
			tag1: 答案tag，编码Unicode，默认为空
			tag2: 答案tag，编码Unicode，默认为空
	'''
	ret = -1
	tag1 = ''
	tag2 = ''
	query_classify = query_lib.query_classify
	query_classify.restype = c_char_p
	out = query_classify(query_gbk)
	ret, tag1, tag2 = split_result(out)
	return ret, tag1.decode('gbk', 'ignore'), tag2.decode('gbk', 'ignore')


def split_result(line):
	'''
		功能: 解析问题类型分类器返回的结果
		params:
			line: 问题类型分类器返回的结果，编码gbk
		return:
			ret: 问题类型，失败返回-1
			tag1: 答案tag，编码gbk，默认为空
			tag2: 答案tag，编码gbk，默认为空
	'''
	ret = -1
	tag1 = ''
	tag2 = ''
	pos = line.find('|^split$|')
	if pos >= 1:
		try:
			ret = int(line[0:pos])
		except:
			ret = -1
		line = line[pos+9:]
	if ret == 2 or ret == 3 or ret == 13:
		pos = line.find('|^TYPE$|')
		if pos != -1:
			items = line.split('\t')
			for item in items:
				pos = item.find('|^TYPE$|')
				if pos != -1:
					tag1 = item[0:pos]
					tag2 = item[pos+8:]
					break
	return ret, tag1, tag2



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


	tag1 = ''
	tag2 = ''
	querys = [u'python好还是c++好', u'python和c++哪个好', u'怎么减肥', u'蟑螂喜欢吃什么']
	for query in querys:
		ret = get_query_type(query)
		ret, tag1, tag2 = get_query_type_and_tag(query)
		print '>>>>>>>>>>'
		print 'query:' + query.encode('utf-8')
		print 'query_type:' + str(ret)
		print 'query_type_name:' + get_query_type_name(ret)
		print 'tag1:' + tag1.encode('utf-8')
		print 'tag2:' + tag2.encode('utf-8')
		print '\n\n'
