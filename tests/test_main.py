import requests


def test_server_status():
    assert requests.get("http://127.0.0.1:8501").status_code == 200
