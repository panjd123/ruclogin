from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.common.exceptions import StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from time import sleep
import datetime
import ddddocr
import base64
import os
import os.path as osp
import configparser
import requests
import pickle
from timeit import default_timer as timer
import docopt

ROOT = os.path.dirname(os.path.abspath(__file__))
INI_PATH = osp.join(ROOT, "config.ini")
CACHE_PATH = osp.join(ROOT, "cache.pkl")

loginer_instance = None
config = configparser.ConfigParser()


class RUC_LOGIN:
    driver: webdriver.Chrome
    usernameInput: WebElement
    passwordInput: WebElement
    codeInput: WebElement
    codeImg: WebElement
    loginButton: WebElement
    login_alter: WebElement
    enableLogging: bool
    username: str
    password: str
    ocr: ddddocr.DdddOcr
    date: str
    lst_img: bytes
    lst_status: tuple

    def __init__(self) -> None:
        self.date = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        self.ocr = ddddocr.DdddOcr()
        global config
        config.read(INI_PATH, encoding="utf-8")
        browser = config["base"]["browser"]

        if browser == "Chrome":
            chrome_options = webdriver.ChromeOptions()
            chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("start-maximized")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument("--disable-logging")
            chrome_options.add_argument("--silent")
            chrome_options.add_experimental_option(
                "excludeSwitches", ["enable-logging"]
            )
            self.driver = webdriver.Chrome(
                options=chrome_options,
                service=ChromeService(ChromeDriverManager().install()),
            )
        elif browser == "Edge":
            edge_options = webdriver.EdgeOptions()
            edge_options.add_argument("--headless=new")
            edge_options.add_argument("start-maximized")
            edge_options.add_argument("--disable-gpu")
            edge_options.add_argument("--no-sandbox")
            edge_options.add_argument("--disable-dev-shm-usage")
            edge_options.add_argument("--disable-extensions")
            edge_options.add_argument("--disable-infobars")
            edge_options.add_argument("--disable-logging")
            edge_options.add_argument("--silent")
            edge_options.add_experimental_option("excludeSwitches", ["enable-logging"])
            self.driver = webdriver.Edge(
                options=edge_options,
                service=EdgeService(EdgeChromiumDriverManager().install()),
            )
        else:
            raise ValueError("browser must be Chrome or Edge")

    def initial_login(self):
        global config
        config.read(INI_PATH, encoding="utf-8")
        self.username = config["base"]["username"]
        self.password = config["base"]["password"]
        self.enableLogging = config["base"].getboolean("enableLogging")
        self.driver.get("https://v.ruc.edu.cn/auth/login")
        self.usernameInput = self.driver.find_element(
            By.XPATH, "/html/body/div/form/div[3]/input"
        )
        self.passwordInput = self.driver.find_element(
            By.XPATH, "/html/body/div/form/div[4]/input"
        )
        self.codeInput = self.driver.find_element(
            By.XPATH, "/html/body/div/form/div[6]/input"
        )
        self.codeImg = self.driver.find_element(
            By.XPATH, "/html/body/div/form/div[7]/img"
        )
        self.loginButton = self.driver.find_element(
            By.XPATH, "/html/body/div/form/div[12]/button"
        )
        self.login_alter = self.driver.find_element(
            By.XPATH, "/html/body/div/form/div[11]"
        )
        self.lst_img = None
        self.lst_status = self.current_status()

    def get_img(self):
        codeImgSrc = self.codeImg.get_attribute("src")
        img = codeImgSrc.split(",")[1]
        img = base64.b64decode(img)
        return img

    def current_status(self):
        try:
            return ("logging in", self.login_alter.text, self.get_img())
        except StaleElementReferenceException:  # 找不到元素，说明已经登录成功
            return ("success", None, None)

    def wait_for_new_img(self):
        waiting_time = 0
        img = self.get_img()
        while img == self.lst_img:
            sleep(0.1)
            waiting_time += 0.1
            if waiting_time > 10:
                raise TimeoutError("CodeImg refresh failed")
            img = self.get_img()
        self.lst_img = img
        return img

    def do_ocr(self):
        def is_valid_result(ocrRes: str):
            if len(ocrRes) != 4:
                return False
            for c in ocrRes:
                if not (
                    ord("a") <= ord(c) <= ord("z") or ord("A") <= ord(c) <= ord("Z")
                ):
                    return False
            return True

        for _ in range(100):
            img = self.wait_for_new_img()
            assert img == self.get_img()
            ocrRes = self.ocr.classification(img)
            if not is_valid_result(ocrRes):
                self.codeImg.click()
            else:
                return ocrRes, img
        raise TimeoutError("OCR failed")

    def try_login(self):
        self.usernameInput.clear()
        self.passwordInput.clear()
        self.codeInput.clear()
        self.usernameInput.send_keys(self.username)
        self.passwordInput.send_keys(self.password)
        ocrRes, img = self.do_ocr()
        self.codeInput.send_keys(ocrRes)

        self.loginButton.click()
        while (
            self.current_status() == self.lst_status
            and self.current_status()[0] == "logging in"
        ):
            sleep(0.1)
        self.lst_status = self.current_status()
        status_msg = self.lst_status[1]
        if status_msg == "验证码不正确或已失效,请重试！":
            return False
        elif status_msg == "用户不存在！" or status_msg == "用户名或密码不正确,请重试！":
            print("username: {}, password: {}".format(self.username, self.password))
            raise ValueError(status_msg)
        return True

    def get_cookies(self):
        raw_cookies = self.driver.get_cookies()
        cookies = {cookie["name"]: cookie["value"] for cookie in raw_cookies}
        try:
            cookies.pop("is_simple")
            cookies.pop("session")
        except:
            print(cookies)
        return cookies

    def login(self):
        for _ in range(10):
            success = self.try_login()
            if success:
                return
        raise TimeoutError("Login failed")

    def login_and_get_cookies(self):
        self.initial_login()
        self.login()
        return self.get_cookies()


