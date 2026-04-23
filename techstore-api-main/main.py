from fastapi import FastAPI, HTTPException, Query, Depends
from pydantic import BaseModel, field_validator, ConfigDict
from typing import Optional, List, Dict, Any
import databases
import sqlalchemy
import os
from functools import wraps

# ─── Configuration ────────────────────────────────────────────────────────────
class Config:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:dedinsaid0@localhost:5432/techstore"
    )
    
config = Config()

# ─── Database ─────────────────────────────────────────────────────────────────
database = databases.Database(config.database_url)
metadata = sqlalchemy.MetaData()

# ─── Tables ───────────────────────────────────────────────────────────────────
def create_table_schema() -> tuple:
    """Создаёт схему таблиц базы данных"""
    categories = sqlalchemy.Table(
        "categories",
        metadata,
        sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
        sqlalchemy.Column("name", sqlalchemy.String(255), nullable=False),
        sqlalchemy.Column("description", sqlalchemy.Text, nullable=True),
    )
    
    products = sqlalchemy.Table(
        "products",
        metadata,
        sqlalchemy.Column("id", sqlalchemy.Integer, primary_key=True, autoincrement=True),
        sqlalchemy.Column("name", sqlalchemy.String(255), nullable=False),
        sqlalchemy.Column("price", sqlalchemy.Numeric(10, 2), nullable=False),
        sqlalchemy.Column("stock", sqlalchemy.Integer, default=0),
        sqlalchemy.Column("category_id", sqlalchemy.Integer, sqlalchemy.ForeignKey("categories.id"), nullable=False),
    )
    
    return categories, products

categories_table, products_table = create_table_schema()
engine = sqlalchemy.create_engine(config.database_url)
metadata.create_all(engine)

# ─── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="TechStore API",
    description="REST API для интернет-магазина TechStore",
    version="1.0.0"
)

# ─── Schemas ──────────────────────────────────────────────────────────────────
class BaseValidator(BaseModel):
    """Базовый класс с общими валидаторами"""
    
    @staticmethod
    def validate_non_empty_string(value: str, field_name: str = "Поле") -> str:
        """Проверяет, что строка не пуста"""
        if not value or not value.strip():
            raise ValueError(f"{field_name} не может быть пустым")
        return value.strip()


class CategoryCreate(BaseValidator):
    name: str
    description: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return cls.validate_non_empty_string(v, "Название категории")


class CategoryOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    
    model_config = ConfigDict(from_attributes=True)


class ProductCreate(BaseValidator):
    name: str
    price: float
    stock: int = 0
    category_id: int
    
    model_config = ConfigDict(from_attributes=True)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        return cls.validate_non_empty_string(v, "Название товара")

    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        if v < 0:
            raise ValueError("Цена не может быть отрицательной")
        return v

    @field_validator("stock")
    @classmethod
    def validate_stock(cls, v):
        if v < 0:
            raise ValueError("Количество на складе не может быть отрицательным")
        return v


class ProductUpdate(BaseModel):
    price: Optional[float] = None
    stock: Optional[int] = None
    
    model_config = ConfigDict(from_attributes=True)

    @field_validator("price")
    @classmethod
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError("Цена не может быть отрицательной")
        return v

    @field_validator("stock")
    @classmethod
    def validate_stock(cls, v):
        if v is not None and v < 0:
            raise ValueError("Количество на складе не может быть отрицательным")
        return v


class ProductOut(BaseModel):
    id: int
    name: str
    price: float
    stock: int
    category_id: int
    
    model_config = ConfigDict(from_attributes=True)

# ─── Lifecycle ────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup():
    await database.connect()


@app.on_event("shutdown")
async def shutdown():
    await database.disconnect()


# ─── Helpers ──────────────────────────────────────────────────────────────────
async def fetch_resource(table: Any, resource_id: int, resource_name: str) -> Dict[str, Any]:
    """Получает ресурс из таблицы по ID"""
    resource = await database.fetch_one(
        table.select().where(table.c.id == resource_id)
    )
    if not resource:
        raise HTTPException(
            status_code=404,
            detail=f"{resource_name} с id={resource_id} не найден"
        )
    return dict(resource)


async def category_exists(category_id: int) -> None:
    """Проверяет существование категории"""
    await fetch_resource(categories_table, category_id, "Категория")


async def verify_category(category_id: int = Query(..., description="ID категории")) -> int:
    """Зависимость для проверки существования категории"""
    await category_exists(category_id)
    return category_id


def filter_none_values(data: Dict[str, Any]) -> Dict[str, Any]:
    """Фильтрует словарь, оставляя только непустые значения"""
    return {k: v for k, v in data.items() if v is not None}


def convert_rows_to_dicts(rows: List[Any]) -> List[Dict[str, Any]]:
    """Преобразует строки БД в словари"""
    return [dict(row) for row in rows]


# ─── CATEGORIES ───────────────────────────────────────────────────────────────

@app.post("/categories", response_model=CategoryOut, status_code=201, tags=["Categories"])
async def create_category(category: CategoryCreate) -> CategoryOut:
    """Создание новой категории"""
    query = categories_table.insert().values(
        name=category.name,
        description=category.description
    )
    cat_id = await database.execute(query)
    return CategoryOut(id=cat_id, name=category.name, description=category.description)


@app.get("/categories", response_model=List[CategoryOut], tags=["Categories"])
async def get_categories() -> List[CategoryOut]:
    """Получение всех категорий"""
    rows = await database.fetch_all(categories_table.select())
    return convert_rows_to_dicts(rows)


# ─── PRODUCTS ─────────────────────────────────────────────────────────────────

@app.get("/products", response_model=List[ProductOut], tags=["Products"])
async def get_products(
    category: Optional[int] = Query(None, description="ID категории для фильтрации")
) -> List[ProductOut]:
    """Список всех товаров. Опционально — фильтрация по category=ID"""
    query = products_table.select()
    if category is not None:
        query = query.where(products_table.c.category_id == category)
    rows = await database.fetch_all(query)
    return convert_rows_to_dicts(rows)


@app.post("/products", response_model=ProductOut, status_code=201, tags=["Products"])
async def create_product(product: ProductCreate) -> ProductOut:
    """Добавление нового товара с проверкой существования категории"""
    await category_exists(product.category_id)
    
    query = products_table.insert().values(
        name=product.name,
        price=product.price,
        stock=product.stock,
        category_id=product.category_id
    )
    prod_id = await database.execute(query)
    return ProductOut(
        id=prod_id,
        name=product.name,
        price=product.price,
        stock=product.stock,
        category_id=product.category_id
    )


@app.patch("/products/{id}", response_model=ProductOut, tags=["Products"])
async def update_product(id: int, data: ProductUpdate) -> ProductOut:
    """Обновление цены или количества товара"""
    existing = await fetch_resource(products_table, id, "Товар")
    
    updates = filter_none_values(data.model_dump())
    if not updates:
        raise HTTPException(status_code=400, detail="Нет данных для обновления")

    await database.execute(
        products_table.update().where(products_table.c.id == id).values(**updates)
    )

    updated = await fetch_resource(products_table, id, "Товар")
    return ProductOut(**updated)


@app.delete("/products/{id}", tags=["Products"])
async def delete_product(id: int) -> Dict[str, str]:
    """Удаление товара"""
    await fetch_resource(products_table, id, "Товар")
    
    await database.execute(
        products_table.delete().where(products_table.c.id == id)
    )
    return {"message": f"Товар с id={id} успешно удалён"}