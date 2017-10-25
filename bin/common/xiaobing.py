#coding=utf8
import os
import sys
import pdb
import time
import json
import urllib
import base64
import traceback
sys.path.append('../')
sys.path.append('../../')
sys.path.append('../lib')
sys.path.append('../../lib')
sys.path.append('../conf')
sys.path.append('../../conf')
import requests
from rdd import RDD
from trie import TagMake
from config import Config


curr_dir = os.path.dirname(os.path.abspath(__file__))
block_xiaobing_words = RDD.TextFile(os.path.join(curr_dir, Config.XIAOBING_BLOCK_WORD)).map(lambda x:x.strip().decode('utf8')).collect()
block_xiaobing_tree = TagMake()
[block_xiaobing_tree.add_tag(word) for word in block_xiaobing_words]




def sendmsg_xiaobing(msg):
    url = "http://m.weibo.cn/msgDeal/sendMsg?"
    st = "ab1de8"
    data = "fileId=null&uid=5175429989&content=%s&st=%s"%(urllib.quote(msg), st)
    # noob
    #cookie = "_T_WM=b78396bea5d9421cbe9addebf1f9eec8; ALF=1472189097; SCF=AvYeNhf2Ecjw0eNmQd2T8RpNGpxup5tTnnr_k20jLMwchjPmjfrx3NEupNINeazdchDOutRpkNOdMoJqSQZagjo.; SUB=_2A256nDfADeTxGeRP61ES-C3PyzuIHXVWf1mIrDV6PUJbktBeLVbmkW0a2yqi5Np3MqY09z2nufRbXx7ecA..; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9WFgzgdZi4msrlTHcDZDXZUx5JpX5o2p5NHD95QEeK50e0n0e05NWs4Dqc_oi--ciKnRiK.pi--ciKn0i-z0i--Ri-2ciKnpi--Ri-zfi-zNi--Xi-zRi-8Wi--fi-2fi-i2i--fiK.7i-8hi--NiKLWiKnXi--fiK.7iKy2i--fi-82iK.Ni--fiK.0iKy8; SUHB=03oUUIgPWiKEdB; SSOLoginState=1469597584"
    cookie = "_T_WM=277311a21eaf8866b81e4d0894781966; ALF=1477731001; SCF=AgF7LjWle8LDinKWYmi0kSOV0QdABYNDWdP7Y-lh7JFY_FWavyFtR5E-8g-EYkZU3sGaXLdBjQZlwke    SUeAAeHk.; SUB=_2A2566KWVDeTxGeNH4lMR8CrPzDyIHXVWEsvdrDV6PUJbktBeLVHAkW06D-bFZm786z2Ml8eoKhNOo5EOhQ..; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9W5xlqSsUlzZp    XLP-VOGOgcC5JpX5o2p5NHD95Qf1K.peh5Xe0M7Ws4Dqcjdi--fiKn7i-8Wi--Ri-8si-i8i--fiK.0i-2f; SUHB=0RyqF4LQgVx9P4; SSOLoginState=1475139013; H5_INDEX=1; H5_INDEX_    TITLE=%E5%80%AA%E8%AF%BE%E5%93%A5; M_WEIBOCN_PARAMS=luicode%3D20000174"

    headers = {"Host": "m.weibo.cn","Connection": "keep-alive", "Content-Length": len(data),"Accept": "application/json", "Origin": "http://m.weibo.cn", "X-Requested-With": "XMLHttpRequest","User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36", "Content-Type": "application/x-www-form-urlencoded", "Referer": "http://m.weibo.cn/msg/chat?uid=5175429989", "Accept-Encoding": "gzip, deflate", "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.4", "Cookie":cookie}

    NUM_TRYS = 10
    ok = -1
    num_trys = 0
    try:
        while num_trys < NUM_TRYS:
            print("post num of try: %d" % num_trys)
            response = requests.post(url, headers=headers, data=data)
            if response:
                resp_js = json.loads(response.content)
                if "ok" in resp_js:
                    ok = resp_js["ok"]
            if ok == 1:
                break;
            num_trys = num_trys + 1
        if num_trys >= NUM_TRYS:
            ans = "POST: num of trys exceed %d" % NUM_TRYS
            return ans
    except Exception,e:
        print("xiaobing post method exception")
        print(traceback.format_exc())

    url = "http://m.weibo.cn/msg/messages?uid=5175429989&page=1"
    get_headers = {"Host": "m.weibo.cn", "Connection": "keep-alive", "Cache-Control": "max-age=0", "Upgrade-Insecure-Requests": 1, "User-Agent": "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8", "Accept-Encoding": "gzip, deflate, sdch", "Accept-Language": "zh-CN,zh;q=0.8,en-US;q=0.6,en;q=0.4", "Cookie": cookie}

    time.sleep(0.5)
    ans = ""
    num_trys = 0
    try:
        id = 0
        while True:
            print("Get num of try: %d" % num_trys)
            response = requests.get(url, headers=get_headers)
            if response:
                obj = json.loads(response.text)
                if "data" in obj:
                    id = int(obj['data'][0]['sender']['id'])
                    print("send id: %d" % id)
                    ans = obj['data'][0]['text'].encode('utf8')
            if id == 5175429989:
                break
            num_trys = num_trys + 1
        #if num_trys >= NUM_TRYS:
        #    ans = "GET: num of trys exceed %d" % NUM_TRYS
        return ans
    except Exception, e:
        print("xiaobing get method exception, return empty")
        print(traceback.format_exc())
        return str(e).encode("utf-8")