def get_cookies(cache=True) -> dict:
    """Get cookies from cache or selenium login.

    Args:
        cache (bool, optional): Force regain when set to False. Defaults to True.

    Returns:
        dict: Like {'tiup_uid': '6112329b90f4d162e19b83c9', 'access_token': 'rhMSVympSBON2Xr8yAdhnQ'}
    """
    global loginer_instance
    if cache:
        if osp.exists(CACHE_PATH):
            cookies = pickle.load(open(CACHE_PATH, "rb"))
            if check_cookies(cookies):
                return cookies
    if loginer_instance is None:
        loginer_instance = RUC_LOGIN()
    cookies = loginer_instance.login_and_get_cookies()
    pickle.dump(cookies, open(CACHE_PATH, "wb"))
    return cookies


def check_cookies(cookies) -> bool:
    """Check if cookies are valid.

    Args:
        cookies (dict): Like {'tiup_uid': '6112329b90f4d162e19b83c9', 'access_token': 'rhMSVympSBON2Xr8yAdhnQ'}

    Returns:
        bool: True if valid, False if invalid(or expired).
    """
    response = requests.get("https://v.ruc.edu.cn/me#/", cookies=cookies)
    try:
        begin = response.text.find("<title>")
        end = response.text.find("</title>")
        title = response.text[begin + 7 : end].replace("\n", "").replace("\r", "")
        if title == "登录 - 中国人民大学":
            return False
        elif title == "微人大":
            return True
        else:
            assert False
    except:
        return False


def update_username_and_password(username: str, password: str):
    """Update username and password, save to disk.

    Args:
        username (str): username
        password (str): password
    """
    global config
    config.read(INI_PATH, encoding="utf-8")
    if username:
        config["base"]["username"] = username
    if password:
        config["base"]["password"] = password
    with open(INI_PATH, "w", encoding="utf-8") as f:
        config.write(f)


def get_username_and_password():
    """Get username and password, read from disk.

    Returns:
        (str, str): (username, password)
    """
    global config
    config.read(INI_PATH, encoding="utf-8")
    return config["base"]["username"], config["base"]["password"]


def update_browser(browser):
    global config
    config.read(INI_PATH, encoding="utf-8")
    if browser:
        config["base"]["browser"] = browser
    with open(INI_PATH, "w", encoding="utf-8") as f:
        config.write(f)


def main():
    usage = r"""Usage:
    ruclogin [--browser=<browser>] [--username=<username>] [--password=<password>]
    
Options:
    --browser=<browser>     browser(Chrome/Edge)
    --username=<username>   username
    --password=<password>   password
    """
    args = docopt.docopt(usage)
    browser = args["--browser"] or input("browser(Chrome/Edge), type enter to skip: ")
    if browser not in ["Chrome", "Edge", ""]:
        raise ValueError("browser must be Chrome or Edge")
    username = args["--username"] or input("username, type enter to skip: ")
    password = args["--password"] or input("password, type enter to skip: ")
    update_username_and_password(username, password)
    update_browser(browser)
    print("Config {} updated:".format(INI_PATH))
    print(
        "Username: {}\nPassword: {}\nBrowser: {}".format(
            config["base"]["username"],
            config["base"]["password"],
            config["base"]["browser"],
        )
    )


if __name__ == "__main__":
    main()
