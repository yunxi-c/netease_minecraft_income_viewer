# -*- coding: utf-8 -*-
import calendar
import json
import os
import random
import time
from collections import OrderedDict
from datetime import datetime, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
from matplotlib import ticker
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from splinter import Browser

from accounts_config import ACCOUNTS

LOGIN_URL = "https://mcdev.webapp.163.com/#/login"
PE_ITEMS_URL = "https://mc-launcher.webapp.163.com/items/categories/pe/?start=0&span=10000"
PE_INCOME_URL = (
    "https://mc-launcher.webapp.163.com/items/categories/pe/{item_id}/incomes/"
    "?begin_time={begin_time}&end_time={end_time}&start=0&span=10000000"
)
PAID_DIAMOND_TYPE = "付费钻石"
REPORT_DATA_DIR_NAME = "report_data"


def get_report_account_name(account):
    return account.split("@", 1)[0]


def get_bright_color():
    full_range = list("0123456789abcdef")
    combination = ["90"]
    combination.insert(random.randint(0, 1), "ff")
    third_color = "{}{}".format(
        full_range[random.randint(0, 15)],
        full_range[random.randint(0, 15)],
    )
    combination.insert(random.randint(0, 2), third_color)
    return "#" + "".join(combination)


def get_pe_income_diamond(total_diamond):
    return total_diamond * 0.65 * 0.5


def get_subsidy_diamond(total_diamond):
    if total_diamond <= 0:
        return 0
    if total_diamond > 1000000:
        return 0
    if total_diamond > 500000:
        return total_diamond * 0.65 * 0.1
    if total_diamond > 300000:
        return total_diamond * 0.65 * 0.2
    if total_diamond > 100000:
        return total_diamond * 0.65 * 0.3
    return total_diamond * 0.65 * 0.5


def get_income_tax(income_before_tax):
    if income_before_tax > 4000:
        return (3200 + (income_before_tax - 4000) * 0.8) * 0.2
    if income_before_tax > 800:
        return (income_before_tax - 800) * 0.2
    return 0


def prompt_month_range():
    year = int(input("请输入查询年份: ").strip())
    query_type = input("请选择查询类型（1=单月查询，2=多月查询）: ").strip()

    if query_type == "1":
        month = int(input("请输入查询月份: ").strip())
        if month < 1 or month > 12:
            raise ValueError("月份必须在 1 到 12 之间")
        return [(year, month)]

    if query_type == "2":
        start_month = int(input("请输入开始月份: ").strip())
        end_month = int(input("请输入结束月份: ").strip())
        if start_month < 1 or start_month > 12 or end_month < 1 or end_month > 12:
            raise ValueError("月份必须在 1 到 12 之间")
        if start_month > end_month:
            raise ValueError("开始月份不能大于结束月份")
        return [(year, month) for month in range(start_month, end_month + 1)]

    raise ValueError("无效查询类型: {}".format(query_type))


def prompt_accounts():
    if not ACCOUNTS:
        raise ValueError("accounts_config.py 中没有配置账号")

    print("请选择账号:")
    print("0. All accounts")
    for index, account_info in enumerate(ACCOUNTS, start = 1):
        print("{}. {}".format(index, account_info["account"]))

    account_no = input("请输入账号序号: ").strip()
    if not account_no.isdigit():
        raise ValueError("账号序号必须是数字: {}".format(account_no))

    if account_no == "0":
        return [
            (account_info["account"], account_info["password"])
            for account_info in ACCOUNTS
        ]

    account_index = int(account_no) - 1
    if account_index < 0 or account_index >= len(ACCOUNTS):
        raise ValueError("无效账号序号: {}".format(account_no))

    account_info = ACCOUNTS[account_index]
    return [(account_info["account"], account_info["password"])]


def parse_pre_json(html):
    soup = BeautifulSoup(html, "lxml")
    pre_nodes = soup.select("pre")
    if not pre_nodes:
        raise ValueError("页面中未找到 JSON 数据")
    return json.loads(pre_nodes[0].text)


