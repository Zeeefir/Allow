# TechStore REST API

## Структура проекта
```
techstore/
├── main.py
├── requirements.txt
├── TechStore.postman_collection.json
└── README.md
```

---

## Запуск

### 1. Создай БД в pgAdmin
Правая кнопка на Databases → Create → Database → назови: `techstore` → Save

### 2. Установи зависимости
```powershell
pip install -r requirements.txt
```

### 3. Запусти сервер
```powershell
$env:DATABASE_URL="postgresql://postgres:dedinsaid0@localhost:5432/techstore"
uvicorn main:app --reload
```

### 4. Swagger документация
Открой: **http://localhost:8000/docs**

---

## Все эндпоинты

### CATEGORIES
| Метод | URL | Описание |
|-------|-----|----------|
| POST  | /categories | Создать категорию |
| GET   | /categories | Получить все категории |

### PRODUCTS
| Метод | URL | Описание |
|-------|-----|----------|
| GET    | /products | Все товары |
| GET    | /products?category=1 | Фильтр по категории |
| POST   | /products | Добавить товар |
| PATCH  | /products/{id} | Обновить цену/количество |
| DELETE | /products/{id} | Удалить товар |

---

## Примеры запросов для Postman

### POST /categories
```json
{
  "name": "Смартфоны",
  "description": "Мобильные телефоны и смартфоны"
}
```

### POST /products
```json
{
  "name": "iPhone 15 Pro",
  "price": 89999.99,
  "stock": 25,
  "category_id": 1
}
```

### PATCH /products/1
```json
{
  "price": 79999.99,
  "stock": 30
}
```

---

## Обработка ошибок

| Ситуация | Код | Ответ |
|----------|-----|-------|
| Товар не найден | 404 | `{"detail": "Товар с id=5 не найден"}` |
| Категория не найдена | 404 | `{"detail": "Категория с id=99 не найдена"}` |
| Отрицательная цена | 422 | `{"detail": "Цена не может быть отрицательной"}` |
| Пустое название | 422 | `{"detail": "Название товара не может быть пустым"}` |

---

## Импорт коллекции в Postman
1. Открой Postman
2. Import → Upload Files → выбери `TechStore.postman_collection.json`
3. Все запросы уже готовы!