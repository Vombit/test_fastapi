# тестовое задание

# Что можно улучшить
- checkhealth для докера, 
- autotest, 
- routes разнести модули по файлам, 
- почистить код и вынести повторения, 
- добавить логгер,
- всё же сделать redis


# Функциональные возможности

- Регистрация и аутентификация пользователя (JWT, OAuth2.0);
- Создание и удаление реферального кода;
- ~~Получение реферального кода по email реферера~~;
- Регистрация по реферальному коду;
- Получение информации о рефералах пользователя;
- UI-документация (Swagger, ReDoc);

# Установка и запуск проекта

### Настройка переменных окружения

Создайте файл `.env` (шаблон `.env.expample`) в корневой директории и добавьте в него (__замените на свои данные__):

```env
SECRET_KEY=123qwerty

DATABASE_USER = postgres
DATABASE_PASSWORD = postgres
DATABASE_HOST = localhost
DATABASE_PORT = 5432
DATABASE_NAME = postgres

ACCESS_TOKEN_TIME = 30
```

### Установка зависимостей

#### **Без Docker**

```sh
python -m venv .venv
source .venv/bin/activate  # Для Linux
.venv\Scripts\activate  # Для Windows
pip install -r requirements.txt
```

#### **С использованием Docker**

```sh
docker-compose up --build
```

### Запуск сервиса

#### **Локальный запуск**

```sh
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### **С использованием Docker**

```sh
docker-compose up -d
```

API доступно по адресу: [localhost:8000](http://localhost:8000)

### UI-документация

После запуска сервиса доступны два интерфейса документации API:

- **Swagger UI**: [localhost:8000/docs](http://localhost:8000/docs)
- **ReDoc**: [localhost:8000/redoc](http://localhost:8000/redoc)




# Примеры запросов

### 1. Регистрация пользователя

#### **POST /register**

```json
{
  "email": "123@ex.com",
  "password": "123",
  "referral_code": "ABC123"  // Необязательно
}
```

### 2. Логин (получение JWT-токена)

#### **POST /token**

Использует `form-data`, где `username` — email, а `password` — пароль.

```sh
curl -X 'POST' \
  'http://localhost:8000/token' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=123@ex.com&password=123'
```

### 3. Создание реферального кода

#### **POST /referral-code**

```json
{
  "expiry": "2022-02-22T00:00:00"
}
```

### 4. Получение списка рефералов

#### **GET /referrals**

```sh
curl -X 'GET' 'http://localhost:8000/referrals' -H 'Authorization: Bearer YOUR_TOKEN'
```

---

### 3. Остановка и удаление контейнеров 

```sh
docker-compose down
```

---
