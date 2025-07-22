## Django instructions.

---

#### Запустить сервер:

`python manage.py runserver`

#### Создать миграции:

`python manage.py makemigrations`

#### Применить миграции:

`python manage.py migrate`

#### Создать новое приложение:

`python manage.py startapp [название приложения]`

После создания приложения не забыть:
- Добавить приложение в `INSTALLED_APPS`
```python
# settings.py

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'django_filters',
    'drf_yasg',

    'api_v1',
    '[название приложения]',
]
```
- Создать `urls.py` в новом приложении:
```python
from django.urls import path

urlpatterns = [
    path('', ...),
]
```
- Подключить маршруты к корневому `urls.py`:
```python
# urls.py
from django.urls import path, include
from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api_v1/', include('figma_api.api_v1.urls')),
    path('', include('путь к urls.py нового приложения'))
]
```
