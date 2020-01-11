import autoreview
from selenium import webdriver
from selenium.webdriver.firefox.options import Options

options = Options()
options.headless = False
driver = webdriver.Firefox(options=options)
ur = autoreview.UdemyReviews(driver)
ur.handle_reviews(test=False, slow=False)
