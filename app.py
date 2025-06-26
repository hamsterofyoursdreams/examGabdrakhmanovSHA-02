from flask import Flask, Response, request
from flask_cors import CORS
import datetime
import uuid
import json
import os
import sys

app = Flask(__name__)
CORS(app)

# Принудительная настройка кодировки UTF-8
if sys.stdout.encoding != 'UTF-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        # Для старых версий Python
        import codecs

        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

# Отключаем ASCII-кодирование в JSON
app.config['JSON_AS_ASCII'] = False

# Конфигурация
DATA_FILE = 'movies.json'
INITIAL_DATA_FILE = 'initial_movies.json'


def load_movies():
    """Загрузить фильмы из JSON-файла с поддержкой кириллицы"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки данных: {str(e)}")
            return {}

    if os.path.exists(INITIAL_DATA_FILE):
        print("Обнаружен файл начальных данных. Создаю основную базу...")
        try:
            with open(INITIAL_DATA_FILE, 'r', encoding='utf-8') as f:
                initial_data = json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки начальных данных: {str(e)}")
            initial_data = {}

        save_movies(initial_data)
        return initial_data

    print("Создаю новую пустую базу фильмов...")
    save_movies({})
    return {}


def save_movies(movies_data):
    """Сохранить фильмы в JSON-файл с поддержкой кириллицы"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(movies_data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Ошибка сохранения данных: {str(e)}")


# Загружаем фильмы при запуске
movies = load_movies()
print(f"Загружено фильмов: {len(movies)}")


def is_valid_movie_data(data):
    """Проверка валидности данных фильма"""
    required_fields = ['title', 'director', 'year', 'genre', 'rating']
    if not all(field in data for field in required_fields):
        return False
    try:
        year = int(data['year'])
        rating = float(data['rating'])
        current_year = datetime.datetime.now().year
        if year < 1888 or year > current_year + 2:
            return False
        if rating < 0 or rating > 10:
            return False
    except (ValueError, TypeError):
        return False
    return True


# Кастомная функция для возврата JSON с UTF-8
def json_response(data, status=200):
    return Response(
        json.dumps(data, ensure_ascii=False),
        status=status,
        mimetype='application/json; charset=utf-8'
    )


# Эндпоинты
@app.route('/movies', methods=['GET'])
def get_all_movies():
    """Получить все фильмы"""
    return json_response(list(movies.values()))


@app.route('/movies/recent', methods=['GET'])
def get_recent_movies():
    """Получить недавно добавленные фильмы (за последние 30 дней)"""
    month_ago = datetime.datetime.now() - datetime.timedelta(days=30)
    recent = []

    for movie in movies.values():
        try:
            created_at = datetime.datetime.fromisoformat(movie['created_at'])
            if created_at >= month_ago:
                recent.append(movie)
        except (ValueError, KeyError):
            continue

    return json_response(recent)


@app.route('/movies/<string:movie_id>', methods=['GET'])
def get_movie(movie_id):
    """Получить фильм по ID"""
    movie = movies.get(movie_id)
    if not movie:
        return json_response({"error": "Фильм не найден"}, 404)
    return json_response(movie)


@app.route('/movies', methods=['POST'])
def add_movie():
    """Добавить новый фильм"""
    try:
        data = request.get_json()
    except Exception:
        return json_response({"error": "Неверный формат JSON"}, 400)

    if not data:
        return json_response({"error": "Не предоставлены данные"}, 400)

    if not is_valid_movie_data(data):
        return json_response({"error": "Некорректные данные фильма"}, 400)

    movie_id = str(uuid.uuid4())
    movie = {
        'id': movie_id,
        'title': data['title'],
        'director': data['director'],
        'year': int(data['year']),
        'genre': data['genre'],
        'rating': float(data['rating']),
        'created_at': datetime.datetime.now().isoformat()
    }

    movies[movie_id] = movie
    save_movies(movies)

    return json_response(movie, 201)


@app.route('/movies/<string:movie_id>', methods=['DELETE'])
def delete_movie(movie_id):
    """Удалить фильм по ID"""
    if movie_id not in movies:
        return json_response({"error": "Фильм не найден"}, 404)

    del movies[movie_id]
    save_movies(movies)

    return '', 204


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)