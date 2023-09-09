# -*- coding:utf-8 -*-
#Freeware, NO COPYRIGHT, Use as it is.
#请确保使用对应版本的chromedriver.exe
#chrome version 116.0.5845.97

import sys
import os
import re
import requests
import json
import time
import signal
from bs4 import BeautifulSoup
from multiprocessing import Process, Lock


from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def end_main():
    sys.exit()

def is_number(s:str):
    try:
        float(s)
        return True
    except ValueError:
        pass
 
    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass
 
    return False

def del_file(path):
    ls = os.listdir(path)
    #print(ls)
    for i in ls:
        c_path = os.path.join(path, i)
        if os.path.isdir(c_path):
            del_file(c_path)
        else:
            os.remove(c_path)
            
def make_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
    else:
        del_file(path)


def string_split(a:str, sy:str):
    str_list = []
    try:
        str_list = a.split(sy)
        str_list = [x for x in str_list if x != ""]
    except:
        pass
    finally:
        return str_list

class Record(object):
    def __init__(self, logfile):
        self.lock = Lock()
        self.file = logfile
        self.lock.acquire()
        if os.path.exists(self.file) == False:
            f = open(self.file, 'w', encoding='utf-8')
            f.close()
        self.lock.release()

    def getData(self):
        self.lock.acquire()
        ret = []
        f = open(self.file, 'r', encoding='utf-8')
        for i in f.readlines():
            ret.append(i.replace("\n", ""))
        f.close()
        self.lock.release()

        return ret

    def appendData(self, data:str):
        self.lock.acquire()
        f = open(self.file, 'a+', encoding='utf-8')
        f.write(data + "\n")
        f.close()
        self.lock.release()

class Book(object):
    def __init__(self):
        self.title = ""
        self.entry_url = ""
        self.chapter_url = ""
        self.download_urls = []


class downloadTask(Process):
    def __init__(self, name, book:Book, record:Record, save_path:str):
        super(downloadTask, self).__init__()
        self.book = book
        self.save_path = save_path
        self.record = record

        self.lock = Lock()

    def run(self):
        service = Service(executable_path='./chromedriver/chromedriver.exe')
        options = webdriver.ChromeOptions()
        options.add_argument("headless")
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 10)

        try:
            ret = self.downloadBook()
        except:
            pass
        #self.close()


    def getPageText(self, url:str, timeout:int = 10):
        page_source = ""
        try:
            self.lock.acquire()
            self.driver.get(url)
            self.driver.implicitly_wait(timeout)
            self.wait.until(EC.presence_of_all_elements_located)
            page_source = self.driver.page_source
        except:
            pass
        finally:
            self.lock.release()
            return page_source


    def downloadBook(self):
        result = False
        #获取Chapter ID
        ps = self.getPageText(self.book.entry_url)
        soup = BeautifulSoup(ps, 'lxml')
        rets = soup.find_all(name='a', attrs={'class': 'btn btn-danger btn-square smooth-goto'})

        book_chapter = ""

        try:
            for ret in rets:
                if self.book.entry_url in ret['href']:
                    book_chapter = ret['href']
                    break
        except Exception as e:
            print(e)
            return result
        
        if book_chapter == '':
            print("No Chapter ID found!")
            return result

        #chapter_id = string_split(str(book_chapter), "/")[-1]

        self.book.chapter_url = book_chapter

        #获取所有页面下载地址
        ps = self.getPageText(self.book.chapter_url)
        soup = BeautifulSoup(ps, 'lxml')
        rets = soup.find_all(name='script')

        #参考https://janda.merahputih.moe/#api-hentai2read
        base_pic_url = "https://cdn-ngocok-static.sinxdr.workers.dev/hentai" 

        for ret in rets:
            if "var gData" in str(ret):
                #print(ret)
                gDataRegex = re.compile(r'.*({.*})', re.DOTALL)
                jstr_origin = gDataRegex.findall(str(ret))[0]
                jstr = jstr_origin.replace("\'", "\"")
                #print(jstr)
                js = json.loads(jstr)
                for i in js["images"]:
                    self.book.download_urls.append(base_pic_url + i)

                break

        if len(self.book.download_urls) > 0:
            #创建保存目录
            sp = self.save_path + self.book.title + '/'
            make_dir(sp)
            
            for pic_download_url in self.book.download_urls:
                print("pic_download_url=", pic_download_url)
                self.downPagePic(pic_download_url, sp)

            self.record.appendData(self.book.title)

            result = True

        return result

    def downPagePic(self, url:str, path:str, timeout:int = 10):
        result = False
        url_split = url.split('/')

        if len(url_split) == 0:
            return

        fn = url_split[-1]
        fs = path + fn
        print(fn)
        print(fs)

        self.lock.acquire()

        try:
            ret = requests.get(url = url)
            
            with open(fs, 'wb') as f:
                f.write(ret.content)
            result = True
        except:
            pass
        finally:
            self.lock.release()
            return result

    def close(self):
        self.driver.quit()


