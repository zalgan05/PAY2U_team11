# Backend сервиса для управления подписками в одном месте

## Описание проекта

PAY2U - это удобный и интуитивно понятный сервис, который позволяет пользователям эффективно управлять своими подписками. С помощью PAY2U вы можете легко подписываться на различные сервисы подписок, отслеживать активные подписки и управлять ими.

## API документация

Документацию по API в формате OpenAPI можно посмотреть [здесь](https://app.swaggerhub.com/apis/ZALGAN94_1/PAY2U/1.0.0)

## Локальный запуск сервиса в Docker 

Склонировать репозиторий на свой компьютер и перейти в корневую папку:
```python
git clone git@github.com:zalgan05/PAY2U_team11.git
cd backend
```

Создать в корневой папке файл .env с переменными окружения, необходимыми
для работы приложения.

Пример содержимого файла:
```
USE_SQLITE='false' # Указывает, будет ли использоваться база данных SQLite.
DEBUG='false' # Указывает, будет ли включен режим отладки.
ALLOWED_HOSTS='127.0.0.1,localhost,xx.xxx.xx.xxx,exampledomen.com'

VERSION_API='1' # Указывает версию API.
TEST_CELERY='false' # Указывает, используется ли тестовый режим Celery.
DEFAULT_REDIS_HOST='redis'

POSTGRES_USER=django_user
POSTGRES_PASSWORD=mysecretpassword
POSTGRES_DB=django
DB_HOST=db
DB_PORT=5432
```

Из корневой директории запустить сборку контейнеров с помощью
docker-compose:
```python
docker-compose up -d
```

Документация будет доступка по ссылке http://127.0.0.1/api/swagger/

Для попадания в админ-зону, перейдите по адресу http://127.0.0.1:8000/admin/.

Логин и пароль:
- login: admin
- password: admin

### Примеры запросов по всем эндпоинтам можно посмотреть в приложенной Postman коллекции
<details>
<summary> Как запустить </summary>
  
- Откройте Postman.

- Импортируйте коллекцию:

  * Нажмите на кнопку "Import" в верхнем левом углу интерфейса Postman.
  
  * Скопируйте туда ссылку:
    ```
    https://raw.githubusercontent.com/zalgan05/PAY2U_team11/develop/PAY2U.postman_collection.json
    ```
- После успешного импорта коллекции вы увидите ее в списке коллекций слева в боковой панели Postman.
</details>

## Технологии

* Python 3.9.10
* Django 3.2
* Django REST framework 3.13
* Nginx
* Docker
* Postgres 13.10
* Celery 5.3.6
* Redis 5.0.3

## Примечание

Frontend сервиса под это API можно посмотреть [тут](https://github.com/margo-yunanova/pay2u-subscriptions-hackathon) 
