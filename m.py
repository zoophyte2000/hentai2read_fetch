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
import shutil
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
        current_list = self.getData()

        if data in current_list:
            pass
        else:
            self.lock.acquire()
            f = open(self.file, 'a+', encoding='utf-8')
            f.write(data + "\n")
            f.close()
            self.lock.release()

class Book(object):
    def __init__(self):
        self.title = ""
        self.entry_url = ""
        self.chapter_urls = []
        self.download_urls = {}


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
        options.add_experimental_option('excludeSwitches',['enable-logging'])
        self.driver = webdriver.Chrome(service=service, options=options)
        self.wait = WebDriverWait(self.driver, 10)

        try:
            ret = self.downloadBook()
        except:
            pass
        finally:
            self.close()
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
        rets = soup.find_all(name='a', attrs={'class': 'pull-left font-w600'})

        try:
            for ret in rets:
                if self.book.entry_url in ret['href']:
                    self.book.chapter_urls.append(ret['href'])
        except Exception as e:
            print(e)
            return result
        
        if len(self.book.chapter_urls) == 0:
            print("No Chapter ID found!")
            return result
        
        #获取所有页面下载地址
        for chapter_url in self.book.chapter_urls:
            ps = self.getPageText(chapter_url)
            soup = BeautifulSoup(ps, 'lxml')
            rets = soup.find_all(name='script')

            #参考https://janda.merahputih.moe/#api-hentai2read
            base_pic_url = "https://cdn-ngocok-static.sinxdr.workers.dev/hentai"

            download_urls = [] 

            for ret in rets:
                if "var gData" in str(ret):
                    #print(ret)
                    gDataRegex = re.compile(r'.*({.*})', re.DOTALL)
                    jstr_origin = gDataRegex.findall(str(ret))[0]
                    jstr = jstr_origin.replace("\'", "\"")
                    #print(jstr)
                    js = json.loads(jstr)
                    for i in js["images"]:
                        download_urls.append(base_pic_url + i)

                    self.book.download_urls[chapter_url] = download_urls
                    #print(self.book.download_urls)
                    break
        
        if len(self.book.download_urls) > 0:
            #创建保存目录
            chapter1 = string_split(self.book.chapter_urls[0], "/")[-1]
            sp_base = self.save_path + self.book.title + '/'

            if len(self.book.chapter_urls) > 1: #多个Chapter
                shutil.rmtree(sp_base)

            #一些补救代码，之后无用
            if os.path.exists(sp_base):
                if os.path.exists(sp_base + chapter1) == False: 
                    make_dir(sp_base + chapter1)
                    for dirpath, dirnames, filenames in os.walk(sp_base):
                        for filename in filenames:
                            shutil.move(os.path.join(dirpath, filename), sp_base + chapter1)


            for chapter_url in self.book.chapter_urls:
                chapter = string_split(chapter_url, "/")[-1]
                if os.path.exists(sp_base + chapter) == False:
                    make_dir(sp_base + chapter + '/')
                
                for pic_download_url in self.book.download_urls[chapter_url]:
                    #print("pic_download_url=", pic_download_url)
                    self.downloadPagePic(pic_download_url, sp_base + chapter + '/')

                self.record.appendData(self.book.title)
                result = True

        return result

    def retriedRequest(self, url:str):
        result = None
        count = 0

        while True:
            try:
                result = requests.get(url = url)
                break

            except:
                if count > 3:
                    print("########CAN NOT GET:", self.book.chapter_url)
                    return result
                else:
                    count = count + 1
                    time.sleep(3)

        return result


    def downloadPagePic(self, url:str, path:str, timeout:int = 10):
        result = False
        url_split = string_split(url, "/")

        if len(url_split) == 0:
            return

        fn = url_split[-1]
        fs = path + fn
        self.lock.acquire()

        try:
            if ((os.path.exists(fs) == False) and (os.path.exists(fs[0:-3]+"png") == False)):
                print(fn)
                print(fs)
                ret = self.retriedRequest(url)
                with open(fs, 'wb') as f:
                    f.write(ret.content)

            if os.path.getsize(fs) < 10*1024:
                #print("########### NEED PNG FIle:", fs)
                os.remove(fs)
                # url = url[0:-3] + "png"
                # fs = fs[0:-3] + "png"
                ret = self.retriedRequest(url)

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
        options.add_experimental_option('excludeSwitches',['enable-logging'])
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
    MAX_TASK_LIMIT = 6  #多少个并行抓取进程
    MAX_PAGE_LIMIT = 105 #page_base的最大页面
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
                #continue
            
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

    #等待最后task_list中的任务结束
    while True:
        if is_exit == True:
            break

        task_list = [x for x in task_list if x.is_alive() == True]
        if len(task_list) != 0:
            time.sleep(3)
        else:
            break

    
    #退出处理
    for i in task_list:
        i.terminate()

    app.close()

    print("Program Exited")