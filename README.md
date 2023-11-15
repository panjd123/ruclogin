# ruclogin

ruclogin is a package for obtaining and checking v.ruc.edu.cn (and jw.ruc.edu.cn) **cookies** using selenium (headless) and requests.

ruclogin 可以帮助你快速地获取和检查 v.ruc.edu.cn (和 jw.ruc.edu.cn) 的 cookies，使用 selenium 和 requests。

## Simple Example

```python
import ruclogin
ruclogin.update_username_and_password("2021201212", "ABC12345")
cookies = ruclogin.get_cookies(domain="v.ruc.edu.cn")
# {'tiup_uid': '6112329b90f4d162e19b83c9', 'session': '7a0b09dc5f5c4587aae0511247ae276d.834554d714de4c19b6ca1ec111ab3514', 'access_token': '1Jf8zOE7S5SYHYS3x5nNHA', 'is_simple': '1'}
```

## Get Started

### 0. Install ruclogin

```bash
git clone https://github.com/panjd123/ruclogin.git
cd ruclogin
pip install .
```

### 1. Install Chrome or Edge

- [Chrome](https://www.google.cn/chrome/)
- [Edge](https://www.microsoft.com/zh-cn/edge)

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
browser(Chrome/Edge), type enter to skip: Chrome
username, type enter to skip: 2021201212
password, type enter to skip: 
Config D:\Program\anaconda3\Lib\site-packages\ruclogin\config.ini updated:
Username: 2021201212
Password: ABC12345
Browser: Chrome
```

### 3. Get your cookies

```python
from ruclogin import *

# you can also update your username and password like this:
update_username_and_password("2021201212", "ABC12345")  # save in disk
print(get_username_and_password())  # ("2021201212", "ABC12345")

cookies = get_cookies(cache=False)  # regain cookies, login in using selenium, save in disk
print(cookies)                      # {'tiup_uid': '6112329b90f4d162e19b83c9', 'session': '7a0b09dc5f5c4587aae0511247ae276d.834554d714de4c19b6ca1ec111ab3514', 'access_token': '1Jf8zOE7S5SYHYS3x5nNHA', 'is_simple': '1'}
success = check_cookies(cookies)    # check cookies using requests
print(success)                      # True
cookies = get_cookies()             # cache=True, it will use the cookies obtained last time, check it first, if it fails, regain it
```

You only need to update your username and password once, and then you can get cookies at any time.

## Update

#### 0.2 Update

You can get jw.ruc.edu.cn cookies now.

```python
from ruclogin import *
cookies = get_cookies(domain="jw") # or get_cookies(domain="jw.ruc.edu.cn")
print(check_cookies(cookies, domain="jw")) # True
```

