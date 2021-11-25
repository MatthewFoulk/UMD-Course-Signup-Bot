
import os
from datetime import datetime as dt

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import NoSuchWindowException, TimeoutException
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


from myemail import send_email

# CHANGE THESE
COURSE = "CMSC351"
SECTION = "0301"
# SECTION = "0101" # Used for debugging

URL = "https://app.testudo.umd.edu/main/dropAdd"

# TIMEOUTS
SHORT_TIMEOUT = 5
MED_TIMEOUT = 10
LONG_TIMEOUT = 30

# HTML
SPRING_DROP_ADD_XPATH = "//*[@id='mainContent']/div[2]/div/div[1]/div/div[2]/button[3]"
MULTIPLE_SESSIONS_BUTTON_XPATH = "//*[@id='mainContent']/div[2]/button"
SECTION_SEAT_COUNT_XPATH = "//*[@id='drop_add_form']/table/tbody/tr[7]/td/div/div[2]/table/tbody/tr[3]/td[3]/span"
# SECTION_SEAT_COUNT_XPATH = "//*[@id='drop_add_form']/table/tbody/tr[7]/td/div/div[2]/table/tbody/tr[1]/td[3]/span" # Used for debugging, refers to 0101 section
REGISTER_CANCEL_XPATH = "//*[@id='drop_add_form']/table/tbody/tr[7]/td/div/div[3]/button[2]"
DUO_PUSH_XPATH = "//*[@id='auth_methods']/fieldset[1]/div[1]/button"
DUO_REMEMBER_NAME = "dampen_choice" 
COURSE_INPUT_NAME = "pendingCourseCourse"
SECTION_INPUT_XPATH = "//*[@id='crs_pending']/td[3]/input"
DROP_BUTTON_XPATH = "//*[@id='drop_add_actionButtons_container_CMSC351_0101']/div/div/div/button[2]"
DROP_CONFIRM_BUTTON_XPATH = "//*[@id='drop_add_form']/table/tbody/tr[2]/td[1]/div[2]/button[1]"

def main():

    try:
        # Load environment variables from .env
        load_dotenv()

        # Initialize chrome profile, and maximize screen
        options = webdriver.ChromeOptions()
        options.add_argument(f"user-data-dir={os.environ.get('CHROME_PROFILE_DIR')}")
        # options.add_argument(f"profile-directory={os.environ.get('CHROME_PROFILE')}") # For debugging with windows pc
        options.add_argument("--headless")  # For server, comment for debugging
        options.add_experimental_option('excludeSwitches', ['enable-logging']) # Disable logging
        # options.add_argument("--start-maximized")     # For Debugging

        # Initialze webdriver
        service = Service(ChromeDriverManager(log_level=0).install())
        driver = webdriver.Chrome(service=service, options=options)

        # Fetch initial url
        driver.get(URL)

        # Login
        login(driver, os.environ.get("UMD_USERNAME"), os.environ.get("UMD_PASSWORD"))

        # Wait for next page to load, then submit 2-factor authentifaction (if it exists)
        try:
            WebDriverWait(driver, SHORT_TIMEOUT).until(EC.frame_to_be_available_and_switch_to_it((By.TAG_NAME, "iframe")))
            duo_2fa(driver)

        # Webpage either never loaded or no 2fa was needed, assume the latter
        except TimeoutException:
            pass

        # Click button for Spring semester drop add
        WebDriverWait(driver, SHORT_TIMEOUT).until(EC.presence_of_element_located((By.XPATH, 
            SPRING_DROP_ADD_XPATH))).click()
        
        # Attempt to add class to see how many seats
        try:
            add_class(driver, COURSE, "")

        # If it fails, assume multiple session warning. Click sign out button and try again
        except TimeoutException:
            driver.find_element(By.XPATH, MULTIPLE_SESSIONS_BUTTON_XPATH).click()
            add_class(driver, COURSE, "")

        # Check if there are seats available for Justin's section
        WebDriverWait(driver, MED_TIMEOUT).until(EC.presence_of_element_located((By.XPATH, 
            SECTION_SEAT_COUNT_XPATH)))
        seats = driver.find_element(By.XPATH, SECTION_SEAT_COUNT_XPATH).text

        if seats.isdigit(): # "Closed" if no seats, so not a digit
            print(f"{dt.now()}: SEATS AVAILABLE")
            driver.find_element(By.XPATH, REGISTER_CANCEL_XPATH).click()    # Cancel the registering done to check seat count
            drop_class(driver)
            add_class(driver, COURSE, SECTION)

            # Send email
            message = f"You've been successfully added to {COURSE} {SECTION} at {dt.now()}. There were {seats} spots available."
            subject = f"SUCCESS: SIGNED UP FOR {COURSE} {SECTION}"
            send_email(message, subject, os.environ.get("SENDER"), 
                os.environ.get("RECEIVER"), os.environ.get("SENDER_PASSWORD"))

            # Send text    
            send_email(message, "", os.environ.get("SENDER"), os.environ.get("TEXT_EMAIL"), os.environ.get("SENDER_PASSWORD"))
        else:
            print(f"{dt.now()}: NO SEATS")

    # Catch all exceptions for logging and debuggin purposes, notify via 
    except Exception as e:
        print(f"{dt.now()}: (ERROR) {e}")

        message = f"The following error occured at {dt.now()}:\n\n{e}"
        subject = "ERROR: SIGNUP SCRIPT"
        send_email(message, subject, os.environ.get("SENDER"), 
            os.environ.get("RECEIVER"), os.environ.get("SENDER_PASSWORD"))

        # Send text    
        send_email(message, "", os.environ.get("SENDER"), os.environ.get("TEXT_EMAIL"), os.environ.get("SENDER_PASSWORD"))

