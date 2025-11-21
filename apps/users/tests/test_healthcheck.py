import pytest
from django.urls import reverse
from rest_framework.test import APIClient

client = APIClient()

@pytest.mark.django_db
def test_healthcheck():
    response = client.get("/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
