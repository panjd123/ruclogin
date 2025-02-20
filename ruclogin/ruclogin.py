# from selenium import webdriver
import base64
import configparser
import datetime
import os
import os.path as osp
import pickle
from getpass import getpass
from time import sleep
from timeit import default_timer as timer
import argparse
import logging

import ddddocr
import onnxruntime
import requests
import seleniumwire.webdriver as webdriver
from requests.exceptions import ConnectionError
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    StaleElementReferenceException,
)
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager

PASSWORD_INPUT = True

ROOT = os.path.dirname(os.path.abspath(__file__))
INI_PATH = osp.join(ROOT, "config.ini")
JW_COOKIES_PATH = osp.join(ROOT, "jw_cookies.pkl")
V_COOKIES_PATH = osp.join(ROOT, "v_cookies.pkl")

loginer_instance = None
config = configparser.ConfigParser()

onnxruntime.set_default_logger_severity(3)

PRIVATE_INFO = 15
logging.addLevelName(PRIVATE_INFO, "PRIVATE_INFO")


def private_info(self, message, *args, **kws):
    if self.isEnabledFor(PRIVATE_INFO):
        self._log(PRIVATE_INFO, message, args, **kws)


logging.Logger.private_info = private_info
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
console_hd = logging.StreamHandler()
console_hd.setLevel(logging.WARNING)
# console_hd.setFormatter(
#     logging.Formatter("%(asctime)s - %(levelname)s- %(module)s - %(message)s")
# )
console_hd.setFormatter(logging.Formatter("%(message)s"))
logger.addHandler(console_hd)


def gen_semester_codes():
    now_year = datetime.datetime.now().year
    codes = [
        f"{y-1}-{y}-{s}"
        for y in [now_year - 3, now_year - 2, now_year - 1, now_year]
        for s in [1, 2, 4]
    ]
    return ",".join(codes)


def semester2code(text="2023-2024学年春季学期"):
    y = text[:9]
    s = "春夏秋冬".index(text[11]) + 1
    return f"{y}-{s}"


def code2semester(code="2023-2024-1"):
    y = code[:9]
    s = int(code[10])
    return f"{y}学年{'春夏秋冬'[s-1]}季学期"


