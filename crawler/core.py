import urllib
import urllib.request
import gzip
import os
import re
import time
import requests
import logging
import random
from bs4 import BeautifulSoup
from crawler.utils.yaml_utils import load_yaml


logger = logging.getLogger(__name__)


class Crawl:
    def request(self, url, proxy_list, data=None, headers=None, method="GET"):
        # IP代理
        if len(proxy_list) > 0:
            # 随机从IP列表中选择一个IP
            proxy = random.choice(proxy_list)
            logger.info("IP代理:{}".format(proxy))
            # 基于选择的IP构建连接
            handle = urllib.request.ProxyHandler({proxy[0]: proxy[1]})
            opener = urllib.request.build_opener(handle)
            urllib.request.install_opener(opener=opener)
        request = urllib.request.Request(url=url, data=data, headers=headers, method=method)
        response = self.urlopen(request)
        return response
    
    def urlopen(self, url):
        try:
            response = urllib.request.urlopen(url)
        except urllib.error.HTTPError as e:
            logger.error("{}: {}".format(e, url.full_url))
            logger.error("cookie可能已失效，请更新cookie后重试！")
            raise Exception(e)
        return response

    def write_txt(self, path, content):
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)

    def read_txt(self, path):
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        return content
    
class application():

    def __init__(self, config_file, application):
        self.crawler = Crawl()
        self.config = load_yaml(config_file)[application]
        self.base_url = self.config["base_url"]
        # 爬取的图片保存地址
        self.save_dir = self.config["save_dir"]
        os.makedirs(self.save_dir, exist_ok=True)
        # 爬取相关的参数
        self.crawl_delay = float(self.config["crawl_delay"])
        self.download_delay = float(self.config["download_delay"])
        self.user_agent = [
            "Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/35.0.1916.153 Safari/537.36",
            "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:30.0) Gecko/20100101 Firefox/30.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_2) AppleWebKit/537.75.14 (KHTML, like Gecko) Version/7.0.3 Safari/537.75.14",
            "Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Win64; x64; Trident/6.0)",
            'Mozilla/5.0 (Windows; U; Windows NT 5.1; it; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11',
            'Opera/9.25 (Windows NT 5.1; U; en)',
            'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
            'Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.5 (like Gecko) (Kubuntu)',
            'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.0.12) Gecko/20070731 Ubuntu/dapper-security Firefox/1.5.0.12',
            'Lynx/2.8.5rel.1 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/1.2.9',
            "Mozilla/5.0 (X11; Linux i686) AppleWebKit/535.7 (KHTML, like Gecko) Ubuntu/11.04 Chromium/16.0.912.77 Chrome/16.0.912.77 Safari/535.7",
            "Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:10.0) Gecko/20100101 Firefox/10.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
        ]
        self.headers = {
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding":"gzip, deflate, br, zstd",
        "Accept-Language":"zh,zh-CN;q=0.9,en;q=0.8",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        }
        # 更新headers
        for k, v in self.config["headers"].items():
            if v:
                self.headers[k] = v
        # logging设置
        log_file = os.path.join(self.save_dir, "{}.log".format(time.strftime('%Y%m%d_%H', time.localtime())))
        if self.config["set_logfile"]:
            hander = logging.FileHandler(filename=log_file)
        else:
            hander = logging.StreamHandler()
        logger.setLevel(logging.INFO) # 设置日志级别
        # log格式
        fmt = '%(asctime)s - %(levelname)s: %(message)s'
        format_str = logging.Formatter(fmt)#设置日志格式
        hander.setFormatter(format_str)
        logger.addHandler(hander)
        # proxy
        if self.config["use_proxy"]:
            self.proxy_list = [_.split("|") for _ in self.config["proxy"]]
        else:
            self.proxy_list = []
        # 可用IP代理过滤
        self.filter_proxy()
        # 打印基本参数
        logger.info("header: {}".format(self.headers))
        logger.info("proxy: {}".format(self.proxy_list))

    def get_urls(self):
        return [self.base_url]

    def get_title(self, html):
        bs = BeautifulSoup(html, "html.parser")
        # 读取店铺名
        shop_name = bs.find("h1",class_="shop-name").string.strip()
        if len(shop_name) == 0:
            raise Exception("店铺名称为空！")
        return shop_name
    
    def check_login(self, html):
        """检查网页是否登录"""
        if re.search("登录失败", html):
            logger.info("网页未登录账号，请更新Cookie后重试！")
            raise Exception("网页未登录账号，请更新Cookie后重试！")
    
    def proxy_is_availabel(self, proxy):
        try:
            # 设置重连次数
            requests.adapters.DEFAULT_RETRIES = 3
            proxy_dict = {proxy[0]:proxy[1]}
            res = requests.get(url="http://icanhazip.com/", timeout=2, proxies=proxy_dict)
            if res.text.strip() == proxy[1].split(":")[0]:
                return True
            else:
                logger.info(f"IP代理{proxy[0]}://{proxy[1]}无效！")
                print(f"IP代理{proxy[0]}://{proxy[1]}无效！")
                return False
        except:
            logger.info(f"IP代理{proxy[0]}://{proxy[1]}无效！")
            print(f"IP代理{proxy[0]}://{proxy[1]}无效！")
            return False
        
    def filter_proxy(self):
        """检查IP代理池是否可用"""
        self.proxy_list = [_ for _ in self.proxy_list if self.proxy_is_availabel(_)]

    def crawl(self):
        # 下载html
        for i, url in enumerate(self.urls):
            self.headers["User-Agent"] = random.choice(self.user_agent)
            # check ip proxy
            self.filter_proxy()
            # 链接网址
            resp = self.crawler.request(url=url, proxy_list=self.proxy_list, headers=self.headers)
            if resp.code == 200:
                print(f">>> 链接{url}成功响应!")
                logger.info(f">>> 链接{url}成功响应!")
            else:
                print(f">>> 链接{url}响应失败:{resp.code}")
                logger.info(f">>> 链接{url}响应失败:{resp.code}")
            html = resp.read()
            html = gzip.decompress(html).decode("utf-8")
            # 保存html
            self.check_login(html)
            shop_name = self.get_title(html)
            dir_path = os.path.join(self.save_dir, f"{shop_name}")
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
            page_num = range(self.page_start, self.page_end+1)[i]
            path = os.path.join(dir_path, f"comment-page-{page_num}.html")
            self.crawler.write_txt(path, html)
            resp.close()
            # 下载 图片
            pic_dir = os.path.join(dir_path, f"comment-pic")
            if not os.path.exists(pic_dir):
                os.makedirs(pic_dir, exist_ok=True)
            self.download_pic(html, pic_dir, page_num, self.proxy_list)
            time.sleep(self.crawl_delay)
        print(f">>> 所有图片已完成下载，请查看:\n{pic_dir}")
        logger.info(f">>> 所有图片已完成下载，请查看:\n{pic_dir}")

    def download_pic(self, html, pic_dir, page_num, proxy_list):
        bs = BeautifulSoup(html, "html.parser")
        def is_img_and_has_data_big(tag):
            return tag.has_attr("data-big")
        items = bs.find_all(is_img_and_has_data_big)
        for i,item in enumerate(items):
            img_link = item.attrs["data-big"]
            # 获取无水印图片
            img_link = img_link.replace("joJrvItByyS4HHaWdXyO_I7F0UeCRQYMHlogzbt7GHgNNiIYVnHvzugZCuBITtvjski7YaLlHpkrQUr5euoQrg", "")
            if not img_link.endswith(".jpg"):
                img_link = img_link.split(".jpg")[0]+".jpg"
            # 延时下载
            time.sleep(self.download_delay)
            logger.info("正在下载: {}".format(img_link))
            saveimg = os.path.join(pic_dir, f"p{page_num}_{i}{os.path.splitext(img_link)[-1]}")
            # IP代理
            if len(proxy_list) > 0:
                # 随机从IP列表中选择一个IP
                proxy = random.choice(proxy_list)
                # 基于选择的IP构建连接
                handle = urllib.request.ProxyHandler({proxy[0]: proxy[1]})
                opener = urllib.request.build_opener(handle)
                urllib.request.install_opener(opener=opener)
            urllib.request.urlretrieve(img_link, saveimg) # 下载链接内容
