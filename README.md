# ruclogin

[![PyPI Downloads](https://img.shields.io/pypi/dm/ruclogin.svg?label=PyPI%20downloads)](
https://pypi.org/project/ruclogin/) [![GitHub Repo stars](https://img.shields.io/github/stars/panjd123/ruclogin?label=Github%20stars)](https://github.com/panjd123/ruclogin)

ruclogin 可以帮助你快速地获取和检查 [v.ruc.edu.cn](v.ruc.edu.cn) (and [jw.ruc.edu.cn](jw.ruc.edu.cn)) 的 cookies，使用 selenium 和 requests。可能的用途包括爬虫，抢课等。

## Simple Example

```python
import ruclogin
ruclogin.update_username_and_password("2021201212", "ABC12345")
cookies = ruclogin.get_cookies(domain="v.ruc.edu.cn") # you can also use domain="jw.ruc.edu.cn"
cookies
# {'tiup_uid': '6112329b90f4d162e19b83c9', 'session': '7a0b09dc5f5c4587aae0511247ae276d.834554d714de4c19b6ca1ec111ab3514', 'access_token': '1Jf8zOE7S5SYHYS3x5nNHA', 'is_simple': '1'}
```

## Get Started

### 0. Install ruclogin

```bash
pip install ruclogin
```

### 1. Install Chrome or Edge

- [Chrome](https://www.google.cn/chrome/)
- [Edge](https://www.microsoft.com/zh-cn/edge)

### 2. Set your username, password and preferred browser in terminal

```bash
ruclogin --username 2021201212 --password ABC12345 --browser Chrome --driver ""
```

或者使用交互式命令行

```bash
ruclogin
```

像这样，请注意，密码的输入不带回显（即不显示你输入的内容），你只需要直接输入，然后回车。

```
(base) PS D:\Code\ruclogin> ruclogin     
username, type enter to skip: 2021201212
password, type enter to skip: 
browser(Chrome/Edge), type enter to skip:
driver_path, type enter to skip:

Config D:\Program\anaconda3\Lib\site-packages\ruclogin\config.ini updated:
        Username: 2021201212
        Password: ******
        Browser: Chrome
        driver_path: D:/Other/driver/chromedriver.exe


Test login? (Y/n):
你好, 信息学院 xxx from v.ruc.edu.cn
你好，xxx 图灵实验班（信息学拔尖人才实验班），你一共修了123学分，48门课，平均绩点3.9，专业排名第2名 from jw.ruc.edu.cn
driver init time: 4.749s
v.ruc.edu.cn get cookies time: 1.587s, check cookies time: 0.348s
jw.ruc.edu.cn get cookies time: 1.925s, check cookies time: 0.395s
```

### 3. Get your cookies

```python
from ruclogin import *

# you can also update your username and password like this:
# update_username_and_password("2021201212", "ABC12345")      # will save in disk
# print(get_username_and_password())                          # ("2021201212", "ABC12345")

cookies = get_cookies(cache=False, domain="v")          # regain cookies, login in using selenium, save in disk
print(cookies)                                          # {'tiup_uid': '6112329b90f4d162e19b83c9', 'session': '7a0b09dc5f5c4587aae0511247ae276d.834554d714de4c19b6ca1ec111ab3514', 'access_token': '1Jf8zOE7S5SYHYS3x5nNHA', 'is_simple': '1'}
success = check_cookies(cookies, domain="v")            # check cookies using requests
if success:
    print(success)                                      # 你好, xx学院 xxx from v.ruc.edu.cn                      
cookies = get_cookies()                                 # cache=True, it will use the cookies obtained last time, check it first, if it fails, regain it
```

无论用什么方式设置用户名和密码，你只需要设置一次。

## Remind

拥有 cookies 相当于拥有微人大的完全访问权限，请不要和任何人分享。

执行 `ruclogin --reset` 可以将所有信息初始化（包括配置文件内保存的用户名密码，以及缓存的 cookies）。

## Q&A

Q: 我遇到报错 `Could not reach host. Are you offline?`

A: 自动获取浏览器驱动需要访问谷歌，你有两个解决方案

1. 开启网络代理
2. 手动包管理，即将浏览器的驱动手动下载到你的主机上，然后指定路径 `ruclogin --driver D:/Other/driver/chromedriver.exe`
   - [官方 ChromeDriver，需要科学上网](https://googlechromelabs.github.io/chrome-for-testing/)
   - [淘宝镜像 ChromeDriver](https://registry.npmmirror.com/binary.html?path=chrome-for-testing/)
   - [官方 EdgeDriver，国内能访问](https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver)

目前脚本的处理方法是，当能访问谷歌时优先使用自动下载的驱动，否则尝试使用手动指定的驱动。

Q: 控制台输出 DevTools listening on ws://..... ?

A: 这个输出关不掉，似乎是最新版 ChromeDriver 的一个问题，目前没有解决方案，不影响用，但是会有烦人的提示。

Q: 我遇到了其他报错。

A: 运行 `ruclogin --debug` 可以显示浏览器的操作过程，这可能有助于你发现问题。如果你是开发者，欢迎提交 pr 修复。

## Update

### 0.2.12

增加了 `--debug` 参数，可以显示浏览器的操作过程。

### 0.2.11

适配最新教务网站。

### 0.2.10

修改了密码的输入方式，现在不回显（即非明文输入）。

增加了 `--reset` 参数用于清空隐私数据。

因为精力所限，删除对 Chromium 的支持。

### 0.2.9

更干净的包卸载，支持临时指定 username 和 password（以方便多用户）。

### 0.2.8

随着 ddddocr 的更新，Pillow 的旧版本要求现在被删去。

### 0.2.7

修复部分 bug，通过了服务器运行。

### 0.2.6

细化了报错提示，更容易检查。 

再次优化了 check_cookies 的输出以适应学期变化。

ruclogin test 现在还会输出耗时。

集成了 `semester2code` 和 `code2semester` 两个函数，用于学期和学期代码之间转换。

### 0.2.5

支持了手动管理浏览器驱动。

删去了 ruclogin test 时请求用户输入前的额外换行。

### 0.2.3

修改了 check_cookies 的输出，现在会输出所用测试请求的结果例如：“你这学期的课有：并行与分布式计算 计算机系统实现Ⅰ 后人类时代的全球影像 机器学习与计算智能Ⅰ 数据库系统概论荣誉课程 迁移学习 科学技术哲学”，失败返回 None。

### 0.2.1

提高 check_cookies 的鲁棒性。

### 0.2

新增 jw.ruc.edu.cn cookies 支持。

```python
from ruclogin import *
cookies = get_cookies(domain="jw") # or get_cookies(domain="jw.ruc.edu.cn")
check_cookies(cookies, domain="jw")
```
