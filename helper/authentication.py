import hmac

import streamlit as st
import streamlit_antd_components as sac

from helper.utility import get_secret_value


def prompt_login(author, disclaimer):
  """Returns `True` if user had entered the correct password"""

  def password_entered():
    # Checks if a password entered by the user is correct
    if hmac.compare_digest(st.session_state["password_to_enter"], get_secret_value("PASSWORD_TO_ENTER")):
      st.session_state["logged_in"] = True
      del st.session_state["password_to_enter"]  # Never store the password
    else:
      st.session_state["logged_in"] = False

  # Return True if the password is validated
  if st.session_state.get("logged_in", False):
    return True

  st.info("1. You are required to read and agree to the following *Disclaimer*.", icon=":material/check_circle:")

  expander = st.expander("DISCLAIMER", icon="🔔", expanded=False)
  expander.write(disclaimer)

  agree = st.checkbox("I have read and agree to the disclaimer.")

  if agree:
    st.info("2. Key in *Password* to continue.", icon="🔑")

    # Show input for password
    st.text_input("Password", type="password", placeholder="Enter Password", label_visibility="collapsed",
                  on_change=password_entered, key="password_to_enter")
    if "logged_in" in st.session_state and not st.session_state["logged_in"]:
      st.error("😕 Password incorrect")

  sac.divider(label=author, icon=sac.BsIcon(name='person', size=20), variant='dotted')

  return False