def login(username, password):
    username = base64.b64encode(username.encode('utf-8')).decode('utf-8')
    postData = {
        "entry": "sso",
        "gateway": "1",
        "from": "null",
        "savestate": "30",
        "useticket": "0",
        "pagerefer": "",
        "vsnf": "1",
        "su": username,
        "service": "sso",
        "sp": password,
        "sr": "1440*900",
        "encoding": "UTF-8",
        "cdult": "3",
        "domain": "sina.com.cn",
        "prelt": "0",
        "returntype": "TEXT",
    }
    loginURL = r'https://login.sina.com.cn/sso/login.php?client=ssologin.js(v1.4.18)'
    session = requests.Session()
    res = session.post(loginURL, data = postData)
    jsonStr = res.content.decode('gbk')
    info = json.loads(jsonStr)
    if info["retcode"] == "0":
        print('login success')
        cookies = session.cookies.get_dict()
        cookies = [key + "=" + value for key, value in cookies.items()]
        cookies = "; ".join(cookies)
        print(cookies + '\n');
    else:
        print("login failed the reason %s" % info["reason"])

    return cookies

#cookie = login('cuew1987@163.com', 'zuojjcom')
#cookie = login('18225051944', 'woshilijin')
cookie = "ALF=1483064375; SCF=AgF7LjWle8LDinKWYmi0kSOV0QdABYNDWdP7Y-lh7JFY-Kzgj0MhfJzrUHXjcOglymSKIpPA7NsC-yufuBcdcfI.; SUB=_2A251OkcCDeTxGeNH4lMR8CrPzDyIHXVWxWlKrDV6PUJbktANLXbdkW0eUuppcSko1-iiaGRGY0G8fnl7LA..; SUBP=0033WrSXqPxfM725Ws9jqgMF55529P9D9W5xlqSsUlzZpXLP-VOGOgcC5JpX5o2p5NHD95Qf1K.peh5Xe0M7Ws4Dqcjdi--fiKn7i-8Wi--Ri-8si-i8i--fiK.0i-2f; SUHB=0z1AW_ImfIIFHN; SSOLoginState=1480472402; _T_WM=462d1f45bf07f6265fb79e707b19cf16; M_WEIBOCN_PARAMS=uicode%3D20000174; H5_INDEX=1; H5_INDEX_TITLE=%E5%80%AA%E8%AF%BE%E5%93%A5" 

def postMsg(msg):
    url = "http://weibo.com/aj/message/add?"
    data = "ajwvr=6&__rnd="+ str(int(time.time())) +"&location=msgdialog&module=msgissue&style_id=1&text=" + msg + "&uid=5175429989&tovfids=&fids=&el=[object HTMLDivElement]&_t=0"
    headers = {
        "Accept": "*/*",
        "Accept-Encoding": "gzip, deflate",
        "Accept-Language": "zh-CN,zh;q=0.8,ko;q=0.6,en;q=0.4,zh-TW;q=0.2,fr;q=0.2",
        "Connection": "keep-alive",
        "Content-Length": str(len(msg)),
        "Content-Type": "application/x-www-form-urlencoded",
        "Cookie": cookie,
        "Host": "weibo.com",
        "Origin": "http://weibo.com",
        "Referer": "http://weibo.com/message/history?uid=5175429989&name=%E5%B0%8F%E5%86%B0",
        "User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/53.0.2785.143 Safari/537.36",
        "X-Requested-With": "XMLHttpRequest"
    }

    info = {}
    try:
        r = requests.post(url, headers=headers, data=data, timeout=3.0)
        jsonStr = r.content.decode('utf-8')
        info = json.loads(jsonStr)
    except Exception, e:
        info["err"] = str(e)
    return info

def getMsg(msg):
    url = "http://m.weibo.cn/msg/messages?uid=5175429989&page=1"
    get_headers = {
        "Host": "m.weibo.cn",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "Upgrade-Insecure-Requests": str(1),
        "X-Requested-With": "XMLHttpRequest",
        "Referer": "http://m.weibo.cn/msg/chat?uid=5175429989",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 9_1 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13B143 Safari/601.1",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, sdch",
        "Accept-Language": "zh-CN,zh;q=0.8,ko;q=0.6,en;q=0.4,zh-TW;q=0.2,fr;q=0.2",
        "Cookie": cookie
    }
    return repeatGet(url, get_headers, msg)

def repeatGet(url, get_headers, msg):
    time.sleep(0.05)
    response = requests.get(url, headers=get_headers)
    result = ""
    if response:
        obj = json.loads(response.text)
        if "data" in obj:
            result = obj['data'][0]['text'].encode('utf8')
            #print(result + '==' + msg)
            #print(result == msg)
            if(result == msg):
                result = repeatGet(url, get_headers, msg)
            if result and result.decode("utf-8") == u"分享语音":
                result = None#result + obj['data'][0]['attachment'][0]['filename'].encode('utf-8')
    return result


def sendmsg_xiaobing2(msg):
    try:
        info = postMsg(msg)
        if info["code"] == "100000":
            print("send success")
            result = getMsg(msg)
            if len(block_xiaobing_tree.make(result)) > 0:
                info["code"] = 1
                result = ""
            else:
                return result, info["code"]
    except Exception, e:
        print(traceback.format_exc())
    return result, info["code"]


if __name__ == "__main__":
    while True:
        msg = str(raw_input('say: '))
#result = sendmsg_xiaobing(msg)
        result, debug_info = sendmsg_xiaobing2(msg)
        print "xiaobin: "+result
