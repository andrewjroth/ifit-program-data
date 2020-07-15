import json
import logging
import re
from getpass import getpass
from lxml import html
import requests
import time


log = logging.getLogger('ifitdata')
log.setLevel(logging.INFO)


class iFitData:
    def __init__(self):
        self.session = requests.session()
        self.login = False
    
    def do_login(self, email, password):
        page = self.session.post('https://www.ifit.com/web-api/login',
            json=dict(email=email, password=password, rememberMe=False))
        log.info("Login Complete: %s %s", page.status_code, page.reason)
        page.raise_for_status()
        self.login = True
    
    def program_iter(self):
        page = self.session.get('https://www.ifit.com/library/video')
        log.info("Got iFit Library: %s %s", page.status_code, page.reason)
        page.raise_for_status()
        tree = html.fromstring(page.content)
        for program in tree.xpath('//div[@id="program-list"]/div'):
            p_title_node = program.xpath('div[@class="challenge-details"]/a[@class="title"]')[0]
            p_title = p_title_node.text
            p_url = p_title_node.attrib['href']
            id_match = re.search('programDetails/([0-9a-f]+)/', p_url)
            p_id = (id_match.group(1) if id_match else None)
            if not p_url.startswith("http"):
                p_url = "https://www.ifit.com{}".format(p_url)
            p_type_m = re.search('icon-(\w+)', program.xpath('i')[0].attrib['class'])
            p_type = p_type_m.group(1) if p_type_m else 'unknown'
            p_image = program.xpath('a/img')[0].attrib['src']
            p_summary = program.xpath('div[@class="challenge-details"]/div[@class="quick-summary"]')[0].text
            p_level = program.xpath('div[@class="challenge-details"]/div[@class="difficulty-level"]/span')[0].text
            log.info("Captured Program: %s <%s>", p_title, p_url)
            yield dict(id=p_id, title=p_title, url=p_url, type=p_type, 
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
            w_id = w_url.split('/')[-1]
            if not w_url.startswith("http"):
                w_url = "https://www.ifit.com{}".format(w_url)
            elem_span = elem_a.getchildren()[0]
            w_title = elem_span.text
            w_distance = workout.xpath('div[@class="wo-icon-lists clearfix js-workout-list-details"]/div[@class="wo-distance list-icon"]/strong')[0].text
            w_elevation = workout.xpath('div[@class="wo-icon-lists clearfix js-workout-list-details"]/div[@class="wo-elevation list-icon"]/strong')[0].text
            w_calories = workout.xpath('div[@class="wo-icon-lists clearfix js-workout-list-details"]/div[@class="wo-calories list-icon"]/strong')[0].text
            log.info("Captured Program Workout: %s <%s>", w_title, w_url)
            yield dict(id=w_id, title=w_title, url=w_url, data=w_data,
                distance=w_distance, elevation=w_elevation, calories=w_calories)

    def download_data(self):
        if not self.login:
            return ValueError("Must Login First")
        programs = list()
        workouts = list()
        start = time.perf_counter()
        for program in ifit.program_iter():
            prog_workouts = list(ifit.program_workout_iter(program['url']))
            for w in prog_workouts:
                w['program'] = program['id']
            workouts.extend(prog_workouts)
            program['workouts'] = list(map(lambda w: w['id'], prog_workouts))
            programs.append(program)
        download_time = time.perf_counter() - start
        log.info("Completed Capture in %03.2f secs, saving data", download_time)
        with open("ifit-program-data.json", 'w') as f:
            json.dump(programs, f, indent=2)
        with open("ifit-workout-data.json", 'w') as f:
            json.dump(workouts, f, indent=2)
        finish = time.perf_counter() - start
        log.info("Completed Download in %03.2f secs and finished in %03.2f secs", download_time, finish)
        

if __name__ == '__main__':
    logging.basicConfig()
    ifit = iFitData()
    usr = input("iFit Email: ")
    pwd = getpass()
    ifit.do_login(usr, pwd)
    ifit.download_data()

