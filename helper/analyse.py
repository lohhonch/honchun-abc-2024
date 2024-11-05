import pandas as pd
import streamlit as st
import streamlit_antd_components as sac
from langchain.chains import RetrievalQA
from langchain.document_loaders import PyPDFLoader, TextLoader, word_document
from langchain.prompts import PromptTemplate
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

import helper
from helper.database import fetch_all, fetch_one
from helper.llm import count_tokens
from helper.utility import save_blob_to_file

VECTOR_STORE_DIRECTORY = "./vector_store"


def analyse_choose(title_repository_setup, disclaimer):
  st.subheader("Choose one repository from below to analyse.")

  def get_selected_row_index():
    row_index = -1

    if (
        "key_analyse_choose_data" in st.session_state
        and st.session_state["key_analyse_choose_data"]["selection"]["rows"]
    ):
      row_index = st.session_state["key_analyse_choose_data"]["selection"][
          "rows"
      ][0]

    return row_index

  def step1():
    def handle_select_row():
      if "key_analyse_choose_data" not in st.session_state:
        return

      row_index = get_selected_row_index()
      if row_index >= 0:
        filtered_df = df.iloc[row_index]
        repository_id = filtered_df.loc[["repository_id"]][0]
        st.session_state["step2_disabled"] = False

        # store repository_id for Step 2 usage
        st.session_state["key_analyse_choose_data_repository_id"] = (
            repository_id
        )

      # End of handle_select_row()

    data = fetch_all("""
                      SELECT t1.name, t1.creation_date, t1.repository_id, (SELECT group_concat(t2.file_name, ', ') FROM Files t2 WHERE t2.repository_id = t1.repository_id)
                      FROM Repository t1
                      ORDER BY t1.creation_date DESC""")
    if data:
      df = pd.DataFrame(data).set_axis(
          ["name", "creation_date", "repository_id", "file_name"], axis="columns"
      )
    else:
      df = pd.DataFrame(
          columns=["name", "creation_date", "repository_id", "file_name"]
      )
      sac.alert(
          label="Repository is empty. Nothing to analyse.",
          description=f"👈 Click on *{title_repository_setup}* from Menu to proceed.",
          color="info",
          banner=False,
          icon=True,
          closable=False,
      )

    st.dataframe(
        df,
        column_config={
            "name": st.column_config.Column("Name", width="medium", required=True),
            "creation_date": st.column_config.DatetimeColumn(
                "Creation Date",
                width="medium",
                format="D MMM YYYY, h:mm a",
                required=True,
            ),
            "file_name": st.column_config.Column("Files", width="large"),
            "repository_id": None,
        },
        hide_index=True,
        selection_mode=["single-row"],
        on_select=handle_select_row,
        key="key_analyse_choose_data",
    )
    # End of step1()

  def step2():
    if "key_analyse_choose_data_repository_id" not in st.session_state:
      sac.alert(
          label="Oops",
          description="Something went wrong",
          color="error",
          banner=False,
          icon=True,
          closable=True,
      )
      return

    repository_id = st.session_state["key_analyse_choose_data_repository_id"]
    data = fetch_all(
        """
                     SELECT file_id, file_name
                     FROM Files
                     WHERE repository_id = ?
                     ORDER BY file_name ASC""",
        [repository_id],
    )

    if data:
      data_as_list = [f"{row[0]}: {row[1]}" for row in data]

      selected_files = sac.transfer(
          items=data_as_list,
          label=None,
          index=None,
          titles=["Associated files", "Selected files for analysis"],
          format_func="title",
          oneway=False,
          reload=True,
          align="center",
          search=True,
          width="100%",
          pagination=False,
          return_index=False,
          key="key_analyse_choose_data_step2_files",
      )

      st.warning(
          "Analysis process may take a while. Sit back and relax.",
          icon=":material/warning:",
      )
      expander = st.expander("DISCLAIMER", icon="🔔", expanded=False)
      expander.write(disclaimer)

      if selected_files:
        st.write("1. This will analyse the selected file(s) individually.")
        _, center1, _ = st.columns((3, 2, 3))
        if center1.button(
            "Analyse",
            icon=":material/memory:",
            type="primary",
            use_container_width=True,
            key="key_analyse_step2_btnAnalyse"
        ):
          with st.spinner("Analysis in progress ..."):
            files_dict = {
                int(file.split(":")[0].strip()): file.split(":")[1].strip()
                for file in selected_files
            }
            analyse_files(files_dict)

        sac.divider(label=None, variant="dotted", size="xs")

        st.write("2. Input a Clause to check if it conflicts with any of the clauses within the selected file(s).")
        st.text_area(label="Enter the Clause to check for conflict:", label_visibility="collapsed",
                     value="", placeholder="Enter the Clause to check for conflict", key="key_analyse_step2_clause")
        _, center2, _ = st.columns((3, 2, 3))
        if center2.button(
            "Send",
            icon=":material/send:",
            type="primary",
            use_container_width=True,
            key="key_analyse_step2_btnSend"
        ):
          with st.spinner("Analysis in progress ..."):
            files_dict = {
                int(file.split(":")[0].strip()): file.split(":")[1].strip()
                for file in selected_files
            }
            send_clause_to_check(files_dict)
    else:
      sac.alert(
          label="Oops",
          description="Something went wrong",
          color="error",
          banner=False,
          icon=True,
          closable=True,
      )

    # End of step2()

  def analyse_files(files_dict):
    collection_name = "honchun_abc_analyse_files"

    def split_docs(file_name, file_type, file_data):
      file_path = save_blob_to_file(file_data, file_name)

      if (
          file_type
          == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      ):
        # docx
        loader = word_document.Docx2txtLoader(file_path)
      elif file_type == "application/pdf":
        # pdf
        loader = PyPDFLoader(file_path)
      elif file_type == "text/plain":
        # txt
        loader = TextLoader(file_path)
      else:
        # Unrecognised type
        sac.alert(
            label="Oops",
            description="Something went wrong",
            color="error",
            banner=False,
            icon=True,
            closable=True,
        )
        return

      documents = loader.load()
      text_splitter = RecursiveCharacterTextSplitter(
          separators=["\n\n", "\n", " ", ""],
          chunk_size=500,
          chunk_overlap=50,
          length_function=count_tokens,
      )

      splitted_documents = text_splitter.split_documents(documents)
      return splitted_documents

      # End of split_docs()

    if not files_dict:
      return

    i = 1
    for file_id in files_dict:
      data = fetch_one(
          """
                      SELECT file_id, repository_id, file_name, type, size, data
                      FROM Files
                      WHERE file_id = ?""",
          [file_id],
      )
      file_name, file_type, file_data = data[2], data[3], data[5]
      splitted_documents = split_docs(file_name, file_type, file_data)

      # Delete vector store
      vector_store = Chroma(
          persist_directory=VECTOR_STORE_DIRECTORY, collection_name=collection_name
      )
      client = vector_store._client
      for collection in client.list_collections():
        client.delete_collection(collection.name)

      # Create the vector db
      vector_db = Chroma.from_documents(
          documents=splitted_documents,
          embedding=helper.llm.embeddings_model,
          collection_name=collection_name,  # one database can have multiple collections
          persist_directory=VECTOR_STORE_DIRECTORY,
      )

      query = """Tell me the conflicting clauses you know of."""

      # Build prompt
      template = """Use the following context to answer the question at the end. The provided context comes from a set of Tender documents. If you don't know the answer, simply state that you don't know — do not attempt to create an answer.

      Clauses refer to the one or more sentences within one bullet point of the entire context you know. You are to process everything before responding.

      **Role**: You are a Procurement Specialist.
      **Goal**: Determine whether any clauses within the provided Tender documents conflict with each other.
      **Backstory**: You are tasked with reviewing one or more Tender documents to identify any conflicting clauses.

      **Task**:
      1. Carefully review the clauses in all the documents.
      2. Identify conflicts by analyzing each clause as a whole and comparing against all clauses across the entire context before you conclude.
      3. If any conflicts are found, list the conflicting clauses in a table format. Include the following columns:
      - S/N
      - **Source 1**
      - **Source 2**
      - ...
      - **Explanation**
      Keep your Explanation short and concise.
      
      **Important**: Only include clauses that conflict with one another, otherwise, just answer "No conclict".

      Finish your response with "Thank you!" on a new line at the end.
      {context}
      Question: {question}
      Analytical Answer:"""
      QA_CHAIN_PROMPT = PromptTemplate.from_template(template)
      qa_chain = RetrievalQA.from_chain_type(
          helper.llm.llm,
          retriever=vector_db.as_retriever(),
          return_source_documents=True,  # Make inspection of document possible
          chain_type_kwargs={"prompt": QA_CHAIN_PROMPT},
      )
      llm_response = qa_chain.invoke(query)

      result = llm_response["result"]

      st.write(f"{i}. Result for *{file_name}*")
      i = i + 1
      st.write(result)
    # End of analyse_files()

  def send_clause_to_check(files_dict):
    collection_name = "honchun_abc_send_clause_to_check"

    def split_docs(file_name, file_type, file_data):
      file_path = save_blob_to_file(file_data, file_name)

      if (
          file_type
          == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
      ):
        # docx
        loader = word_document.Docx2txtLoader(file_path)
      elif file_type == "application/pdf":
        # pdf
        loader = PyPDFLoader(file_path)
      elif file_type == "text/plain":
        # txt
        loader = TextLoader(file_path)
      else:
        # Unrecognised type
        sac.alert(
            label="Oops",
            description="Something went wrong",
            color="error",
            banner=False,
            icon=True,
            closable=True,
        )
        return

      documents = loader.load()
      text_splitter = RecursiveCharacterTextSplitter(
          separators=["\n\n", "\n", " ", ""],
          chunk_size=500,
          chunk_overlap=50,
          length_function=count_tokens,
      )

      splitted_documents = text_splitter.split_documents(documents)
      return splitted_documents

      # End of split_docs()

    if not files_dict:
      return

    i = 1
    for file_id in files_dict:
      data = fetch_one(
          """
                      SELECT file_id, repository_id, file_name, type, size, data
                      FROM Files
                      WHERE file_id = ?""",
          [file_id],
      )
      file_name, file_type, file_data = data[2], data[3], data[5]
      splitted_documents = split_docs(file_name, file_type, file_data)

      # Delete vector store
      vector_store = Chroma(
          persist_directory=VECTOR_STORE_DIRECTORY, collection_name=collection_name
      )
      client = vector_store._client
      for collection in client.list_collections():
        client.delete_collection(collection.name)

      # Create the vector db
      vector_db = Chroma.from_documents(
          documents=splitted_documents,
          embedding=helper.llm.embeddings_model,
          collection_name=collection_name,  # one database can have multiple collections
          persist_directory=VECTOR_STORE_DIRECTORY,
      )

      query = st.session_state["key_analyse_step2_clause"]

      # Build prompt
      template = """Use the following context to answer the question at the end. The provided context comes from a set of Tender documents. If you don't know the answer, simply state that you don't know — do not attempt to create an answer.

      Clauses refer to the one or more sentences within one bullet point of the entire context you know.

      **Role**: You are a Procurement Specialist.
      **Goal**: Determine whether clause provided to you within <PromptXYZ> conflicts with the clauses you know.
      **Backstory**: You are tasked to review if clause provided to you within <Prompt> conflicts with the clauses you know.

      **Task**:
      1. Carefully review the clauses in all the documents to build up your knowledge.
      2. Read the <PromptXYZ> and check against what you know to determine if it conflicts with what you know.
      3. If any conflicts are found, list the conflicting clauses in a table format. Include the following columns:
      - S/N
      - **Clause with conflicts**
      - **Explanation**
      Keep your Explanation short and concise.
      
      **Important**: Only include clauses that conflict with one another, otherwise, just answer "No conclict".

      Finish your response with "Thank you!" on a new line at the end.
      {context}

      Remember that you are only going to take in question within below Prompt:
      <Prompt>
      {question}
      </Prompt>
      Analytical Answer:"""
      QA_CHAIN_PROMPT = PromptTemplate.from_template(template)
      qa_chain = RetrievalQA.from_chain_type(
          helper.llm.llm,
          retriever=vector_db.as_retriever(),
          return_source_documents=True,  # Make inspection of document possible
          chain_type_kwargs={"prompt": QA_CHAIN_PROMPT},
      )
      llm_response = qa_chain.invoke(query)

      result = llm_response["result"]

      st.write(f"{i}. Result for *{file_name}*")
      i = i + 1
      st.write(result)
    # End of send_clause_to_check()

  steps_options = sac.steps(
      items=[
          sac.StepsItem(title="step 1", subtitle="choose one repository"),
          sac.StepsItem(
              title="step 2",
              subtitle="pick files to include",
              disabled=(get_selected_row_index() == -1),
          ),
      ],
      key="key_analyse_choose_data_steps",
  )

  if steps_options == "step 1":
    step1()
  elif steps_options == "step 2":
    step2()
  # End of analyse_choose()
