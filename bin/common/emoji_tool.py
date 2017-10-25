#coding=utf8
import os
import sys
import time
import logging

import chardet
import binascii
import pdb
import random

from rdd import RDD
from trie import TagMake
from collections import Counter
import traceback

from tornado.options import options

detlog = logging.getLogger('details')
exclog = logging.getLogger('exception')


c_curr_dir = os.path.dirname(os.path.abspath(__file__))
emoji_qq = os.path.join(c_curr_dir, '../../data/emoji_data/emoji_qq')
emoji_wx = os.path.join(c_curr_dir, '../../data/emoji_data/emoji_wx')
emoji_sb = os.path.join(c_curr_dir, '../../data/emoji_data/emoji_sb')
emoji_all = os.path.join(c_curr_dir, '../../data/emoji_data/emoji_all')
emoji_ot = os.path.join(c_curr_dir, '../../data/emoji_data/emoji_ot')
emoji_replies = os.path.join(c_curr_dir, '../../data/emoji_data/emoji_replies')


randEmojiMAX = 0
emoji_tree = TagMake()
emoji_map = {}
emoji_dict = {}
emotion_dict = {}
emoji_rand_set = []
label = ['Softbank unicode','Wechat emoji']


if options.service == "qqgroup" or options.service == "groupqa":
	emoji_reply_set = ['QQ emoji', 'Text']
	emoji_dirs = [emoji_qq, emoji_sb, emoji_all, emoji_ot]
else:
	emoji_reply_set = ['Text', 'Wechat_emoji', 'Other']
	emoji_dirs = [emoji_wx, emoji_sb, emoji_all]


try:
	for rel_emoji_dir in emoji_dirs:
		emoji_dir = os.path.join(c_curr_dir, rel_emoji_dir)
		emoji_tmp = RDD.TextFile(emoji_dir).map(lambda x:x.split('\t')[0]).collect()
		[emoji_tree.add_tag(word) for word in emoji_tmp]

		if rel_emoji_dir == emoji_qq or rel_emoji_dir == emoji_wx:
			emoji_rand_set = emoji_tmp
			randEmojiMAX = len(emoji_rand_set)

		for line in open(emoji_dir):
			key, hex, val,description,emotion = line.split('\t')
			if len(emotion.strip()) > 0:
				emoji_dict[key] = emotion.strip()
			emoji_map[key] = val
			if description in label:
				emoji_tree.add_tag(val)
				emoji_map[val] = val+description
	detlog.info("============= emoji tool imported ! =============")
except Exception, e:
	s = sys.exc_info()
	exclog.info('\n%s' % (traceback.format_exc(e)))


try:
	for line in open(emoji_replies):
		line_list = line.strip().split("\t")
		if line_list[1] in emoji_reply_set:
			if line_list[0] not in emotion_dict:
				emotion_dict[line_list[0]] = line_list[2]
			else:
				emotion_dict[line_list[0]] = emotion_dict[line_list[0]] + "#" + line_list[2]
except Exception, e:
	exclog.info('\n%s' % (traceback.format_exc(e)))





def replace_emoji(query):
	emoji_lst = emoji_tree.make(query)
	for emoji in emoji_lst:
		key, i, j = emoji
		val = emoji_map[key]
		query = query.replace(key, val, 1)
	return query


def clean_emoji_in_query(query, platform):

	# ret s
	flag = 0
	emoji_reply = ''
	cleaned_query = query

	emoji_line=''
	char_value=''
	returnQuery = {}
	emoji_list = emoji_tree.make_repeat(query.encode("utf-8"))
	begin = 0
	if len(emoji_list) == 0: # pure text
		returnQuery['label']='string'
		flag = 0
		emoji_reply = ''
		cleaned_query = query
	else:
		for emo in emoji_list:
			e,i,j = emo
			char_value += query[begin:i].lstrip()
			begin = i+j

		if begin < len(query) - 1:
			char_value += query[begin:len(query)].lstrip()

		if len(char_value) > 0: # regard as mainly text
			flag = 0
			emoji_reply = ''
			cleaned_query = char_value
		else: # regard as emoji
			flag = 1
			emoji_reply = emoji2query(emoji_list, platform)
			cleaned_query = query

	return flag, emoji_reply, cleaned_query


def get_emotion(emoji_label_dict):

	return_dict = {}
	emotion_list = []
	query_emotion_dict = {}
	query_emoji_len = len(emoji_label_dict)

	for (k,v) in emoji_label_dict.items():
		#print "emoji_label_dict_key=%s,value=%d" %(k,v)
		if k not in emoji_dict:
			continue
		emotionLabel = emoji_dict[k].split('|')
		for label in emotionLabel:
			if label in query_emotion_dict:
				query_emotion_dict[label] += 1
			else:
				query_emotion_dict[label] = 0

	emotion_list = [item for item in query_emotion_dict]
	return emotion_list


def emoji2query(emoji_list, platform):
	emoji_label_dict = {}
	query= ''
	for emo in emoji_list:
		e,i,j = emo
		if e in emoji_label_dict:
			emoji_label_dict[e] += 1
		else:
			emoji_label_dict[e] = 0

	len_emoji_label_dict = len(emoji_label_dict)
	len_emoji_list = len(emoji_list)
	emotion_list = get_emotion(emoji_label_dict)
	len_emotion_class = len(emotion_list)

	if len_emotion_class == 0:
		if len_emoji_label_dict > 1:
			ret_len = random.randint(4,9)
			for i in range(ret_len):
				rtt =random.randint(0,randEmojiMAX-1)
				query += emoji_rand_set[rtt]
		else:
			ret_len = random.randint(1,3*len_emoji_list)%30+1
			for i in range(ret_len):
				query += emoji_list[0][0]
	else:
		for i in range(len_emoji_list):
			emotion_label = emotion_list[random.randint(0,len_emotion_class-1)]
			if emotion_label not in emotion_dict:
				query += emoji_list[0][0]
				continue

			emotion = emotion_dict[emotion_label].split("#")
			# TODO @zhengliming
			emotmp = emotion[random.randint(0,len(emotion)-1)]
			query += emotmp
			if emotmp not in emoji_dict:
				query = emotmp
				break

	return query


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


