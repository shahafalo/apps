from collections import defaultdict
import datetime
import json
import time
import os

from selenium import webdriver
from selenium.webdriver.common.by import By


NONE_DISPLAY_STR = "display: none;"
CHOOSE_LOCAL_STR = "Selecione um local de atendimento"
HISTORY_PATH = "./portugal_turns.json"


def main():
    driver = webdriver.Firefox()
    driver.get("https://siga.marcacaodeatendimento.pt/Marcacao/Entidades")
    driver.find_element(By.XPATH, '//button[@title="IRN Registo"]').click()
    click_on_wanted_option(driver, "IdCategoria",
                           "22002"  # Cidadão
                           )
    click_on_wanted_option(driver, "IdSubcategoria",
                           "22003"  # Cartão de Cidadão - Pedido/Renovação
                           )
    click_on_wanted_option(driver, "IdMotivo",
                           "22705"  # Pedido/Renovação de Cartão de Cidadão
                           )
    driver.find_element(By.CLASS_NAME, 'set-date-button').click()
    time.sleep(0.5)
    click_on_wanted_option(driver, "IdDistrito",
                           "11"  # LISBOA
                           )
    click_on_wanted_option(driver, "IdLocalidade",
                           "6"  # LISBOA
                           )
    open_turns_by_site = defaultdict(list)
    element = driver.find_element(By.ID, "IdLocalAtendimento")
    options = element.find_elements(By.TAG_NAME, "option")
    site_names = [option.get_attribute("text") for option in options
                  if option.get_attribute("text") != CHOOSE_LOCAL_STR]
    for site_name in site_names:
        element = driver.find_element(By.ID, "IdLocalAtendimento")
        options = element.find_elements(By.TAG_NAME, "option")
        option = [option for option in options if option.get_attribute("text") == site_name][0]
        option.click()
        driver.find_element(By.CLASS_NAME, 'set-date-button').click()
        time.sleep(0.5)
        get_all_turns(driver, open_turns_by_site, site_name)
        time.sleep(0.5)
    driver.close()
    if not os.path.exists(HISTORY_PATH):
        with open(HISTORY_PATH, "w") as f:
            json.dump({}, f)
    
    with open(HISTORY_PATH, "r") as f:
        history = json.load(f)

    new_turns = get_new_turns(history, open_turns_by_site)
    if new_turns:
        print("A change detected, should send mail")
        print("new_turns: %s", new_turns)
    else:
        print("Nothing changed, closing")

    with open(HISTORY_PATH, "w") as f:
        json.dump(dict(open_turns_by_site), f)


def get_all_turns(driver, open_turns_by_site, site_name):
    time.sleep(0.5)
    if len(driver.find_elements(By.CLASS_NAME, 'error-message')) == 1:
        print("skipping current option, no available appointments for: %s", site_name)
        driver.find_element(By.CLASS_NAME, 'm-left').click()  # previous page
        return
    driver.find_element(By.CLASS_NAME, 'set-date-button').click()  # get all dates
    time.sleep(1)
    while True:
        days_element = driver.find_element(By.CLASS_NAME, 'week-days')
        buttons_elements = days_element.find_elements(By.XPATH, '//button[contains(@id, "2022")]')
        open_turns = [button.get_attribute("id") for button in buttons_elements if
                      button.get_property("parentElement").get_attribute("style") != NONE_DISPLAY_STR]
        open_turns = [transform_date_str_to_datetime(turn.split(';')[-1])
                      for turn in open_turns]  # clean format '12785;2022-09-20 09:30'
        open_turns_by_site[site_name] += open_turns
        right_arrow_element = driver.find_element(By.CLASS_NAME, 'arrow-right')
        if right_arrow_element.get_attribute("style") == NONE_DISPLAY_STR:
            previous_element = driver.find_element(By.CLASS_NAME, 'previous')
            link_elements = previous_element.find_elements(By.XPATH, "//a")
            [l for l in link_elements if l.get_attribute("onclick")][0].click()  # clicking on previous page link
            time.sleep(0.5)
            return
        else:
            right_arrow_element.click()


def click_on_wanted_option(driver, wanted_id, wanted_option):
    time.sleep(0.1)
    element = driver.find_element(By.ID, wanted_id)
    options = element.find_elements(By.TAG_NAME, "option")
    for option in options:
        value = option.get_attribute("value")
        if value == wanted_option:
            option.click()
            return
    print("couldn't find wanted option :(")


def transform_date_str_to_datetime(date_str):
    try:
        return datetime.datetime.strptime(date_str, '%d-%m-%Y %H:%M:%S')
    except ValueError:
        return datetime.datetime.strptime(date_str, '%Y-%m-%d %H:%M')


def get_new_turns(history, current_turns_by_site):
    new_turns_by_site = {}
    for site in current_turns_by_site:
        previous_turns = set(history.get(site, []))
        current_turns = set(current_turns_by_site[site])
        new_turns = current_turns.difference(previous_turns)
        if new_turns:
            new_turns_by_site[site] = new_turns
    return new_turns_by_site


if __name__ == '__main__':
    main()
