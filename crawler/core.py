import urllib
import urllib.request
import gzip
import os
import time
import logging
from bs4 import BeautifulSoup
from crawler.utils.yaml_utils import load_yaml


logger = logging.getLogger(__name__)


class Crawl:
    def request(self, url, data=None, headers=None, method="GET"):
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

    def get_urls(self):
        return [self.base_url]

    def get_title(self, html):
        bs = BeautifulSoup(html, "html.parser")
        # 读取店铺名
        shop_name = bs.find("h1",class_="shop-name").string.strip()
        if len(shop_name) == 0:
            raise Exception("店铺名称为空！")
        return shop_name
    
    def crawl(self):
        # 下载html
        for i, url in enumerate(self.urls):
            resp = self.crawler.request(url=url, headers=self.headers)
            if resp.code == 200:
                print(f">>> 链接{url}成功响应!")
                logger.info(f">>> 链接{url}成功响应!")
            else:
                print(f">>> 链接{url}响应失败:{resp.code}")
                logger.info(f">>> 链接{url}响应失败:{resp.code}")
            html = resp.read()
            html = gzip.decompress(html).decode("utf-8")
            # 保存html
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
            self.download_pic(html, pic_dir, page_num)
            time.sleep(self.crawl_delay)
        print(f">>> 所有图片已完成下载，请查看:\n{pic_dir}")
        logger.info(f">>> 所有图片已完成下载，请查看:\n{pic_dir}")

    def download_pic(self, html, pic_dir, page_num):
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
            urllib.request.urlretrieve(img_link, saveimg) # 下载链接内容
