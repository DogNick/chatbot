#a1. import sys
import os

#a2. import thirdparty
import requests

def upload(filename):
	token = 'ew_XYTgQWhRuJ0cLrRhV8MzDuZYnboQiPvRb9aHbp88AWj6y2RV0LLpU8bhcgINSjy-7FrWRYY66SWdjAgIY1Bd6pztOaiOCXgfgangm-VUDQNeAAAWJG'
	url = 'https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=' + token + '&type=image'
	files= {'media': open(filename, 'rb')}
	r = requests.post(url, files=files, verify = False)
	print r.text

path='upload'
for dirpath,dirnames,filenames in os.walk(path):
	for file in filenames:
		fullpath=os.path.join(dirpath,file)
		upload(fullpath)


