#coding=utf-8

import check_dirty_answer as dirty
import string_process as str_judge
import tencent_segment as tc_seg


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

# answer根据source的过滤条件
SOURCE_FILTER = {
		'wechat':('common', 'multi'),
		'tsinghua_robot':('common', 'multi'),
		'weimi':('common', 'multi'),
		'gd_mobile':('special', 'text'),
		'aiplatform':('special', 'text'),
		'aiplatform_chat':('special', 'text'),
		'aiplatform_qa':('special', 'text'),
		'aiplatform_teemo':('special', 'text'),
		'yzdd_onsite':('special', 'text'),
		'common_show':('special', 'text'),
		'show_medical':('special', 'text'),
		'qqgroup':('common', 'multi'),
		'qcloud':('special', 'text'),
		'afanti':('special', 'text'),
		'wenda':('common', 'multi'),
		'board':('common', 'multi'),
		'test':('common', 'multi'),
}


def judge_online_answer_quality(query, params, answer, debug_info, p_answer_filter):
	"""判断answer质量
	Args:
		query: 原始query，编码Unicode
		params: query信息
		answer: 编码Unicode
		debug_info: debug信息
		p_answer_filter: answer过滤词表
	Returns:
		answer: 编码Unicode，若被过滤掉，返回None
		debug_info: debug信息
	Raises:
	"""
	answer, debug_info = judge_online_common_answer_quality(query, params, answer, debug_info, p_answer_filter)
	answer, debug_info = judge_online_special_answer_quality(query, params, answer, debug_info)
	return answer, debug_info

def judge_online_common_answer_quality(query, params, answer, debug_info, p_answer_filter):
	"""通用模块，判断answer质量
	Args:
		query: 原始query，编码Unicode
		params: query信息
		answer: 编码Unicode
		debug_info: debug信息
		p_answer_filter: answer过滤词表
	Returns:
		answer: 编码Unicode，若被过滤掉，返回None
		debug_info: debug信息
	Raises:
	"""
	query_type = debug_info['query_type']
	if answer == '' or answer == None:
		debug_info['status'] = 'answer empty'
		return None, debug_info
	dirty_flag, dirty_word = dirty.check_dirty_answer(answer.decode('utf-8'))
	if dirty_flag and debug_info['is_ugc'] == True:
		debug_info['status'] = 'dirty word[' + dirty_word + ']'
		return None, debug_info
	if len(query) <= 2 and debug_info['priority_id'].find('baike') == -1:
		debug_info['status'] = 'not baike answer, query too short'
		return None, debug_info
	if debug_info['use_ugc_conf'] == False and debug_info['is_ugc'] == True:
		debug_info['status'] = 'filter ugc answer'
		return None, debug_info
	if answer.find(query) != -1 and len(query) + 4 >= len(answer):
		debug_info['status'] = 'answer contain query'
		return None, debug_info
	if debug_info['is_ugc'] == True and len(str_judge.delete_punctuation(answer)) <= 2:
		debug_info['status'] = 'answer too short(' + str(len(answer)) + ')'
		return None, debug_info
	if debug_info['is_ugc'] == True and p_answer_filter.search(answer) != None:
		debug_info['status'] = 'answer filter(' + p_answer_filter.search(answer).group(0) + ')'
		return None, debug_info
	if debug_info['q_type_filter'] == True and (query_type == 0 or query_type == 1) and debug_info['priority_id'] == 'qa':
		debug_info['status'] = 'query type filter(' + str(query_type) + ')'
		return None, debug_info
	if debug_info['is_ugc'] == True and query_type == 4 and query.find(u'现在') != -1:
		debug_info['status'] = 'time filter'
		return None, debug_info
	if debug_info['is_ugc'] == True and comm.is_contain_url(answer, tc_seg.seg_with_pos(answer)):
		debug_info['status'] = 'ugc answer contain url'
		return None, debug_info
	if debug_info['priority'] >= ANSWER_PRIORITY['qa'][0]:
		if (debug_info['index'] < 4 and debug_info['wendaF'] < 5) or (debug_info['index'] >= 4 and debug_info['wendaF'] <= 5):
			debug_info['status'] = 'low wendaF'
			return None, debug_info
		if debug_info['trank'] < 3:
			debug_info['status'] = 'low trank'
			return None, debug_info
		if debug_info['rel'] < 0.3:
			debug_info['status'] = 'low rel'
			return None, debug_info
	if debug_info['is_ugc'] == True:
		_flag, answer, ch = str_judge.is_contained_special_characters(answer)
		if _flag:
			debug_info['status'] = 'charater deprecated(' + ch + ')'
			return None, debug_info
	return answer, debug_info

def judge_online_special_answer_quality(query, params, answer, debug_info):
	"""根据source过滤answer
	Args:
		query: 原始query，编码Unicode
		params: query信息
		answer: 编码Unicode
		debug_info: debug信息
	Returns:
		answer: 编码Unicode，若被过滤掉，返回None
		debug_info: debug信息
	Raises:
	"""
	if answer == None or answer == '':
		return None, debug_info
	source = params.get('source', '')
	if source not in SOURCE_FILTER or SOURCE_FILTER[source][0] == 'special':
		if ANSWER_PRIORITY[debug_info['priority_id']][2] != 'text' and debug_info['priority_id'] == 'VR_map_1':
			answer = u'我也不知道呢，你可以用地图工具搜索一下哦。'
		if ANSWER_PRIORITY[debug_info['priority_id']][2] != 'text':
			answer = None
			debug_info['status'] = 'answer is not text'
		#if debug_info['is_ugc'] == True and len(answer) > 100:
		#	debug_info['flag'] = 'answer too long(' + str(len(answer)) + ')'
		#	return None, debug_info
	if source == 'qqgroup' and len(answer) > 200:
		answer = None
		debug_info['status'] = 'qqgroup answer too long'
	return answer, debug_info


