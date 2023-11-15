# ruclogin

ruclogin is a package for obtaining and checking [v.ruc.edu.cn](v.ruc.edu.cn) (and [jw.ruc.edu.cn](jw.ruc.edu.cn)) **cookies** using selenium (headless) and requests.

ruclogin 可以帮助你快速地获取和检查 [v.ruc.edu.cn](v.ruc.edu.cn) (and [jw.ruc.edu.cn](jw.ruc.edu.cn)) 的 cookies，使用 selenium 和 requests。可能的用途包括抢课等。

[PyPI](https://pypi.org/project/ruclogin/) | [GitHub](https:://github.com/panjd123/ruclogin)

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

Now you can simply install ruclogin using pip.

```bash
pip install ruclogin
```

If you are worried about security issues, you can also install ruclogin from source code.

如果你担心安全问题，你也可以从源码安装 ruclogin。

```bash
git clone https://github.com/panjd123/ruclogin.git
cd ruclogin
pip install .
```

### 1. Install Chrome, Edge or Chromium

- [Chrome](https://www.google.cn/chrome/)
- [Edge](https://www.microsoft.com/zh-cn/edge)
- [Chromium](https://chromium.woolyss.com/download/zh/)

### 2. Set your username, password and preferred browser in terminal

```bash
ruclogin --username 2021201212 --password ABC12345 --browser Chrome
```

or just

```bash
ruclogin
```

and then type your username, password and preferred browser in terminal.

```
(base) PS D:\Code\campus\ruclogin> ruclogin
browser(Chrome/Edge/Chormium), type enter to skip: Chrome
username, type enter to skip: 2021201212
password, type enter to skip: 

Config D:\Program\anaconda3\Lib\site-packages\ruclogin\config.ini updated:
    Username: 2021201212
    Password: ABC12345
    Browser: Chrome

Test login? (Y/n):

你好, 信息学院 xxx from v.ruc.edu.cn
你这学期的课有：并行与分布式计算 计算机系统实现Ⅰ 后人类时代的全球影像 机器学习与计算智能Ⅰ 数据库系统概论荣誉课程 迁移学习 科学技术哲学 from jw.ruc.edu.cn
```

### 3. Get your cookies

```python
from ruclogin import *

# you can also update your username and password like this:
update_username_and_password("2021201212", "ABC12345")      # save in disk
print(get_username_and_password())                          # ("2021201212", "ABC12345")

cookies = get_cookies(cache=False, domain="v")          # regain cookies, login in using selenium, save in disk
print(cookies)                                          # {'tiup_uid': '6112329b90f4d162e19b83c9', 'session': '7a0b09dc5f5c4587aae0511247ae276d.834554d714de4c19b6ca1ec111ab3514', 'access_token': '1Jf8zOE7S5SYHYS3x5nNHA', 'is_simple': '1'}
success = check_cookies(cookies, domain="v")            # check cookies using requests
if success:
    print(success)                                      # 你好, xx学院 xxx from v.ruc.edu.cn                      
cookies = get_cookies()                                 # cache=True, it will use the cookies obtained last time, check it first, if it fails, regain it
```

You only need to update your username and password once, and then you can get cookies at any time.

无论用什么方式设置用户名和密码，你只需要设置一次。

## Update

#### 0.2 Update

You can get jw.ruc.edu.cn cookies now.

```python
from ruclogin import *
cookies = get_cookies(domain="jw") # or get_cookies(domain="jw.ruc.edu.cn")
check_cookies(cookies, domain="jw")
```

#### 0.2.1 Update

提高 check_cookies 的鲁棒性。

#### 0.2.3 Update

修改了 check_cookies 的输出，现在会输出所用测试请求的结果例如：“你这学期的课有：并行与分布式计算 计算机系统实现Ⅰ 后人类时代的全球影像 机器学习与计算智能Ⅰ 数据库系统概论荣誉课程 迁移学习 科学技术哲学”，似乎更有趣一点。