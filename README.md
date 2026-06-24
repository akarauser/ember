# ember
Local search engine

Ember works as your local search engine for "md", "txt", "docx", "pdf" files. Once you have added your files to the database, you can search over them whenever you want.

## Overview
- Multiple files: You can add multiple files to database
- Reranking: System rerank retrieved documents based on your query for better output
- Offline usage: You can use application offline if you have started it with internet once.
- Single search: By using the `Filter` section, you can search over only certain file with a keyword.

## Installation
You can install application by following:

```
git clone https://github.com/akarauser/ember.git
cd ember

docker build .
```

## Usage
You can attach *data* and *models* folders to volumes to be able use persistant.

After you run your container, go to http://localhost:8501/

(*It can take time for the first time.*)

Choose your files to add database. After it's completed you can use `Query` section to search.

##  License
MIT License (see LICENSE)

## Project Structure
```
ember
├── LICENSE
├── README.md
├── uv.lock
├── tests
│   ├── test_main.py
│   └── __init__.py
├── .gitignore
├── .dockerignore
├── src
│   └── ember
│       ├── __init__.py
│       ├── utils
│       │   ├── __init__.py
│       │   ├── tools.py
│       │   └── logger.py
│       └── main.py
├── .streamlit
│   └── config.toml
├── .python-version
├── pyproject.toml
└── Dockerfile