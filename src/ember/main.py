import time
from pathlib import Path
from tempfile import TemporaryDirectory

import streamlit as st

from ember.utils.logger import JsonLogger
from ember.utils.tools import ingest_document, retrieve_results

logger = JsonLogger.setup_logger()


st.set_page_config("Ember", page_icon="🔥", layout="wide")

if "keyword" not in st.session_state:
    st.session_state["keyword"] = ""


with st.sidebar:
    with st.container(border=False, gap="medium"):
        st.markdown("# Welcome to Ember!")
        st.markdown(
            "You can upload your files and search over them even if you are offline!"
        )
    with st.container(border=False, gap="medium"):
        st.session_state["keyword"] = (
            st.text_input(
                "Filter",
                placeholder="Keyword",
            )
            .lower()
            .strip()
        )
        with st.form(
            "upload-form", clear_on_submit=True, enter_to_submit=False, border=False
        ):
            uploaded_files = st.file_uploader(
                "Upload your files",
                type=["md", "txt", "docx", "pdf"],
                accept_multiple_files=True,
            )
            submitted = st.form_submit_button("Submit")

            if submitted and uploaded_files is not None:
                with TemporaryDirectory(dir=str(Path(__file__).parents[0])) as tmp_dir:
                    for file in uploaded_files:
                        with st.spinner(f"{file.name}"):
                            file_path = Path(tmp_dir, file.name)
                            with open(file_path, "wb") as f:
                                f.write(file.getvalue())
                            ingest_document(str(file_path))
                        file_info = st.info(f"{file.name} processed.")
                        time.sleep(2)
                        file_info.empty()
                        logger.log(20, f"{file.name} processed.")


with st.container(border=False):
    query = st.text_input("Query", label_visibility="hidden", placeholder="Type...")

    if query:
        if st.session_state["keyword"]:
            results = retrieve_results(query=query, filter=st.session_state["keyword"])
        else:
            results = retrieve_results(query)
        st.code(
            results,
            height=500,
            language="markdown",
            wrap_lines=True,
        )