def login(driver: webdriver.Chrome, username: str, password: str, username_id="username", password_id="password"):
    """Generic login

    Args:
        driver (webdriver.Chrome): Selenium driver, Chrome preferred but not needed
        username (str): username
        password (str): password
        username_id (str, optional): HTML 'id' of username input. Defaults to "username".
        password_id (str, optional): HTML 'id' of passowrd input. Defaults to "password".
    """

    # Find username and password input fields
    username_input = driver.find_element(By.ID, username_id)
    password_input = driver.find_element(By.ID, password_id)

    # Fill in username and passsword (clear any autofilled)
    username_input.clear()
    username_input.send_keys(username)
    password_input.clear()
    password_input.send_keys(password)
    
    # Submit Form
    password_input.send_keys(Keys.RETURN)


def duo_2fa(driver: webdriver.Chrome):
    """Submit duo push two-factor authentification and
    remember authentification for 24hrs. You still must accept login
    on your default device

    Args:
        driver (webdriver.Chrome): Selenium driver, Chrome preferred but not needed
    """
    # Wait for 2fa to fully load, throws nosuchwindowexception when in headless mode
    WebDriverWait(driver, SHORT_TIMEOUT, ignored_exceptions=[NoSuchWindowException,]).until(EC.element_to_be_clickable((By.XPATH, DUO_PUSH_XPATH)))

    # Click remember me for 24 hours
    driver.find_element(By.NAME, DUO_REMEMBER_NAME).click()

    # Click duo push button
    driver.find_element(By.XPATH, DUO_PUSH_XPATH).click()


def add_class(driver: webdriver.Chrome, course=COURSE, section=SECTION):
    """Add a class to your registration

    Args:
        driver (webdriver.Chrome): Selenium driver, Chrome prefferred but not needed
        course (str, optional): Course to add. Defaults to COURSE.
        section (str, optional): Section of course to add. Defaults to SECTION.
    """
    WebDriverWait(driver, SHORT_TIMEOUT).until(EC.presence_of_element_located((By.NAME, COURSE_INPUT_NAME)))
    course_input = driver.find_element(By.NAME, COURSE_INPUT_NAME)
    course_input.send_keys(course)
    section_input = driver.find_element(By.XPATH, SECTION_INPUT_XPATH)
    section_input.send_keys(section)
    section_input.send_keys(Keys.RETURN)


def drop_class(driver:webdriver.Chrome):
    """Drop course from registration

    NOTE: Change DROP_BUTTON_XPATH and possibly DROP_CONFIRM_BUTTON_XPATH
    for your specific course

    Args:
        driver (webdriver.Chrome): Selenium driver, Chrome is preferred
    """
    # Wait for, then click drop button
    WebDriverWait(driver, SHORT_TIMEOUT).until(EC.element_to_be_clickable((By.XPATH, DROP_BUTTON_XPATH)))
    driver.find_element(By.XPATH, DROP_BUTTON_XPATH).click()

    # Wait for, then click confirmation of drop
    WebDriverWait(driver, SHORT_TIMEOUT).until(EC.element_to_be_clickable((
        By.XPATH, DROP_CONFIRM_BUTTON_XPATH)))
    confirm_button = driver.find_element(By.XPATH, DROP_CONFIRM_BUTTON_XPATH).click()
    

if __name__ == "__main__":
    main()