class RUC_LOGIN:
    """
    For developer:
    RUC_LOGIN works like this:
    1. __init__ function will initialize the webdriver, and read the config from the ini file.
    2. initial_login function will get the elements in the login page, like input, button, etc.
    3. get_img function will get the current image of the code.
    4. do_ocr function will try to do OCR for at most 100 times,
        it only returns when the result is looks like a valid code(4 letters),
        otherwise it will click the codeImg and try again.
    5. try_login function will use the do_ocr function to get the code, and then login.
        Return False if the code is wrong (failed to login), else return True (success to login).
    6. login function will try to login for at most 20 times, raise TimeoutError if failed too many times.
    7. after login, get_cookies function will get the cookies from the driver, and return it.

    The reason why we use do_ocr function is because the ocr's recognition accuracy is not high,
    and it often makes obvious mistakes, we can recognize the code in advance and manually refresh a code.
    """

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

    def __init__(self, debug=False) -> None:
        self.date = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        self.ocr = ddddocr.DdddOcr(show_ad=False)
        global config
        config.read(INI_PATH, encoding="utf-8")
        browser = config["base"]["browser"]

        def get_options(options):
            options.add_argument("start-maximized")
            if not debug:
                options.add_argument("--headless=new")
                options.add_argument("--disable-gpu")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_argument("--disable-extensions")
                options.add_argument("--disable-infobars")
                options.add_argument("--disable-logging")
                options.add_argument("--silent")
                options.add_argument("--log-level=3")
                options.add_experimental_option("detach", True)
                options.add_experimental_option("excludeSwitches", ["enable-logging"])
            return options

        if browser == "Chrome":
            options = get_options(webdriver.ChromeOptions())
            try:
                self.driver = webdriver.Chrome(options=options)
                logger.info("Using Chrome from PATH")
            except Exception as e1:
                try:
                    logger.info(f"Failed to find Chrome in the PATH: {e1}")
                    self.driver = webdriver.Chrome(
                        options=options,
                        service=ChromeService(ChromeDriverManager().install()),
                    )
                    logger.info("Using Chrome driver installed by webdriver_manager")
                except Exception as e2:
                    logger.info(
                        f"Failed to download Chrome driver automatically using webdriver_manager: {e2}"
                    )
                    driver_path = config["base"]["driver"]
                    if not osp.exists(driver_path):
                        logger.error(
                            f"Driver '{driver_path}' not found; attempts to locate Chrome in the PATH and download via webdriver_manager also failed"
                        )
                        raise RuntimeError(f"driver {driver_path} not found")
                    self.driver = webdriver.Chrome(
                        options=options,
                        service=ChromeService(executable_path=driver_path),
                    )
                    logger.info(f"Using Chrome driver from {driver_path}")
        elif browser == "Edge":
            options = get_options(webdriver.EdgeOptions())
            try:
                self.driver = webdriver.Edge(options=options)
                logger.info("Using Edge from PATH")
            except Exception as e1:
                try:
                    logger.info(f"Failed to find Edge in the PATH: {e1}")
                    self.driver = webdriver.Edge(
                        options=options,
                        service=EdgeService(EdgeChromiumDriverManager().install()),
                    )
                    logger.info("Using Edge driver installed by webdriver_manager")
                except Exception as e2:
                    logger.info(
                        f"Failed to download Edge driver automatically using webdriver_manager: {e2}"
                    )
                    driver_path = config["base"]["driver"]
                    if not osp.exists(driver_path):
                        logger.error(
                            f"Driver '{driver_path}' not found; attempts to locate Edge in the PATH and download via webdriver_manager also failed"
                        )
                        raise RuntimeError(f"driver {driver_path} not found")
                    self.driver = webdriver.Edge(
                        options=options,
                        service=EdgeService(executable_path=driver_path),
                    )
                    logger.info(f"Using Edge driver from {driver_path}")
        else:
            raise ValueError("browser must be Chrome or Edge")

        self.wait = WebDriverWait(self.driver, 10)

    def initial_login(self, domain: str, username="", password=""):
        """
        Update username and password, and get the elements in the login page.
        """
        global config
        # 使用 raw 配置读取器来避免 % 解析问题
        config.read(INI_PATH, encoding="utf-8")
        self.username = username or config.get("base", "username", raw=True)
        self.password = password or config.get("base", "password", raw=True)
        self.enableLogging = config["base"].getboolean("enableLogging")

        if domain.startswith("v"):
            url = r"https://v.ruc.edu.cn/auth/login"
        else:
            url = r"https://v.ruc.edu.cn/auth/login?&proxy=true&redirect_uri=https%3A%2F%2Fv.ruc.edu.cn%2Foauth2%2Fauthorize%3Fresponse_type%3Dcode%26scope%3Dall%26state%3Dyourstate%26client_id%3D5d25ae5b90f4d14aa601ede8.ruc%26redirect_uri%3Dhttps%3A%2F%2Fjw.ruc.edu.cn%2FsecService%2Foauthlogin"
        self.driver.get(url)

        def try_click(by, value):
            ele = self.wait.until(EC.element_to_be_clickable((by, value)))
            while True:
                try:
                    ele.click()
                except ElementClickInterceptedException:
                    self.driver.implicitly_wait(0.1)
                    continue
                break
            return ele

        # self.usernameInput = self.driver.find_element(
        #     By.XPATH, "/html/body/div/form/div[3]/input"
        # )
        self.usernameInput = try_click(By.XPATH, "/html/body/div/form/div[3]/input")
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
        )  # This element show the login failed reason, like "验证码不正确或已失效,请重试！"
        self.rememberMe = self.driver.find_element(
            By.XPATH, "/html/body/div/form/div[13]/span[1]/div"
        ).click()
        self.lst_img = None
        self.lst_status = self.current_status()

    def get_img(self):
        """
        Get the current image of the code.
        """
        codeImgSrc = self.codeImg.get_attribute("src")
        img = codeImgSrc.split(",")[1]
        img = base64.b64decode(img)
        return img

    def current_status(self):
        try:
            # 直接返回原始文本，不做任何格式化
            raw_text = self.login_alter.text
            if raw_text and "%" in raw_text:
                # 如果文本中包含%，进行特殊处理
                raw_text = raw_text.replace("%", "%%")
            return ("logging in", raw_text, self.get_img())
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
        """
        Try to do OCR for at most 100 times,
        it only returns when the result is looks like a valid code(4 letters).
        """

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
        """
        Use the do_ocr function to get the code, and then login.
        Return False if the code is wrong (failed to login), else return True (success to login).
        """
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

        # 处理状态消息时避免格式化问题
        if status_msg and "验证码不正确" in status_msg:
            return False
        elif status_msg and "用户不存在" in status_msg:
            raise ValueError(
                "用户不存在：\nusername: {}\tpassword：see {}".format(
                    self.username, INI_PATH
                )
            )
        elif status_msg and "用户名或密码不正确" in status_msg:
            raise ValueError(
                "用户名或密码不正确：\nusername: {}\tpassword：see {}".format(
                    self.username, INI_PATH
                )
            )
        elif status_msg:
            # 避免直接使用可能包含%的文本
            raise ValueError(
                "Login failed, raw status msg: {}".format(repr(status_msg))
            )
        return True

    def get_cookies(self, domain="v"):
        if domain.startswith("v"):
            raw_cookies = self.driver.get_cookies()
            cookies = {cookie["name"]: cookie["value"] for cookie in raw_cookies}
            return cookies
        elif domain.startswith("jw"):
            [
                self.driver.wait_for_request(
                    url,
                    timeout=10,
                )
                for url in [
                    "/Njw2017/index.html*",
                    "/secService/oauthlogin*",
                ]
            ]
            cookies = {}
            for request in self.driver.requests:
                if request.response:
                    cookie_header = request.response.headers["Set-Cookie"]
                    if cookie_header:
                        name, value = cookie_header.split(";")[0].split("=", 1)
                        cookies.update({name: value})
            return cookies

    def login(self):
        """
        Try to login for at most 20 times, raise TimeoutError if failed too many times.
        """
        for _ in range(20):
            success = self.try_login()
            if success:
                return
        raise TimeoutError("Login failed, try too many times")

    def __del__(self):
        if hasattr(self, "driver"):
            self.driver.quit()
        return


