import os
import time

from dotenv import load_dotenv
import streamlit as st

TEMP_FOLDER = os.path.join(os.getcwd(), "temp")

if not os.path.exists(TEMP_FOLDER):
  os.makedirs(TEMP_FOLDER)


def get_secret_value(k):
  """
  Return value of secret key.
  Take from .streamlit/secrets.toml, followed by .env
  """

  load_dotenv(".env")

  ret = ""
  if st.secrets.load_if_toml_exists() and k in st.secrets:
    ret = st.secrets[k]
  else:
    if k in os.environ:
      ret = os.getenv(k)

  return ret


def save_blob_to_file(blob_data, file_name):
  remove_old_files(TEMP_FOLDER)

  file_path = os.path.join(TEMP_FOLDER, file_name)
  try:
    with open(file_path, 'wb') as file:
      file.write(blob_data)
      return file_path
  except Exception:
    return ""


def remove_old_files(folder_path, age_in_minutes=1):
  # Convert age from minutes to seconds
  age_in_seconds = age_in_minutes * 60
  current_time = time.time()

  try:
    for filename in os.listdir(folder_path):
      file_path = os.path.join(folder_path, filename)

      # Check if it is a file (not a directory)
      if os.path.isfile(file_path):
        # Get the file's last modified time
        file_mod_time = os.path.getmtime(file_path)

        # Calculate the file age
        file_age = current_time - file_mod_time

        # Delete the file if it is older than the specified age
        if file_age > age_in_seconds:
          os.remove(file_path)
  except Exception:
    pass