def visit_json(browser, url, retry = 5, sleep_seconds = 1):
    last_error = None
    for _ in range(retry):
        try:
            browser.visit(url)
            return parse_pre_json(browser.html)
        except Exception as exc:
            last_error = exc
            time.sleep(sleep_seconds)
    raise RuntimeError("请求失败: {}\n{}".format(url, last_error))


def wait_for_any_element(driver, selectors, timeout = 20):
    end_time = time.time() + timeout

    while time.time() < end_time:
        for by, value in selectors:
            elements = driver.find_elements(by, value)
            if elements:
                return elements[0]
        time.sleep(0.5)

    raise TimeoutError("未找到目标元素: {}".format(selectors))


def has_clause_error(driver):
    error_selectors = [
        (By.XPATH, "//*[contains(text(),'您需要同意相关条款')]"),
        (By.XPATH, "//*[contains(text(),'同意相关条款')]"),
    ]
    for by, value in error_selectors:
        for element in driver.find_elements(by, value):
            try:
                if element.is_displayed():
                    return True
            except Exception:
                continue
    return False


def click_login_clause(driver, timeout = 8):
    end_time = time.time() + timeout
    precise_selectors = [
        (By.CLASS_NAME, "j-mail-clause-checkbox"),
        (By.CSS_SELECTOR, ".j-mail-clause-checkbox"),
    ]
    row_selectors = [
        (By.XPATH, "//*[contains(text(),'我已经同意')]"),
        (By.XPATH, "//*[contains(text(),'隐私协议')]/.."),
        (By.XPATH, "//*[contains(text(),'用户协议')]/.."),
    ]

    while time.time() < end_time:
        for by, value in precise_selectors:
            elements = driver.find_elements(by, value)
            for element in elements:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                    time.sleep(0.1)
                    if element.is_displayed() and element.is_enabled():
                        driver.execute_script("arguments[0].click();", element)
                        time.sleep(0.2)
                        return True
                except Exception:
                    try:
                        element.click()
                        time.sleep(0.2)
                        return True
                    except Exception:
                        continue

        for by, value in row_selectors:
            elements = driver.find_elements(by, value)
            for element in elements:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
                    time.sleep(0.1)
                    if not element.is_displayed():
                        continue
                    driver.execute_script(
                        """
                        const row = arguments[0];
                        const rect = row.getBoundingClientRect();
                        const x = rect.left + 14;
                        const y = rect.top + rect.height / 2;
                        const target = document.elementFromPoint(x, y);
                        if (target) {
                            ['mouseover', 'mousedown', 'mouseup', 'click'].forEach(function(type) {
                                target.dispatchEvent(new MouseEvent(type, {
                                    view: window,
                                    bubbles: true,
                                    cancelable: true,
                                    clientX: x,
                                    clientY: y
                                }));
                            });
                        }
                        """,
                        element,
                    )
                    time.sleep(0.2)
                    return True
                except Exception:
                    try:
                        ActionChains(driver).move_to_element_with_offset(element, 14,
                                                                         element.size["height"] / 2).click().perform()
                        time.sleep(0.2)
                        return True
                    except Exception:
                        continue
        time.sleep(0.3)
    return False


def switch_to_login_frame(browser, timeout = 20):
    end_time = time.time() + timeout
    selectors = [
        (By.NAME, "email"),
        (By.CSS_SELECTOR, "input[type='email']"),
        (By.NAME, "password"),
        (By.CSS_SELECTOR, "input[type='password']"),
    ]

    while time.time() < end_time:
        browser.driver.switch_to.default_content()

        if all(browser.driver.find_elements(by, value) == [] for by, value in selectors[:2]):
            pass
        else:
            return

        iframe_list = browser.find_by_tag("iframe")
        for iframe in iframe_list:
            try:
                browser.driver.switch_to.default_content()
                browser.driver.switch_to.frame(iframe._element)
                if any(browser.driver.find_elements(by, value) for by, value in selectors):
                    return
            except Exception:
                continue

        time.sleep(0.5)

    browser.driver.switch_to.default_content()
    raise TimeoutError("未找到登录表单所在的 iframe 或页面")