def driver_init(debug=False):
    global loginer_instance
    if loginer_instance is None:
        loginer_instance = RUC_LOGIN(debug=debug)


def get_cookies(cache=True, domain="v", retry=3, username="", password="") -> dict:
    """Get cookies from cache or selenium login.

    Args:
        cache (bool, optional): Force regain when set to False. Defaults to True.

        domain (str, optional): "v", "jw", "v.ruc.edu.cn", "jw.ruc.edu.cn". Defaults to "v".

        username (str, optional)

        password (str, optional)

    Returns:
        dict: Like {'tiup_uid': '6112329b90f4d162e19b83c9', 'access_token': 'rhMSVympSBON2Xr8yAdhnQ'}
    """
    global loginer_instance
    domain = domain.split(".")[0]
    cache_path = osp.join(ROOT, f"{domain}_cookies.pkl")
    if cache:
        if osp.exists(cache_path):
            try:
                cookies = pickle.load(open(cache_path, "rb"))
                if check_cookies(cookies, domain):
                    return cookies
            except EOFError as e:
                pass
    driver_init()
    try:
        loginer_instance.initial_login(domain, username, password)
        loginer_instance.login()
        cookies = loginer_instance.get_cookies(domain)
        if not cookies:
            raise RuntimeError("Login failed, cookies are empty, please try again")
    except RuntimeError as e:
        logger.warning(f"retry {retry}: {e}")
        if retry == 1:
            raise e
        else:
            get_cookies(cache=False, domain=domain, retry=retry - 1)
    pickle.dump(cookies, open(cache_path, "wb"))
    return cookies


