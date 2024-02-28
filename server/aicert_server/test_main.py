from fastapi.testclient import TestClient
from .main import app


test_client = TestClient(app)


def test_read_main():
    response = test_client.post(
        "/build",
        json={
            "image": "python",
            "git_repo_url": "https://github.com/mithril-security/sample-test-repo.git",
            "command": "python3 main.py",
            "artifact_pattern": "output.txt",
        },
    )
    print(response.json())
    # Use assert False to get stdout/stderr
    # assert False
    # assert response.status_code == 200
    # assert response.json() == {"msg": "Hello World"}
