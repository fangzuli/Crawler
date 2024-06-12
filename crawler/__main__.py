from crawler.core import application

class DaZhongDianPing(application):
    def __init__(self, config_file, application):
        super().__init__(config_file, application)
        # 获取urls
        self.shop_id = self.config["shop_id"]
        self.page_start = self.config["page_start"]
        self.page_end = self.config["page_end"]
        self.urls = self.get_urls()

    def get_urls(self):
        urls = [self.base_url.format(self.shop_id, _) for _ in range(self.page_start, self.page_end+1)]
        return urls



def main():
    # 爬取评论图片
    dianping = DaZhongDianPing(config_file="config/config.yaml", application="dazhongdianping")
    dianping.crawl()


if __name__ == "__main__":
    main()


    