def has_login_form(browser):
    selectors = [
        (By.NAME, "email"),
        (By.CSS_SELECTOR, "input[type='email']"),
        (By.NAME, "password"),
        (By.CSS_SELECTOR, "input[type='password']"),
    ]

    browser.driver.switch_to.default_content()
    if all(browser.driver.find_elements(by, value) == [] for by, value in selectors[:2]):
        if any(browser.driver.find_elements(by, value) for by, value in selectors[2:]):
            return True
    else:
        return True

    iframe_list = browser.find_by_tag("iframe")
    for iframe in iframe_list:
        try:
            browser.driver.switch_to.default_content()
            browser.driver.switch_to.frame(iframe._element)
            if any(browser.driver.find_elements(by, value) for by, value in selectors):
                return True
        except Exception:
            continue
    browser.driver.switch_to.default_content()
    return False


def wait_for_login_success(browser, timeout = 20):
    end_time = time.time() + timeout
    while time.time() < end_time:
        browser.driver.switch_to.default_content()
        current_url = str(browser.driver.current_url)
        if not current_url.startswith(LOGIN_URL):
            return True
        if not has_login_form(browser):
            return True
        time.sleep(1)
    return False


def login(browser, account, password):
    browser.visit(LOGIN_URL)
    time.sleep(2)
    try:
        switch_to_login_frame(browser)
    except TimeoutError:
        browser.driver.switch_to.default_content()
        if wait_for_login_success(browser, timeout = 3):
            time.sleep(1)
            return
        print("未自动找到登录表单。")
        print("如果页面出现验证码、二维码、二次确认或页面结构变化，请在浏览器窗口手动完成登录后回到终端。")
        input("完成登录后按回车继续...")
        if not wait_for_login_success(browser, timeout = 10):
            raise RuntimeError("登录未完成：请确认浏览器已完成登录并跳转出登录页。")
        time.sleep(1)
        return

    email_input = wait_for_any_element(
        browser.driver,
        [
            (By.NAME, "email"),
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[placeholder*='邮箱']"),
        ],
    )
    password_input = wait_for_any_element(
        browser.driver,
        [
            (By.NAME, "password"),
            (By.CSS_SELECTOR, "input[type='password']"),
        ],
    )

    email_input.clear()
    email_input.send_keys(account)
    password_input.clear()
    password_input.send_keys(password)

    click_login_clause(browser.driver, timeout = 6)

    login_button = wait_for_any_element(
        browser.driver,
        [
            (By.ID, "dologin"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.XPATH, "//button[contains(., '登录')]"),
            (By.XPATH, "//a[contains(., '登录')]"),
        ],
    )

    def submit_login():
        try:
            browser.driver.execute_script("arguments[0].click();", login_button)
        except Exception:
            try:
                login_button.click()
            except Exception:
                password_input.send_keys(Keys.ENTER)

    try:
        submit_login()
        time.sleep(0.8)
        if has_clause_error(browser.driver):
            click_login_clause(browser.driver, timeout = 2)
            submit_login()
    except Exception:
        submit_login()

    browser.driver.switch_to.default_content()
    if wait_for_login_success(browser, timeout = 15):
        time.sleep(1)
        return

    print("自动登录后页面仍停留在登录页。")
    print("如果页面出现验证码、二次确认或未自动跳转，请在浏览器窗口手动完成后回到终端。")
    input("完成登录后按回车继续...")
    if not wait_for_login_success(browser, timeout = 5):
        raise RuntimeError("登录未完成：页面仍处于登录态输入页面，请检查账号、验证码或登录页元素是否变化。")
    time.sleep(1)