def check_cookies(cookies, domain="v"):
    """Check if cookies are valid.

    Args:
        cookies (dict): Like {'tiup_uid': '6112329b90f4d162e19b83c9', 'access_token': 'rhMSVympSBON2Xr8yAdhnQ'}

        domain (str, optional): "v", "jw", "v.ruc.edu.cn", "jw.ruc.edu.cn". Defaults to "v".

    Returns:
        optional[str]: None if cookies are invalid, else a greeting message.
    """
    try:
        if domain.startswith("v"):
            response = requests.get(
                "https://v.ruc.edu.cn/v3/api/me/roles",
                cookies=cookies,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                },
            )
            role = response.json()["data"][-1]
            return f"你好, {role['departmentname']} {role['username']}"
        elif domain.startswith("jw"):
            response = requests.post(
                "https://jw.ruc.edu.cn/resService/jwxtpt/v1/xsd/cjgl_xsxdsq/professionalRankingQuery",
                params={
                    "resourceCode": "XSMH0527",
                    "apiCode": "jw.xsd.xsdInfo.controller.CjglKccjckController.professionalRankingQuery",
                },
                cookies={"SESSION": cookies["SESSION"]},
                headers={
                    "Accept": "application/json, text/plain, */*",
                    "TOKEN": cookies["token"],
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
                },
                json={"jczy013id": gen_semester_codes()},
            )
            d = response.json()["data"][0]
            return "你好，{} {}，你一共修了{}学分，{}门课，平均绩点{}，专业排名第{}名".format(
                d["ndzy_name"],
                d["xs_name"],
                d["sdxf"],
                d["countnum"],
                d["pjxfjd"],
                d["pm"],
            )
    except:
        return None


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
    if username or password:
        with open(INI_PATH, "w", encoding="utf-8") as f:
            config.write(f)
        if osp.exists(JW_COOKIES_PATH):
            os.remove(JW_COOKIES_PATH)
        if osp.exists(V_COOKIES_PATH):
            os.remove(V_COOKIES_PATH)


def get_username_and_password():
    """Get username and password, read from disk.

    Returns:
        (str, str): (username, password)
    """
    global config
    config.read(INI_PATH, encoding="utf-8")
    return config["base"]["username"], config["base"]["password"]


