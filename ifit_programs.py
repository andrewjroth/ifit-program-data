import json
import logging
import re
from getpass import getpass
from lxml import html
import requests


log = logging.getLogger('ifitdata')
log.setLevel(logging.INFO)


class iFitData:
    def __init__(self):
        self.session = requests.session()
    
    def do_login(self, email, password):
        page = self.session.post('https://www.ifit.com/web-api/login',
            json=dict(email=email, password=password, rememberMe=False))
        log.info("Login Complete: %s %s", page.status_code, page.reason)
        page.raise_for_status()
    
    def program_iter(self):
        page = self.session.get('https://www.ifit.com/library/video')
        log.info("Got iFit Library: %s %s", page.status_code, page.reason)
        page.raise_for_status()
        tree = html.fromstring(page.content)
        for program in tree.xpath('//div[@id="program-list"]/div'):
            p_title_node = program.xpath('div[@class="challenge-details"]/a[@class="title"]')[0]
            p_title = p_title_node.text
            p_url = p_title_node.attrib['href']
            if not p_url.startswith("http"):
                p_url = "https://www.ifit.com{}".format(p_url)
            p_type_m = re.search('icon-(\w+)', program.xpath('i')[0].attrib['class'])
            p_type = p_type_m.group(1) if p_type_m else 'unknown'
            p_image = program.xpath('a/img')[0].attrib['src']
            p_summary = program.xpath('div[@class="challenge-details"]/div[@class="quick-summary"]')[0].text
            p_level = program.xpath('div[@class="challenge-details"]/div[@class="difficulty-level"]/span')[0].text
            log.info("Captured Program: %s <%s>", p_title, p_url)
            yield dict(title=p_title, url=p_url, type=p_type, 
                image=p_image, summary=p_summary, level=p_level)
    
    def program_workout_iter(self, url):
        page = self.session.get(url)
        log.info("Got Program Details: %s %s", page.status_code, page.reason)
        page.raise_for_status()
        tree = html.fromstring(page.content)
        for workout in tree.xpath('//li[@class="clearfix js-workout-item"]'):
            w_data = json.loads(workout.xpath('script')[0].text)
            elem_details = workout.xpath('div[@class="wo-details"]')[0]
            elem_a = elem_details.getchildren()[0]
            w_url = elem_a.attrib['href']
            if not w_url.startswith("http"):
                w_url = "https://www.ifit.com{}".format(w_url)
            elem_span = elem_a.getchildren()[0]
            w_title = elem_span.text
            w_distance = workout.xpath('div[@class="wo-icon-lists clearfix js-workout-list-details"]/div[@class="wo-distance list-icon"]/strong')[0].text
            w_elevation = workout.xpath('div[@class="wo-icon-lists clearfix js-workout-list-details"]/div[@class="wo-elevation list-icon"]/strong')[0].text
            w_calories = workout.xpath('div[@class="wo-icon-lists clearfix js-workout-list-details"]/div[@class="wo-calories list-icon"]/strong')[0].text
            log.info("Captured Program Workout: %s <%s>", w_title, w_url)
            yield dict(title=w_title, url=w_url, data=w_data,
                distance=w_distance, elevation=w_elevation, calories=w_calories)


if __name__ == '__main__':
    logging.basicConfig()
    ifit = iFitData()
    usr = input("iFit Email: ")
    pwd = getpass()
    ifit.do_login(usr, pwd)
    result = list()
    for program in ifit.program_iter():
        program['workouts'] = list(ifit.program_workout_iter(program['url']))
        result.append(program)
    log.info("Completed Capture, saving data")
    with open('ifit-program-data.json', 'w') as f:
        json.dump(result, f, indent=2)

