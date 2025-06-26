import pytest
import json
import uuid
import datetime
from app import app, is_valid_movie_data, load_movies, save_movies
import os
import sys


# Фикстура для тестового клиента Flask
@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# Фикстура для временного файла данных
@pytest.fixture(autouse=True)
def setup_and_teardown(tmp_path, monkeypatch):
    # Временный файл для данных
    test_data_file = tmp_path / "test_movies.json"
    initial_data = {
        "existing_movie": {
            "id": "existing_movie",
            "title": "Начало",
            "director": "Кристофер Нолан",
            "year": 2010,
            "genre": "Фантастика",
            "rating": 8.8,
            "created_at": datetime.datetime.now().isoformat()
        }
    }

    # Сохраняем начальные данные
    with open(test_data_file, 'w', encoding='utf-8') as f:
        json.dump(initial_data, f, ensure_ascii=False)

    # Монтируем временный файл в приложении
    monkeypatch.setattr('app.DATA_FILE', str(test_data_file))
    monkeypatch.setattr('app.INITIAL_DATA_FILE', str(test_data_file))

    # Перезагружаем данные
    from app import load_movies, movies
    app.movies = load_movies()
    monkeypatch.setattr('app.movies', app.movies)

    yield


# Тесты для функции is_valid_movie_data
def test_valid_movie_data():
    valid_data = {
        'title': 'Интерстеллар',
        'director': 'Кристофер Нолан',
        'year': 2014,
        'genre': 'Фантастика',
        'rating': 8.6
    }
    assert is_valid_movie_data(valid_data) is True


def test_invalid_movie_data():
    invalid_data = {
        'title': '',
        'director': 'Кристофер Нолан',
        'year': 1700,  # Недопустимый год
        'genre': 'Фантастика',
        'rating': 15  # Недопустимый рейтинг
    }
    assert is_valid_movie_data(invalid_data) is False


# Тесты для GET /movies
def test_get_all_movies(client):
    response = client.get('/movies')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['title'] == 'Начало'


def test_get_all_movies_empty(client, monkeypatch):
    # Временно подменяем movies на пустой словарь
    monkeypatch.setattr('app.movies', {})
    response = client.get('/movies')
    assert response.status_code == 200
    assert json.loads(response.data) == []


# Тесты для GET /movies/recent
def test_get_recent_movies(client):
    response = client.get('/movies/recent')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 1
    assert data[0]['title'] == 'Начало'


def test_get_recent_movies_empty(client, monkeypatch):
    # Фильм с устаревшей датой
    old_date = (datetime.datetime.now() - datetime.timedelta(days=31)).isoformat()

    # Создаем тестовые данные
    test_movies = {
        'old_movie': {
            'id': 'old_movie',
            'title': 'Старый фильм',
            'director': 'Старый режиссер',
            'year': 2000,
            'genre': 'Старый жанр',
            'rating': 5.0,
            'created_at': old_date
        }
    }
    monkeypatch.setattr('app.movies', test_movies)

    response = client.get('/movies/recent')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert len(data) == 0


# Тесты для GET /movies/<id>
def test_get_movie_by_id(client):
    response = client.get('/movies/existing_movie')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['title'] == 'Начало'


def test_get_nonexistent_movie(client):
    response = client.get('/movies/non_existent_id')
    assert response.status_code == 404
    data = json.loads(response.data)
    assert data['error'] == "Фильм не найден"


# Тесты для POST /movies
def test_add_movie(client):
    new_movie = {
        'title': 'Матрица',
        'director': 'Лана Вачовски',
        'year': 1999,
        'genre': 'Фантастика',
        'rating': 8.7
    }
    response = client.post(
        '/movies',
        data=json.dumps(new_movie),
        content_type='application/json'
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'Матрица'
    assert 'id' in data


def test_add_invalid_movie(client):
    invalid_movie = {
        'title': 'Некорректный фильм',
        'director': 'Режиссер',
        'year': 1700,  # Недопустимый год
        'genre': 'Драма',
        'rating': 11  # Недопустимый рейтинг
    }
    response = client.post(
        '/movies',
        data=json.dumps(invalid_movie),
        content_type='application/json'
    )
    assert response.status_code == 400
    data = json.loads(response.data)
    assert 'error' in data


# Тесты для DELETE /movies/<id>
def test_delete_movie(client):
    response = client.delete('/movies/existing_movie')
    assert response.status_code == 204

    # Проверяем, что фильм действительно удален
    response = client.get('/movies/existing_movie')
    assert response.status_code == 404


def test_delete_nonexistent_movie(client):
    response = client.delete('/movies/non_existent_id')
    assert response.status_code == 404


# Дополнительный тест с полным русским описанием
def test_full_russian_movie(client):
    # Создаем фильм с полным русским описанием
    new_movie = {
        'title': 'Леон',
        'director': 'Люк Бессон',
        'year': 1994,
        'genre': 'Криминальная драма',
        'rating': 8.6
    }
    response = client.post(
        '/movies',
        data=json.dumps(new_movie),
        content_type='application/json'
    )
    assert response.status_code == 201
    data = json.loads(response.data)
    assert data['title'] == 'Леон'
    assert data['director'] == 'Люк Бессон'
    assert data['genre'] == 'Криминальная драма'

    # Проверяем получение фильма
    movie_id = data['id']
    response = client.get(f'/movies/{movie_id}')
    assert response.status_code == 200
    movie_data = json.loads(response.data)
    assert movie_data['title'] == 'Леон'

    # Проверяем удаление
    response = client.delete(f'/movies/{movie_id}')
    assert response.status_code == 204