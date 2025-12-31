from typing import Optional

from pydantic import BaseModel

from ..core.schemas import MainSchema, BaseListSchema
from .enums import (
    ProductPhotoDepEnum,
    ProductOrientationEnum,
    ProductTypeOfPlatbandEnum,
)


class ProductDescriptionConstruction(BaseModel):
    main_text: Optional[str] = None
    additional_text: Optional[str] = None


class ProductDescriptionFinishingCovering(BaseModel):
    text: Optional[str] = None
    advantages: list[str] = []


class ProductDescriptionFinishing(BaseModel):
    covering: ProductDescriptionFinishingCovering


class ProductDescription(BaseModel):
    construction: Optional[ProductDescriptionConstruction] = None
    advantages: list[str] = []
    finishing: Optional[ProductDescriptionFinishing] = None
    text: Optional[str] = None


class ProductPhotoCreate(BaseModel):
    product_id: int
    photo: str
    is_main: Optional[bool] = False
    dependency: ProductPhotoDepEnum
    with_glass: Optional[bool] = None
    orientation: Optional[ProductOrientationEnum] = None
    type_of_platband: Optional[ProductTypeOfPlatbandEnum] = None
    color_id: Optional[int] = None
    size_id: Optional[int] = None
    glass_color_id: Optional[int] = None


class ProductPhotoUpdate(BaseModel):
    is_main: Optional[bool] = None
    dependency: Optional[ProductPhotoDepEnum] = None
    with_glass: Optional[bool] = None
    orientation: Optional[ProductOrientationEnum] = None
    type_of_platband: Optional[ProductTypeOfPlatbandEnum] = None
    color_id: Optional[int] = None
    size_id: Optional[int] = None
    glass_color_id: Optional[int] = None


class ProductPhotoShow(MainSchema):
    id: int
    product_id: int
    photo: str
    is_main: bool
    dependency: ProductPhotoDepEnum
    with_glass: Optional[bool] = None
    orientation: Optional[ProductOrientationEnum] = None
    type_of_platband: Optional[ProductTypeOfPlatbandEnum] = None
    color_id: Optional[int] = None
    size_id: Optional[int] = None


class ProductCreate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    price: int
    description: Optional[ProductDescription] = None
    have_glass: Optional[bool] = False
    material_choice: Optional[bool] = False
    type_of_platband_choice: Optional[bool] = False
    orientation_choice: Optional[bool] = False
    category_id: int
    covering_id: Optional[int] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    price: Optional[int] = None
    description: Optional[ProductDescription] = None
    have_glass: Optional[bool] = None
    material_choice: Optional[bool] = None
    type_of_platband_choice: Optional[bool] = None
    orientation_choice: Optional[bool] = None
    category_id: Optional[int] = None
    covering_id: Optional[int] = None


class ProductShow(MainSchema):
    id: int
    name: Optional[str] = None
    sku: Optional[str] = None
    price: int
    description: Optional[ProductDescription] = None
    have_glass: bool | None = False
    material_choice: bool
    type_of_platband_choice: bool
    orientation_choice: bool
    category_id: int
    covering_id: Optional[int] = None
    photos: list[ProductPhotoShow] = []


class CategoryCreate(BaseModel):
    name: str
    is_glass_available: bool
    have_material_choice: bool
    have_orientation_choice: bool
    have_type_of_platband_choice: bool
    priority: Optional[int] = None
    allowed_sizes: Optional[list[int]] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    is_glass_available: Optional[bool] = None
    have_material_choice: Optional[bool] = None
    have_orientation_choice: Optional[bool] = None
    have_type_of_platband_choice: Optional[bool] = None
    priority: Optional[int] = None
    allowed_sizes: Optional[list[int]] = None


class CategoryShow(MainSchema):
    id: int
    name: str
    is_glass_available: bool
    have_material_choice: bool
    have_orientation_choice: bool
    have_type_of_platband_choice: bool
    priority: Optional[int] = None
    allowed_sizes: list[int] = []


class ProductSizeCreate(BaseModel):
    height: int
    width: int
    thickness: int


class ProductSizeUpdate(BaseModel):
    height: Optional[int] = None
    width: Optional[int] = None
    thickness: Optional[int] = None


class ProductSizeShow(MainSchema):
    id: int
    height: int
    width: int
    thickness: int
    dimensions: str


class ProductRelCreate(BaseModel):
    name: str
    active: bool


class ProductRelUpdate(BaseModel):
    name: Optional[str] = None
    active: Optional[bool] = None


class ProductRelShow(MainSchema):
    id: int
    name: str
    active: bool


ProductListSchema = BaseListSchema[ProductShow]
ProductSizeListSchema = BaseListSchema[ProductSizeShow]
ProductRelListSchema = BaseListSchema[ProductRelShow]
CategoryListSchema = BaseListSchema[CategoryShow]
