# from selenium import webdriver
import seleniumwire.webdriver as webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.common.exceptions import StaleElementReferenceException
from requests.exceptions import ConnectionError
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
import docopt
import onnxruntime
from getpass import getpass
from timeit import default_timer as timer

PASSWORD_INPUT = True

ROOT = os.path.dirname(os.path.abspath(__file__))
INI_PATH = osp.join(ROOT, "config.ini")
JW_COOKIES_PATH = osp.join(ROOT, "jw_cookies.pkl")
V_COOKIES_PATH = osp.join(ROOT, "v_cookies.pkl")

loginer_instance = None
config = configparser.ConfigParser()

onnxruntime.set_default_logger_severity(3)


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
        driver_path = config["base"]["driver"]

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
                self.driver = webdriver.Chrome(
                    options=options,
                    service=ChromeService(ChromeDriverManager().install()),
                )
            except ConnectionError as e:
                if not osp.exists(driver_path):
                    raise e
                self.driver = webdriver.Chrome(
                    options=options,
                    service=ChromeService(executable_path=driver_path),
                )
        elif browser == "Edge":
            options = get_options(webdriver.EdgeOptions())
            try:
                self.driver = webdriver.Edge(
                    options=options,
                    service=EdgeService(EdgeChromiumDriverManager().install()),
                )
            except ConnectionError as e:
                if not osp.exists(driver_path):
                    raise e
                self.driver = webdriver.Edge(
                    options=options,
                    service=EdgeService(executable_path=driver_path),
                )
        else:
            raise ValueError("browser must be Chrome or Edge")

    def initial_login(self, domain: str, username="", password=""):
        """
        Update username and password, and get the elements in the login page.
        """
        global config
        config.read(INI_PATH, encoding="utf-8")
        self.username = username or config["base"]["username"]
        self.password = password or config["base"]["password"]
        self.enableLogging = config["base"].getboolean("enableLogging")
        if domain.startswith("v"):
            url = r"https://v.ruc.edu.cn/auth/login"
        else:
            url = r"https://v.ruc.edu.cn/auth/login?&proxy=true&redirect_uri=https%3A%2F%2Fv.ruc.edu.cn%2Foauth2%2Fauthorize%3Fresponse_type%3Dcode%26scope%3Dall%26state%3Dyourstate%26client_id%3D5d25ae5b90f4d14aa601ede8.ruc%26redirect_uri%3Dhttps%3A%2F%2Fjw.ruc.edu.cn%2FsecService%2Foauthlogin"
        self.driver.get(url)
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
        if status_msg == "验证码不正确或已失效,请重试！":
            return False
        elif status_msg == "用户不存在！":
            raise ValueError(
                f"用户不存在：\nusername: {self.username}\tpassword：see {INI_PATH}"
            )
        elif status_msg == "用户名或密码不正确,请重试！":
            raise ValueError(
                f"用户名或密码不正确：\nusername: {self.username}\tpassword：see {INI_PATH}"
            )
        elif status_msg:
            raise ValueError("Login failed, status msg from website: " + status_msg)
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
                        cookies.update(
                            {
                                cookie.split("=")[0]: cookie.split("=")[1].split(";")[0]
                                for cookie in cookie_header.split(", ")
                            }
                        )
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
        print(f"retry {retry}:", e)
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
                "https://v.ruc.edu.cn/v3/api/me/roles", cookies=cookies
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
            with open(JW_COOKIES_PATH, "w"):
                pass
        if osp.exists(V_COOKIES_PATH):
            with open(V_COOKIES_PATH, "w"):
                pass


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
    usage = r"""Usage:
    ruclogin [--username=<username>] [--password=<password>] [--browser=<browser>] [--driver=<driver_path>] [--reset] [--debug]
    
Options:
    --username=<username>   username
    --password=<password>   password
    --browser=<browser>     browser(Chrome/Edge)
    --driver=<driver_path>  driver_path
    --reset
    --debug
    """
    args = docopt.docopt(usage)
    if args["--reset"]:
        update_username_and_password("2021201212", "ABC12345")
        update_other(browser="Chrome", driver_path="D:/Other/driver/chromedriver.exe")
        config.read(INI_PATH, encoding="utf-8")
        print("Config {} updated:".format(INI_PATH))
        print(
            "\tUsername: {}\n\tPassword: {}\n\tBrowser: {}\n\tdriver_path: {}".format(
                config["base"]["username"],
                config["base"]["password"],
                config["base"]["browser"],
                config["base"]["driver"],
            )
        )
        print(f"The size of {V_COOKIES_PATH} is {osp.getsize(V_COOKIES_PATH)}")
        print(f"The size of {JW_COOKIES_PATH} is {osp.getsize(JW_COOKIES_PATH)}")
        return
    restart = True
    while restart:
        username = args["--username"] or input("username, type enter to skip: ")
        if PASSWORD_INPUT:
            password = args["--password"] or getpass("password, type enter to skip: ")
        else:
            password = args["--password"] or input("password, type enter to skip: ")
        browser = args["--browser"] or input(
            "browser(Chrome/Edge), type enter to skip: "
        )
        browser = browser.capitalize()
        if browser not in ["Chrome", "Edge", ""]:
            raise ValueError("browser must be Chrome or Edge")
        driver_path = args["--driver"] or input("driver_path, type enter to skip: ")
        update_username_and_password(username, password)
        update_other(browser, driver_path)
        print("\nConfig {} updated:".format(INI_PATH))
        print(
            "\tUsername: {}\n\tPassword: {}\n\tBrowser: {}\n\tdriver_path: {}".format(
                config["base"]["username"],
                "******" if PASSWORD_INPUT else config["base"]["password"],
                config["base"]["browser"],
                config["base"]["driver"],
            )
        )
        print("\n")
        isTest = input("Test login? (Y/n): ")
        if isTest.lower() in ["y", "yes", ""]:
            print("Testing, please be patient and wait...")
            try:
                init_tic = timer()
                driver_init(args["--debug"])
                init_toc = timer()
                v_get_tic = timer()
                v_cookies = get_cookies(domain="v", cache=False)
                v_get_toc = timer()
                v_check_tic = timer()
                v_msg = check_cookies(v_cookies, domain="v")
                if not v_msg:
                    print(v_cookies)
                    raise RuntimeError("v.ruc.edu.cn cookies are invalid")
                v_check_toc = timer()
                jw_get_tic = timer()
                jw_cookies = get_cookies(domain="jw", cache=False)
                jw_get_toc = timer()
                jw_check_tic = timer()
                jw_msg = check_cookies(jw_cookies, domain="jw")
                if not jw_msg:
                    print(jw_cookies)
                    raise RuntimeError("jw.ruc.edu.cn cookies are invalid")
                jw_check_toc = timer()
                print(v_msg, "from v.ruc.edu.cn")
                print(jw_msg, "from jw.ruc.edu.cn")
                print("driver init time: {:.3f}s".format(init_toc - init_tic))
                print(
                    "v.ruc.edu.cn get cookies time: {:.3f}s, check cookies time: {:.3f}s".format(
                        v_get_toc - v_get_tic, v_check_toc - v_check_tic
                    )
                )
                print(
                    "jw.ruc.edu.cn get cookies time: {:.3f}s, check cookies time: {:.3f}s".format(
                        jw_get_toc - jw_get_tic, jw_check_toc - jw_check_tic
                    )
                )
                break
            except Exception as e:
                print(e)
                restart = input("Login failed, restart? (Y/n):")
                restart = restart == "" or restart.lower()[0] == "y"


if __name__ == "__main__":
    main()
    # domain = "v"
    # cookies = get_cookies(cache=False, domain=domain)
    # print(cookies)
    # success = check_cookies(cookies, domain=domain)
    # print(success)
