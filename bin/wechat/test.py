# -*- coding: utf-8 -*-
# filename: material.py
import urllib2
import json
import poster.encode
import pdb
from poster.streaminghttp import register_openers

class Material(object):
    def __init__(self):
        register_openers()
    #上传
    def uplaod(self, accessToken, filePath, mediaType):
        openFile = open(filePath, "rb")
        fileName = "hello"
        param = {'media': openFile, 'filename': fileName}
        #param = {'media': openFile}
        postData, postHeaders = poster.encode.multipart_encode(param)

        postUrl = "https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=%s&type=%s" % (accessToken, mediaType)
        request = urllib2.Request(postUrl, postData, postHeaders)
        urlResp = urllib2.urlopen(request)
        print urlResp.read()
    #下载
    def get(self, accessToken, mediaId):
        postUrl = "https://api.weixin.qq.com/cgi-bin/material/get_material?access_token=%s" % accessToken
        postData = "{ \"media_id\": \"%s\" }" % mediaId
        urlResp = urllib2.urlopen(postUrl, postData)
        headers = urlResp.info().__dict__['headers']
        if ('Content-Type: application/json\r\n' in headers) or ('Content-Type: text/plain\r\n' in headers):
            jsonDict = json.loads(urlResp.read())
            print jsonDict
        else:
            buffer = urlResp.read()  # 素材的二进制
            mediaFile = file("test_media.jpg", "wb")
            mediaFile.write(buffer)
            print "get successful"
    #删除
    def delete(self, accessToken, mediaId):
        postUrl = "https://api.weixin.qq.com/cgi-bin/material/del_material?access_token=%s" % accessToken
        postData = "{ \"media_id\": \"%s\" }" % mediaId
        urlResp = urllib2.urlopen(postUrl, postData)
        print urlResp.read()
    
    #获取素材列表
    def batch_get(self, accessToken, mediaType, offset=0, count=20):
        postUrl = ("https://api.weixin.qq.com/cgi-bin/material"
               "/batchget_material?access_token=%s" % accessToken)
        postData = ("{ \"type\": \"%s\", \"offset\": %d, \"count\": %d }"
                    % (mediaType, offset, count))
        urlResp = urllib2.urlopen(postUrl, postData)
        r = urlResp.read()
        print r
        j = json.loads(r)
        lst = j['item']
        l = []
        for item in lst:
            l.append(item['media_id'])
        print l


if __name__ == '__main__':
    myMaterial = Material()
    accessToken = 'BOuwwsLq0nS0AzHhmAMvV7UIHUrCStznk0zWGJBIMw3j-Cy88iO290pNijYvwaaEk3Zgfy8U5BEVTzS2tvexGEhoZg3JhTltFGK_vffKw4_WXvzxfEQ_5nR2FYbt-eoAOKYeACAHDR'
    mediaType = "image"
    myMaterial.batch_get(accessToken, mediaType)
