import traceback
import sys
import time
from datetime import datetime
import os
from random import randrange

from selenium.common.exceptions import NoSuchElementException
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

import auths
from languages import class_languages, languages
from responses import responses
from skip import classes_to_skip

from googletrans import Translator

import yagmail


def deEmojify(inputString):
    return inputString.encode('ascii', 'ignore').decode('ascii')


class UdemyReviews:
    def __init__(self, browser):
        os.chdir(os.path.dirname(__file__))
        self.start_date = datetime.now()
        self.yag = yagmail.SMTP(auths.gmail_user, auths.gmail_pass)
        try:
            os.remove(os.getcwd()+'/lock.txt')
            # print('lock file removed')
        except FileNotFoundError:
            # print('lock file not found')
            pass
        self.translator = Translator(service_urls=['translate.google.com'])
        sys.excepthook = self.handle_exit
        self.review_data = {}
        self.initialize_dict(self.review_data)
        self.browser = browser
        self.browser.get('https://www.udemy.com/join/login-popup/?next=/instructor/performance/reviews/?unresponded=1')
        WebDriverWait(self.browser, 25).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "#email--1"))).send_keys(auths.username)
        self.browser.find_element_by_css_selector('#id_password').send_keys(auths.password)
        self.browser.find_element_by_css_selector('#submit-id-submit').click()
        time.sleep(3)

    def handle_exit(self, exctype=None, value=None, tb=None):
        try:
            self.browser.close()
            self.browser.quit()
        except:
            pass
        subject = "Udemy Reviews processed " + str(self.start_date)
        if exctype:
            subject += " w/ error"
        text = ""
        text += 'Processed ' + str(self.review_data['total_reviews']) + ' reviews'
        text += '\n' + 'Total reviews responded: ' + str(self.review_data['total_answered'])
        text += '\n' + 'Total reviews skipped: ' + str(self.review_data['total_skipped'])
        text += '\n' + '\nTotal star count:'
        for star, num in self.review_data['total_stars'].items():
            text += '\n' + str(star) + ':  ' + str(num)
        text += '\n' + '\nTotal survey count (negative, neutral, positive):'
        text += '\n' + str(self.survey_to_string(self.review_data['total_survey']))
        if exctype:
            text += '\n \n Ended with an error: \n'
            error_strings = traceback.format_exception(exctype, value, tb)
            for string in error_strings:
                text += string
        print(subject)
        print(text)
        self.yag.send(to='anthonyebiner+udemybot@gmail.com', subject=subject, contents=text)

    def survey_to_string(self, survey):
        string = ""
        for survey, answers in survey.items():
            if survey == 1:
                string += 'Valuable information: ' + str(answers[-1]) + '/' + str(answers[0]) + '/' + str(
                    answers[1]) + '\n'
            elif survey == 2:
                string += 'Clear explanations: ' + str(answers[-1]) + '/' + str(answers[0]) + '/' + str(
                    answers[1]) + '\n'
            elif survey == 3:
                string += 'Engaging delivery: ' + str(answers[-1]) + '/' + str(answers[0]) + '/' + str(
                    answers[1]) + '\n'
            elif survey == 4:
                string += 'Helpful practice activities: ' + str(answers[-1]) + '/' + str(answers[0]) + '/' + str(
                    answers[1]) + '\n'
            elif survey == 5:
                string += 'Accurate course description: ' + str(answers[-1]) + '/' + str(answers[0]) + '/' + str(
                    answers[1]) + '\n'
            elif survey == 6:
                string += 'Knowledgeable instructor: ' + str(answers[-1]) + '/' + str(answers[0]) + '/' + str(
                    answers[1])
        return string

    def initialize_dict(self, dictionary):
        dictionary['total_reviews'] = 0
        dictionary['total_stars'] = {1: 0, 1.5: 0, 2: 0, 2.5: 0, 3: 0, 3.5: 0, 4: 0, 4.5: 0, 5: 0}
        dictionary['total_survey'] = {0: {-1: 0, 0: 0, 1: 0}, 1: {-1: 0, 0: 0, 1: 0}, 2: {-1: 0, 0: 0, 1: 0},
                                      3: {-1: 0, 0: 0, 1: 0}, 4: {-1: 0, 0: 0, 1: 0}, 5: {-1: 0, 0: 0, 1: 0}}
        dictionary['total_answered'] = 0
        dictionary['total_skipped'] = 0
        dictionary['total_reported'] = 0

    def scroll_shim(self, object):
        x = object.location['x']
        y = object.location['y']
        scroll_by_coord = 'window.scrollTo(%s,%s);' % (
            x,
            y
        )
        self.browser.execute_script(scroll_by_coord)

    def get_reviews(self):
        while len(self.browser.find_elements_by_class_name('mb20')) != 10:
            time.sleep(0.1)
        return self.browser.find_elements_by_class_name('mb20')

    def get_num_stars(self, review):
        stars = float(review.find_element_by_css_selector("div[data-purpose='star-rating-shell'").get_attribute('aria-label').split(' ')[1])
        if stars < 1:
            stars = 1
        # print(str(stars) + ' out of 5 stars')
        return stars

    def get_review_text(self, review):
        try:
            text = review.find_element_by_css_selector("div[class='view-more-container--view-more--25_En']").text
            return deEmojify(text)
        except NoSuchElementException:
            return None

    def get_survey_responses(self, review):
        survey_responses = []
        try:
            surveys = review.find_elements_by_css_selector("div[class='review--survey-answer-container--gTHBk']")
            if len(surveys) != 6:
                return []
            for survey in surveys:
                survey_response = survey.find_element_by_css_selector("[class*='review--survey-answer']").get_attribute(
                    'aria-label')
                if 'positive' in survey_response.lower():
                    survey_responses += [1]
                elif 'neutral' in survey_response.lower():
                    survey_responses += [0]
                elif 'negative' in survey_response.lower():
                    survey_responses += [-1]
                else:
                    raise ValueError('Got label ' + survey_response.lower())
            if len(survey_responses) != 6:
                raise ValueError('Only got ' + str(len(survey_responses)) + ' Responses')
            return survey_responses
        except NoSuchElementException:
            return []

    def get_course_name(self, review):
        return review.find_element_by_css_selector("a[data-purpose='course-title']").text

    def get_first_name(self, review):
        return review.find_element_by_css_selector("[href*='/user/']").text.split(' ')[0]

    def handle_reviews(self, test=False, slow=True):
        while not os.path.exists(os.getcwd()+'/lock.txt'):
            for review in self.get_reviews():
                self.scroll_shim(review)

                # print('---')

                course_name = self.get_course_name(review)
                # print(course_name)
                try:
                    first_name = self.get_first_name(review)
                except NoSuchElementException:
                    first_name = ''
                stars = self.get_num_stars(review)
                review_text = self.get_review_text(review)
                survey_responses = self.get_survey_responses(review)

                self.review_data['total_reviews'] += 1

                self.review_data['total_stars'][stars] += 1

                for n, survey in enumerate(survey_responses):
                    self.review_data['total_survey'][n][survey] += 1
                # print(survey_responses)

                # if not review_text:
                    # print('No text')
                # else:
                    # print(review_text)

                if review_text and stars < 4 or course_name in classes_to_skip:
                    self.review_data['total_skipped'] += 1
                    # print('Skipped')
                    continue

                try:
                    lang = class_languages[course_name]
                except KeyError:
                    lang = 'en'

                if lang not in languages:
                    self.review_data['total_skipped'] += 1
                    # print('Language ({}) not Recognized'.format(lang))
                    # print('Skipped')
                    if slow:
                        time.sleep(2)
                    continue

                try:
                    WebDriverWait(review, 10).until(
                        EC.visibility_of_element_located(
                            (By.CSS_SELECTOR, "button[data-purpose='respond-button']"))).click()

                    if review_text:
                        lang = self.translator.detect(review_text)
                        if lang.lang not in languages or lang.confidence < 0.5:
                            try:
                                lang = class_languages[course_name]
                            except KeyError:
                                lang = 'en'
                        else:
                            lang = lang.lang

                    response = responses['en'][stars].format(first_name)
                    if lang not in responses.keys():
                        response = self.translator.translate(response, src='en', dest=lang).text

                    if slow:
                        time.sleep(randrange(1, 3))
                    else:
                        time.sleep(0.25)

                    if stars >= 4 or not review_text:
                        review.find_element_by_css_selector("textarea[class='form-control']").send_keys(
                            response)
                    else:
                        # print('Skipped')
                        self.review_data['total_skipped'] += 1
                        continue

                    if slow:
                        time.sleep(randrange(1, 3))
                    else:
                        time.sleep(0.1)

                    if not test:
                        review.find_element_by_css_selector("button[data-purpose='post-response-button']").click()
                        # print('Response Posted ({})'.format(lang))

                    if slow:
                        time.sleep(randrange(1, 3))

                    WebDriverWait(review, 10).until(EC.visibility_of_element_located(
                        (By.CSS_SELECTOR, "div[data-purpose='response-container']")))

                    self.review_data['total_answered'] += 1

                except NoSuchElementException:
                    self.review_data['total_skipped'] += 1
                    # print('Already responded')
                    # print('Skipped')

            WebDriverWait(self.browser, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, '.pagination-next'))).click()
        # print('Exiting')
        self.handle_exit()