def build_month_window(year_value, month_value):
    current_day = datetime(year_value, month_value, 1)
    month_start_date = datetime(current_day.year, current_day.month, 1, 0, 0, 0)
    month_end_date = month_start_date + timedelta(
        days = calendar.monthrange(current_day.year, current_day.month)[1]
    )
    month_start = (month_start_date - timedelta(days = 9)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    month_end = (month_end_date - timedelta(days = 9)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    return current_day, month_start, month_end


def collect_pe_income(browser, month_start, month_end):
    items_response = visit_json(browser, PE_ITEMS_URL)
    if items_response.get("status") != "ok":
        raise RuntimeError("PE 商品列表请求失败: {}".format(items_response))

    all_pe_items = items_response.get("data", {}).get("item", [])
    total_diamond = 0.0
    daily_diamond = {}
    component_total_diamond = {}
    component_daily_diamond = {}

    for item in all_pe_items:
        if item.get("price_type") != "diamond":
            continue

        item_id = item["item_id"]
        item_name = item["item_name"]
        component_daily_diamond[item_name] = {}

        data_url = PE_INCOME_URL.format(
            item_id = item_id,
            begin_time = month_start,
            end_time = month_end,
        )
        income_response = visit_json(browser, data_url)
        if income_response.get("status") != "ok" or not income_response.get("data"):
            continue

        data = income_response["data"]
        item_total_diamond = float(data.get("total_diamonds", 0))
        total_diamond += item_total_diamond
        component_total_diamond[item_name] = item_total_diamond

        for order in data.get("orders", []):
            if order.get("point_type") != PAID_DIAMOND_TYPE:
                continue
            if order.get("refund_status") != "":
                continue

            ship_time = datetime.strptime(order["ship_time"][:10], "%Y-%m-%d").date()
            day = str(ship_time)
            point = float(order.get("point", 0))

            daily_diamond[day] = daily_diamond.get(day, 0.0) + point
            component_daily_diamond[item_name][day] = (
                    component_daily_diamond[item_name].get(day, 0.0) + point
            )

    return total_diamond, daily_diamond, component_total_diamond, component_daily_diamond


def build_income_summary(total_diamond, daily_diamond, component_total_diamond, component_daily_diamond):
    income_diamond = get_pe_income_diamond(total_diamond)
    subsidy_diamond = get_subsidy_diamond(total_diamond)
    total_income_diamond = income_diamond + subsidy_diamond
    income_before_tax = total_income_diamond / 100
    income_tax = get_income_tax(income_before_tax)
    income_real = income_before_tax - income_tax

    scale = income_real / total_diamond * 100 if total_diamond > 0 else 0.0

    daily_income = {
        day: diamonds / 100 * scale
        for day, diamonds in daily_diamond.items()
    }

    component_daily_income = {}
    for item_name, item_daily_diamond in component_daily_diamond.items():
        item_income = {
            day: diamonds / 100 * scale
            for day, diamonds in item_daily_diamond.items()
        }
        if item_income:
            component_daily_income[item_name] = item_income

    component_month_income = []
    for item_name, diamonds in component_total_diamond.items():
        tax_after = diamonds / 100 * scale
        if tax_after > 0:
            component_month_income.append((diamonds, tax_after, item_name))
    component_month_income.sort(key = lambda row: row[1], reverse = True)

    return {
        "income_diamond": income_diamond,
        "subsidy_diamond": subsidy_diamond,
        "total_income_diamond": total_income_diamond,
        "income_before_tax": income_before_tax,
        "income_tax": income_tax,
        "income_real": income_real,
        "daily_income": daily_income,
        "component_daily_income": component_daily_income,
        "component_month_income": component_month_income,
    }


def print_summary(account, current_day, total_diamond, daily_diamond, summary):
    print("monthStart/monthEnd 已计算完成")
    print("=" * 80)
    print("统计账号: {}".format(account))
    print("统计月份: {}".format(current_day.strftime("%Y-%m")))
    print("原始钻石: {:15.2f}".format(total_diamond))
    print("分成钻石: {:15.2f}".format(summary["income_diamond"]))
    print("补贴钻石: {:15.2f}".format(summary["subsidy_diamond"]))
    print("总钻石数: {:15.2f}".format(summary["total_income_diamond"]))
    print("税前收益: {:15.2f}".format(summary["income_before_tax"]))
    print("预缴税额: {:15.2f}".format(summary["income_tax"]))
    print("税后收益: {:15.2f}".format(summary["income_real"]))
    print("=" * 80)

    print("\n每日钻石收益:")
    for day in sorted(daily_diamond.keys()):
        print("{}--------{:15.2f}".format(day, daily_diamond[day]))

    if summary["component_month_income"]:
        print("\nPE 组件本月收益明细:")
        print("{:>15} {:>15}  {}".format("钻石数", "税后收益", "组件名称"))
        print("-" * 60)
        for diamonds, tax_after, name in summary["component_month_income"]:
            print("{:>15.2f} {:>15.2f}  {}".format(diamonds, tax_after, name))

    print("\n组件每日收益数据:")
    print(summary["component_daily_income"])


def build_day_component_breakdown(component_daily_diamond, component_daily_income):
    day_map = {}
    for component_name, daily_values in component_daily_diamond.items():
        for day, diamonds in daily_values.items():
            income = component_daily_income.get(component_name, {}).get(day, 0.0)
            day_map.setdefault(day, []).append((component_name, diamonds, income))

    for day, rows in day_map.items():
        rows.sort(key = lambda row: (row[2], row[1], row[0]), reverse = True)
    return day_map


def build_report_payload(account, report, generated_at):
    current_day = report["current_day"]
    summary = report["summary"]
    daily_diamond = OrderedDict(sorted(report["daily_diamond"].items(), key = lambda row: row[0]))
    component_daily_diamond = report["component_daily_diamond"]
    component_daily_income = summary["component_daily_income"]
    day_component_breakdown = build_day_component_breakdown(component_daily_diamond, component_daily_income)

    return {
        "account": account,
        "generated_at": generated_at,
        "month": current_day.strftime("%Y-%m"),
        "summary": {
            "total_diamond": report["total_diamond"],
            "income_diamond": summary["income_diamond"],
            "subsidy_diamond": summary["subsidy_diamond"],
            "total_income_diamond": summary["total_income_diamond"],
            "income_before_tax": summary["income_before_tax"],
            "income_tax": summary["income_tax"],
            "income_real": summary["income_real"],
        },
        "days": [
            {
                "day": day,
                "diamonds": daily_diamond[day],
                "income": summary["daily_income"].get(day, 0.0),
                "components": [
                    {
                        "name": component_name,
                        "diamonds": diamonds,
                        "income": income,
                    }
                    for component_name, diamonds, income in day_component_breakdown.get(day, [])
                ],
            }
            for day in daily_diamond.keys()
        ],
        "components": [
            {
                "name": component_name,
                "total_diamonds": next(
                    (diamonds for diamonds, _, name in summary["component_month_income"] if name == component_name),
                    0.0,
                ),
                "total_income": next(
                    (income for _, income, name in summary["component_month_income"] if name == component_name),
                    0.0,
                ),
                "daily": [
                    {
                        "day": day,
                        "diamonds": component_daily_diamond.get(component_name, {}).get(day, 0.0),
                        "income": income,
                    }
                    for day, income in OrderedDict(sorted(daily_income.items(), key = lambda row: row[0])).items()
                ],
            }
            for component_name, daily_income in sorted(component_daily_income.items(), key = lambda row: row[0])
        ],
    }


def save_month_json_files(account, month_reports, output_dir):
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    data_dir = output_dir / REPORT_DATA_DIR_NAME
    data_dir.mkdir(exist_ok = True)
    report_account = get_report_account_name(account)

    for report in month_reports:
        payload = build_report_payload(account, report, generated_at)
        year_month = report["current_day"].strftime("%Y_%#m") if os.name == "nt" else report["current_day"].strftime(
            "%Y_%-m")
        data_path = data_dir / "{}_{}.json".format(report_account, year_month)
        data_path.write_text(
            json.dumps(payload, ensure_ascii = False, indent = 2),
            encoding = "utf-8",
        )
        print("月度 JSON 已生成/替换: {}".format(data_path))

    account_map = {}
    for json_path in data_dir.glob("*.json"):
        if json_path.name == "index.json":
            continue
        stem_parts = json_path.stem.rsplit("_", 2)
        if len(stem_parts) != 3 or not stem_parts[1].isdigit() or not stem_parts[2].isdigit():
            continue
        account_name = stem_parts[0]
        year_value = int(stem_parts[1])
        month_value = int(stem_parts[2])
        account_map.setdefault(account_name, []).append(
            {
                "month": "{:04d}-{:02d}".format(year_value, month_value),
                "file": json_path.name,
                "year": year_value,
                "month_number": month_value,
            }
        )

    accounts = []
    for account_name, files in account_map.items():
        files.sort(key = lambda item: (item["year"], item["month_number"]), reverse = True)
        accounts.append(
            {
                "account": account_name,
                "months": files,
            }
        )
    accounts.sort(key = lambda item: item["account"])

    index_path = data_dir / "index.json"
    index_path.write_text(
        json.dumps({"accounts": accounts}, ensure_ascii = False, indent = 2),
        encoding = "utf-8",
    )
    print("JSON 索引已更新: {}".format(index_path))


def save_and_open_report(account, month_reports):
    output_dir = Path(__file__).resolve().parent
    save_month_json_files(account, month_reports, output_dir)
    report_path = output_dir / "\u6536\u76ca\u62a5\u544a.html"
    if not report_path.exists():
        raise FileNotFoundError("未找到 HTML 报告页面: {}".format(report_path))
    os.startfile(str(report_path))
    print("请在打开的页面中点击“选择 report_data 文件夹”读取本地 JSON。")


def open_report_page(output_dir):
    report_path = output_dir / "\u6536\u76ca\u62a5\u544a.html"
    if not report_path.exists():
        raise FileNotFoundError("HTML report page not found: {}".format(report_path))
    os.startfile(str(report_path))
    print("Please select the report_data folder in the opened report page to load local JSON.")


def plot_income(month_results):
    fig, ax = plt.subplots(1, 1)
    labels = []

    for label, daily_income in month_results:
        ordered_income = OrderedDict(sorted(daily_income.items(), key = lambda row: row[0]))
        ax.plot(
            list(ordered_income.keys()),
            list(ordered_income.values()),
            label = label,
            color = get_bright_color(),
        )
        labels.append(label)

    ax.xaxis.set_major_locator(ticker.MultipleLocator(100))
    plt.legend(labels = labels)
    plt.xticks(size = "small", rotation = 50, fontsize = 13)
    plt.show()


def run_account_report(account, password, month_range, output_dir, label_with_account = False):
    month_results = []
    month_reports = []

    browser = Browser("chrome")
    try:
        login(browser, account, password)

        for year_value, month_value in month_range:
            current_day, month_start, month_end = build_month_window(year_value, month_value)
            print("monthStart {} monthEnd {}".format(month_start, month_end))

            total_diamond, daily_diamond, component_total_diamond, component_daily_diamond = collect_pe_income(
                browser, month_start, month_end
            )
            summary = build_income_summary(
                total_diamond,
                daily_diamond,
                component_total_diamond,
                component_daily_diamond,
            )
            print_summary(account, current_day, total_diamond, daily_diamond, summary)
            month_label = current_day.strftime("%Y-%m")
            if label_with_account:
                month_label = "{} {}".format(get_report_account_name(account), month_label)
            month_results.append((month_label, summary["daily_income"]))
            month_reports.append(
                {
                    "current_day": current_day,
                    "total_diamond": total_diamond,
                    "daily_diamond": daily_diamond,
                    "component_daily_diamond": component_daily_diamond,
                    "summary": summary,
                }
            )

    finally:
        browser.quit()

    save_month_json_files(account, month_reports, output_dir)
    return month_results


def main():
    month_range = prompt_month_range()
    selected_accounts = prompt_accounts()
    output_dir = Path(__file__).resolve().parent
    month_results = []
    label_with_account = len(selected_accounts) > 1

    for account, password in selected_accounts:
        month_results.extend(
            run_account_report(
                account,
                password,
                month_range,
                output_dir,
                label_with_account = label_with_account,
            )
        )

    open_report_page(output_dir)
    plot_income(month_results)


if __name__ == "__main__":
    main()