class MainTask(object):
    def __init__(self):
        service = Service(executable_path='./chromedriver/chromedriver.exe')
        options = webdriver.ChromeOptions()
        options.add_argument("headless")
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 10)
        self.lock = Lock()

    def getPageText(self, url:str, timeout:int = 10):
        page_source = ""
        try:
            self.lock.acquire()
            self.driver.get(url)
            self.driver.implicitly_wait(timeout)
            #self.wait.until(EC.presence_of_all_elements_located)
            page_source = self.driver.page_source
        except:
            pass
        finally:
            self.lock.release()
            return page_source

    def initTasks(self, start_url):
        books = []

        print("start_url:", start_url)
        ps = self.getPageText(start_url)
        soup = BeautifulSoup(ps, 'lxml')
        rets = soup.find_all(name='div', attrs={'class': 'col-xs-6 col-sm-4 col-md-3 col-xl-2'})
        
        #取得某一页的书本清单
        for ret in rets:
            try:
                book = Book()
                title_html = ret.find(name='a', attrs={'class': 'title'})
                book.entry_url = title_html['href']
                book.title = string_split(book.entry_url, '/')[-1]
                books.append(book)
            except Exception as e:
                print("Books Parser Exception:", title_html)
                print(e)
                continue
        return books
    
    def close(self):
        self.driver.quit()


def handler(signum, frame):
    global is_exit
    is_exit = True
    print("receive a signal %d, is_exit = %d"%(signum, is_exit))


if __name__ =="__main__":
    
    log = "books.txt"  #本子的记录设置，避免重复下载
    save_path = "./download/" #保存本子的目录
    MAX_TASK_LIMIT = 5  #多少个并行抓取进程
    MAX_PAGE_LIMIT = 10 #page_base的最大页面
    page_base = "https://hentai2read.com/hentai-list/category/rape/all/name-az" #要抓取的页面
    #抓取页面范围，请根据需要修改
    #https://hentai2read.com/hentai-list/category/rape/all/name-az/1/
    #https://hentai2read.com/hentai-list/category/rape/all/name-az/MAX_PAGE_LIMIT/

    #初始化
    task_list = []
    page_list = []
    finished_books = []
    is_exit = False

    app = MainTask() #实例化主程序
    record = Record(log) #实例化记录

    #支持Ctrl-C结束程序
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


    #读取已经完成的书本，避免重复下载
    finished_books = record.getData()
    print(finished_books)


    #生成要抓取的页面列表
    for p in range(1, MAX_PAGE_LIMIT):
        page_list.append(page_base + '/' + str(p) + '/')

    #循环抓取页面
    for page in page_list:
        if is_exit == True:
            break

        #获取页面中的书本集合
        books = app.initTasks(page)

        #循环抓取书本，每个书本一个进程，最多进程数 MAX_TASK_LIMIT
        for book in books:
            if is_exit == True:
                break
            
            print("----------------------------------------------------------")
            print("Title:", book.title)
            print("Entry_Url:", book.entry_url)

            #检查是否已经获取，可以删除log中的书本名来重新抓取
            if book.title in finished_books:
                print("book already done - ", book.title)
            
            #限制进程数，等待空余
            while True:
                if is_exit == True:
                    break
                task_list = [x for x in task_list if x.is_alive() == True]
                if len(task_list) < MAX_TASK_LIMIT:
                    break
                else:
                    time.sleep(3)
            
            #启动新进程开始抓取本子
            task = downloadTask("download", book, record, save_path)
            task.start()
            task_list.append(task)
            print("++++++New Task Started:",task)
            #print(task_list)
    
    #退出处理
    for i in task_list:
        i.terminate()

    print("Program Exited")