def update_other(browser=None, driver_path=None):
    global config
    config.read(INI_PATH, encoding="utf-8")
    if browser:
        config["base"]["browser"] = browser
    if driver_path:
        config["base"]["driver"] = driver_path
    with open(INI_PATH, "w", encoding="utf-8") as f:
        config.write(f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", type=str, default=None)
    parser.add_argument("--password", type=str, default=None)
    parser.add_argument("--browser", type=str, default=None)
    parser.add_argument("--driver", type=str, default=None)
    parser.add_argument("--reset", action="store_true")
    parser.add_argument("--debug", action="store_true")
    parser.add_argument("--no_interactive", action="store_true")
    parser.add_argument("--private", action="store_true")
    parser.add_argument("-V", action="store_true", help="Show paths.")
    args = parser.parse_args()
    if args.private:
        console_hd.setLevel(logging.INFO)
    else:
        console_hd.setLevel(PRIVATE_INFO)
    if args.V:
        logger.info(f"配置文件路径：{INI_PATH}")
        logger.info(f"教务系统 cookies 缓存路径：{JW_COOKIES_PATH}")
        logger.info(f"信息门户 cookies 缓存路径：{V_COOKIES_PATH}")
        return
    if args.reset:
        update_username_and_password("2021201212", "ABC12345")
        update_other(browser="Chrome", driver_path="D:/Other/driver/chromedriver.exe")
        config.read(INI_PATH, encoding="utf-8")
        logger.info("Config {} updated:".format(INI_PATH))
        logger.private_info(
            "\tusername: {}\n\tpassword: {}\n\tbrowser: {}\n\tdriver: {}".format(
                config["base"]["username"],
                config["base"]["password"],
                config["base"]["browser"],
                config["base"]["driver"],
            )
        )
        assert not osp.exists(JW_COOKIES_PATH)
        assert not osp.exists(V_COOKIES_PATH)
        return
    restart = True
    retry = 0
    while restart:
        username = args.username or input("username, type enter to skip: ")
        if PASSWORD_INPUT:
            password = args.password or getpass("password, type enter to skip: ")
        else:
            password = args.password or input("password, type enter to skip: ")
        browser = args.browser or input("browser(Chrome/Edge), type enter to skip: ")
        browser = browser.capitalize()
        if browser not in ["Chrome", "Edge", ""]:
            raise ValueError("browser must be Chrome or Edge")
        driver_path = args.driver or input("driver_path, type enter to skip: ")
        update_username_and_password(username, password)
        update_other(browser, driver_path)
        if args.no_interactive:
            isTest = "y"
        else:
            logger.info("Config {} updated:".format(INI_PATH))
            password_display = (
                repr(config["base"]["password"])[1:-1]  # 使用 repr() 并去掉引号
                if not PASSWORD_INPUT
                else "******"
            )
            logger.private_info(
                "\tusername: {}\n\tpassword: {}\n\tbrowser: {}\n\tdriver: {}".format(
                    config["base"]["username"],
                    password_display,
                    config["base"]["browser"],
                    config["base"]["driver"],
                )
            )
            isTest = input("\nTest login? (Y/n): ")
        if isTest.lower() in ["y", "yes", ""]:
            logger.info("Testing, please be patient and wait...")
            try:
                init_tic = timer()
                driver_init(args.debug)
                init_toc = timer()
                logger.info("Driver init time: {:.3f}s".format(init_toc - init_tic))
                v_get_tic = timer()
                v_cookies = get_cookies(domain="v", cache=False)
                v_get_toc = timer()
                logger.info(
                    "v.ruc.edu.cn get cookies time: {:.3f}s".format(
                        v_get_toc - v_get_tic
                    )
                )
                v_check_tic = timer()
                v_msg = check_cookies(v_cookies, domain="v")
                if not v_msg:
                    logger.error(f"v.ruc.edu.cn cookies are invalid")
                    logger.private_info(f"v_cookies: {v_cookies}")
                    raise RuntimeError("v.ruc.edu.cn cookies are invalid")
                v_check_toc = timer()
                logger.private_info(v_msg + " from v.ruc.edu.cn")
                logger.info(
                    "v.ruc.edu.cn check cookies time: {:.3f}s".format(
                        v_check_toc - v_check_tic
                    )
                )
                jw_get_tic = timer()
                jw_cookies = get_cookies(domain="jw", cache=False)
                jw_get_toc = timer()
                logger.info(
                    "jw.ruc.edu.cn get cookies time: {:.3f}s".format(
                        jw_get_toc - jw_get_tic
                    )
                )
                jw_check_tic = timer()
                jw_msg = check_cookies(jw_cookies, domain="jw")
                if not jw_msg:
                    logger.error(f"jw.ruc.edu.cn cookies are invalid: {jw_cookies}")
                    logger.private_info(f"jw_cookies: {jw_cookies}")
                    raise RuntimeError("jw.ruc.edu.cn cookies are invalid")
                jw_check_toc = timer()
                logger.private_info(jw_msg + " from jw.ruc.edu.cn")
                logger.info(
                    "jw.ruc.edu.cn check cookies time: {:.3f}s".format(
                        jw_check_toc - jw_check_tic
                    )
                )
                break
            except Exception as e:
                logger.error(e)
                if args.no_interactive:
                    retry += 1
                    logger.info(f"retry {retry} times")
                    if retry == 5:
                        raise e
                else:
                    restart = input("Login failed, restart? (Y/n/r(raise exception)):")
                    if len(restart) > 0 and restart.lower()[0] == "r":
                        raise e
                    restart = restart == "" or restart.lower()[0] == "y"


if __name__ == "__main__":
    main()
    # v_cookies = get_cookies(cache=False, domain="v")
    # print(v_cookies)
    # v_success = check_cookies(v_cookies, domain="v")
    # print(v_success)

    # jw_cookies = get_cookies(cache=False, domain="jw")
    # print(jw_cookies)
    # jw_success = check_cookies(jw_cookies, domain="jw")
    # print(jw_success)
