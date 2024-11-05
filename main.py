import sys

# Required for Streamlit
try:
  # Attempt to import pysqlite3
  __import__('pysqlite3')
  # Remap pysqlite3 to sqlite3 in sys.modules
  sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
except ImportError:
  pass

import ast
import configparser
from datetime import datetime
from time import sleep

import streamlit as st
import streamlit_antd_components as sac

from helper.analyse import analyse_choose
from helper.authentication import prompt_login
from helper.database import create_db, fetch_one
from helper.repository import repository_manage, repository_uploader
from helper.utility import get_secret_value


class ConfigHandler:
  def __init__(self):
    self.config = configparser.ConfigParser()
    self.config.read("config.ini")

  def get_value(self, section, key):
    value = self.config.get(section, key)
    try:
      # Convert string value to a Python data structure
      return ast.literal_eval(value)
    except (SyntaxError, ValueError):
      # If not a data structure, return the plain string
      return value


# Initialising config.ini
config_handler = ConfigHandler()
APPLICATION_VERSION = config_handler.get_value("application", "APPLICATION_VERSION")
APPLICATION_AUTHOR = config_handler.get_value("application", "APPLICATION_AUTHOR")
TITLE_DEFAULT = config_handler.get_value("title", "TITLE_DEFAULT")
TITLE_HOME = config_handler.get_value("title", "TITLE_HOME")
TITLE_REPOSITORY = config_handler.get_value("title", "TITLE_REPOSITORY")
TITLE_REPOSITORY_SETUP = config_handler.get_value("title", "TITLE_REPOSITORY_SETUP")
TITLE_REPOSITORY_MANAGE = config_handler.get_value("title", "TITLE_REPOSITORY_MANAGE")
TITLE_ANALYSE = config_handler.get_value("title", "TITLE_ANALYSE")
TITLE_ABOUT_US = config_handler.get_value("title", "TITLE_ABOUT_US")
TITLE_METHODOLOGY = config_handler.get_value("title", "TITLE_METHODOLOGY")
TITLE_DISCLAIMER = config_handler.get_value("title", "TITLE_DISCLAIMER")
TITLE_SIGN_OUT = config_handler.get_value("title", "TITLE_SIGN_OUT")
CONTENT_HOME = config_handler.get_value("content", "CONTENT_HOME")
CONTENT_ABOUT_US = config_handler.get_value("content", "CONTENT_ABOUT_US")
CONTENT_METHODOLOGY = config_handler.get_value("content", "CONTENT_METHODOLOGY")
CONTENT_DISCLAIMER = config_handler.get_value("content", "CONTENT_DISCLAIMER")

# Initialising .env / secrets
PASSWORD_TO_ENTER = get_secret_value("PASSWORD_TO_ENTER")
DATABASE_NAME = get_secret_value("DATABASE_NAME")
MAX_NUMBER_OF_FILES = get_secret_value("MAX_NUMBER_OF_FILES")

# Streamlit configuration
page_title = TITLE_DEFAULT
if "menu_option" in st.session_state and st.session_state.menu_option != TITLE_HOME:
  page_title = f"{st.session_state.menu_option} | {TITLE_DEFAULT}"

st.set_page_config(page_title=page_title, page_icon=":page_with_curl:", layout="wide")


def main():
  try:
    # st.write(st.session_state)

    if (
        "menu_option" not in st.session_state
        or st.session_state.menu_option == TITLE_HOME
    ):
      st.title(f":page_with_curl: {TITLE_DEFAULT}")
    else:
      st.title(f"{st.session_state.menu_option}")

    create_db()

    if not st.session_state.get("logged_in", False):
      if prompt_login(APPLICATION_AUTHOR, CONTENT_DISCLAIMER):
        st.success("Logged in successfully!")
        sleep(0.5)
        st.rerun()
      sac.tags(
          [sac.Tag(label=f"version=={APPLICATION_VERSION}")],
          align="start",
          color="green",
      )
    else:
      # Make side bar; More icons at https://icons.getbootstrap.com/
      with st.sidebar:
        st.session_state.menu_option = sac.menu(
            [
                sac.MenuItem(TITLE_HOME, icon="house"),
                sac.MenuItem(
                    TITLE_REPOSITORY,
                    icon="database",
                    children=[
                        sac.MenuItem(
                            TITLE_REPOSITORY_SETUP, icon="folder-plus"
                        ),
                        sac.MenuItem(
                            TITLE_REPOSITORY_MANAGE, icon="folder2-open"
                        ),
                    ],
                ),
                sac.MenuItem(TITLE_ANALYSE, icon="cpu"),
                sac.MenuItem(type="divider"),
                sac.MenuItem(TITLE_ABOUT_US, icon="info-circle"),
                sac.MenuItem(TITLE_METHODOLOGY, icon="lightbulb"),
                sac.MenuItem(TITLE_DISCLAIMER, icon="bell"),
                sac.MenuItem(TITLE_SIGN_OUT, icon="box-arrow-right"),
            ],
            open_all=True,
            key="key_sidebar",
        )

        sac.divider(
            label=APPLICATION_AUTHOR,
            icon=sac.BsIcon(name="person", size=20),
            variant="dotted",
        )

        data = fetch_one(
            "SELECT creation_date AS formatted_date FROM Configuration WHERE key=?",
            ["setup_on"],
        )
        if data:
          since_date_str = datetime.strptime(
              data[0], "%Y-%m-%d %H:%M:%S"
          ).strftime("%d %b %Y, %I:%M%p")
          sac.tags(
              [
                  sac.Tag(label=f"since=={since_date_str}"),
                  sac.Tag(label=f"version=={APPLICATION_VERSION}"),
              ],
              align="start",
              color="green",
          )

      if st.session_state.menu_option == TITLE_HOME:
        st.markdown(CONTENT_HOME)
      elif st.session_state.menu_option == TITLE_ABOUT_US:
        st.markdown(CONTENT_ABOUT_US)
      elif st.session_state.menu_option == TITLE_REPOSITORY_SETUP:
        repository_uploader(MAX_NUMBER_OF_FILES)
      elif st.session_state.menu_option == TITLE_REPOSITORY_MANAGE:
        repository_manage(TITLE_REPOSITORY_SETUP)
      elif st.session_state.menu_option == TITLE_ANALYSE:
        analyse_choose(TITLE_REPOSITORY_SETUP, CONTENT_DISCLAIMER)
      elif st.session_state.menu_option == TITLE_METHODOLOGY:
        st.write(CONTENT_METHODOLOGY)
        st.image("./images/methodology.png", caption="Methodology")
      elif st.session_state.menu_option == TITLE_DISCLAIMER:
        st.write(CONTENT_DISCLAIMER)
      elif st.session_state.menu_option == TITLE_SIGN_OUT:
        for key in st.session_state.keys():
          del st.session_state[key]
        st.info("Logged out successfully!")
        sleep(0.5)
        st.rerun()

  except Exception as e:
    st.exception(e)

  # End of main()


# Current py is run as the main program
if __name__ == "__main__":
  # os.environ.pop("xxx")
  main()
