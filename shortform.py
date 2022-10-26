import time
import os
import unicodedata
import re
import getpass


def error(package):
    print("Run:")
    print("pip install", package)


try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
except:
    error("selenium")
    print("Then:")
    print("(0) Install Chrome (if you have not already).")
    print("(1) Learn your Chrome version: Three dots > Help > About Google Chrome")
    print("(2) Find Chrome driver for this version at https://chromedriver.chromium.org/downloads, and download the one for your operating system.")
    print("(3) Extract the file content to somewhere mentioned in the environment variable named PATH.")
    exit(1)


try:
    from bs4 import BeautifulSoup
except:
    error("beautifulsoup4")
    exit(1)


def warning():
    print("Downloading the book summaries from Shortform may be an illegal action.")
    print("Please read Terms & Conditions carefully before proceeding.")
    input("Enter to continue.")
    print()


def login(driver):
    # Get the user data.
    print("Log in to Shortform.")
    email = input("Email: ")
    password = getpass.getpass("Password (It will not be stored!): ")
    print()

    # Open the page.
    login_page = "https://www.shortform.com/app/login"
    driver.get(login_page)
    bs = BeautifulSoup(driver.page_source, "html.parser")
    login_page_title = bs.find("title").text

    # Fill the form.
    driver.find_element(By.ID, "login_email").send_keys(email)
    driver.find_element(By.ID, "login_password").send_keys(password)
    driver.find_element(By.CLASS_NAME, "shortform-sign-up__submit").click()

    # Wait until the redirection.
    while True:
        time.sleep(1)
        bs = BeautifulSoup(driver.page_source, "html.parser")
        redirected_page_title = bs.find("title").text
        if login_page_title != redirected_page_title:
            break


def read_book_names(driver, books_path):
    def update_book_list(driver, books_path):
        def get_book_names():
            source = driver.page_source
            bs = BeautifulSoup(source, "html.parser")
            book_name_elements = bs.select(".card-text__name")
            book_names = [book_name_element.text for book_name_element in book_name_elements]
            return book_names

        url = "https://www.shortform.com/app/books"
        driver.get(url)
        time.sleep(5)

        prev_num_books = len(get_book_names())
        while True:
            for _ in range(100):
                driver.find_elements(By.CLASS_NAME, "keywords__input")[0].send_keys(Keys.PAGE_DOWN)
            time.sleep(1)
            num_books = len(get_book_names())
            if num_books == prev_num_books:
                break
            prev_num_books = num_books

        book_names = get_book_names()

        with open(books_path, "w") as f:
            f.write("\n".join(book_names) + "\n")

    to_be_updated = input("Update book list? (y/n) ").strip().lower() in ("y", "yes")
    if to_be_updated:
        update_book_list(driver, books_path)

    if not os.path.exists(books_path):
        print(f"ERROR: {books_path} does not exist!")
        exit(1)

    with open(books_path) as f:
        book_names = f.read().splitlines()

    return book_names


def download_book_summaries(driver, summary_dir, book_names):
    def download_book_summary(driver, book_name):
        def slugify(value, allow_unicode=False):
            # Patch.
            # Normally strengthsfinder 2.0 -> strengthsfinder-20
            # But we want strengthsfinder 2.0 -> strengthsfinder-2-0
            # Also for Emotional Intelligence 2.0, we want emotional-intelligence-2-0
            for major in range(1, 10):
                for minor in range(0, 10, 5):
                    value = value.replace(f"{major}.{minor}", f"{major}-{minor}")

            """
            Taken from https://github.com/django/django/blob/master/django/utils/text.py
            Convert to ASCII if "allow_unicode" is False. Convert spaces or repeated
            dashes to single dashes. Remove characters that aren't alphanumerics,
            underscores, or hyphens. Convert to lowercase. Also strip leading and
            trailing whitespace, dashes, and underscores.
            """
            value = str(value)
            if allow_unicode:
                value = unicodedata.normalize("NFKC", value)
            else:
                value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
            value = re.sub(r"[^\w\s-]", "", value.lower())
            return re.sub(r"[-\s]+", "-", value).strip("-_")

        slugified_book_name = slugify(book_name.strip().lower().replace("/", "-").replace("*", "-"))

        book_path = summary_dir + os.sep + slugified_book_name + ".html"
        if os.path.exists(book_path):
            print(book_path, "already exists.")
            return

        summary_url = f"https://www.shortform.com/app/book/{slugified_book_name}/1-page-summary"
        driver.get(summary_url)
        time.sleep(5)

        source = driver.page_source
        bs = BeautifulSoup(source, "html.parser")

        try:
            summary_element = bs.select_one(".sf-chapter")
        except:
            print(f"ERROR: No .sf-chapter on {summary_url}!")

        try:
            with open(book_path, "w") as f:
                f.write("<html>\n")
                f.write("<head>\n")
                f.write(f"<title>{book_name}</title>\n")
                f.write("</head>\n")
                f.write("<body>\n")
                f.write(str(summary_element) + "\n")
                f.write("</body>\n")
                f.write("</html>\n")
                print(book_path, "created.")
        except:
            if os.path.exists(books_path):
                os.remove(books_path)

    if not os.path.exists(summary_dir):
        os.mkdir(summary_dir)
    print(f"Book summaries will be downloaded into {summary_dir}.")

    for book_name in book_names:
        download_book_summary(driver, book_name)


if __name__ == "__main__":

    warning()

    main_dir = os.path.dirname(os.path.realpath(__file__))

    driver = webdriver.Chrome()
    login(driver)

    books_path = main_dir + os.sep + "books.txt"
    book_names = read_book_names(driver, books_path)

    summary_dir = main_dir + os.sep + "summaries"
    download_book_summaries(driver, summary_dir, book_names)

    driver.quit()
