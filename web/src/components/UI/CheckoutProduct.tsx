import { useEffect, useRef, useState } from "react";
import { useDispatch } from "react-redux";
import noImage from "../../assets/no_image.png";
import { ChangeCartProduct } from "../../redux/actions/CartActions";
import "../../styles/components/UI/CheckoutProduct.scss";
import { ProductPhotoType } from "../../types/productsRelatedTypes";
import { getItem } from "../../utils/getItem";
import { changeCartItem } from "../../utils/handleCart";
import DropDown from "./DropDown";
import { DEFAULT_DOOR_SIZES, CATEGORIES_WITH_DEFAULT_SIZES } from "../../constants/defaultSizes";
import { DEFAULT_DOOR_COLORS, CATEGORIES_WITH_DEFAULT_COLORS } from "../../constants/defaultColors";
import { DEFAULT_GLASS_COLORS, CATEGORIES_WITH_DEFAULT_GLASS_COLORS } from "../../constants/defaultGlassColors";
import { GLASS_PRESENCE_OPTIONS } from "../../constants/glassPresence";
import { ORIENTATION_OPTIONS, DEFAULT_ORIENTATION } from "../../constants/orientationOptions";

type CheckoutProductProps = {
    product: any;
    setValue?: any;
    deleteItem?: any;
    onQuantityChange?: any;
};

const debounce = (func: any, delay: any) => {
    let timeoutId: any;
    return (...args: any) => {
        if (timeoutId) {
            clearTimeout(timeoutId);
        }
        timeoutId = setTimeout(() => {
            func(...args);
        }, delay);
    };
};

const CheckoutProduct = ({
    product,
    setValue,
    deleteItem,
    onQuantityChange,
}: CheckoutProductProps) => {
    const [allowedSizes, setAllowedSizes] = useState<any>([]);
    const [availableColors, setAvailableColors] = useState<any>([]);
    const [availableGlassColors, setAvailableGlassColors] = useState<any>([]);
    const [productPhotos, setProductPhotos] = useState<ProductPhotoType[]>([]);
    const [currentPhoto, setCurrentPhoto] = useState<string>("");
    const [currentProduct, setCurrentProduct] = useState<any>({});
    const [currentProductChild, setCurrentProductChild] = useState<any>({});
    const [productQuantity, setProductQuantity] = useState<number>(1);
    const [previousQuantity, setPreviousQuantity] = useState<number>(1);
    const [currentPrice, setCurrentPrice] = useState<number>(0);
    const [totalValue, setTotalValue] = useState<number>(0);
    const isProductLoaded = useRef(false);
    const [withGlass, setWithGlass] = useState(false);
    const dispatch = useDispatch();

    // Обчислені значення для відображення в лейблах
    const selectedColor = availableColors.find((color: any) => color.id === product?.color_id);
    const selectedSize = allowedSizes.find((size: any) => size.id === product?.size_id);
    const selectedGlassColor = availableGlassColors.find((color: any) => color.id === product?.glass_color_id);
    const productHasGlass = currentProductChild?.have_glass;

    const getProductInfo = async (product: any) => {
        setCurrentProduct(product);
        setCurrentProductChild(product.product);
        setProductQuantity(product.quantity);
        setPreviousQuantity(product.quantity);
        setCurrentPrice(product.product.price);
        setTotalValue(product.total_price);
        setWithGlass(product?.with_glass || false);
    };

    useEffect(() => {
        const newProduct = { ...product };
        const currentProductClone = { ...currentProduct };

        delete newProduct.product;
        delete newProduct?.quantity;

        Object.keys(newProduct).forEach((newProductKey: string) => {
            if (
                newProduct[newProductKey] ===
                currentProductClone?.[newProductKey]
            ) {
                delete newProduct[newProductKey];
            }
        });

        if (JSON.stringify(newProduct) !== "{}") {
            getProductInfo(product);
        }
    }, [product]);

    useEffect(() => {
        if (!isProductLoaded.current) {
            isProductLoaded.current = true;
            return;
        }

        const setNewQuantity = () => {
            if (previousQuantity === productQuantity || productQuantity <= 1)
                return;

            setPreviousQuantity(productQuantity);
        };

        const delayDebounceFn = setTimeout(async () => {
            setNewQuantity();

            await changeCartItem(product.id, {
                quantity: productQuantity,
            }).then(async (res) => {
                setTotalValue(currentPrice * productQuantity);

                if (onQuantityChange) {
                    const currentData = res?.data || res;
                    await onQuantityChange({
                        currentObject: {
                            ...product,
                            quantity: productQuantity,
                        },
                        currentData,
                    });
                }
            });
        }, 300);

        return () => {
            clearTimeout(delayDebounceFn);
        };
    }, [productQuantity]);

    useEffect(() => {
        const loadProductData = async () => {
            if (currentProduct && currentProductChild?.category_id) {
                // Завантаження розмірів
                if (CATEGORIES_WITH_DEFAULT_SIZES.includes(currentProductChild.category_id)) {
                    setAllowedSizes(DEFAULT_DOOR_SIZES);
                } else {
                    let currentSizes: any = [];
                    const currentCategory = await getItem(
                        `api/v1/product/category/${currentProductChild.category_id}/`
                    );

                    const allowedSizesIds = currentCategory.allowed_sizes;

                    if (allowedSizesIds && allowedSizesIds.length > 0) {
                        for (const sizeId of allowedSizesIds) {
                            const sizeObject = await getItem(
                                "api/v1/product/size/$id",
                                {
                                    id: sizeId,
                                }
                            );

                            if (sizeObject) {
                                currentSizes.push(sizeObject);
                            }
                        }
                    }
                    setAllowedSizes(currentSizes);
                }

                // Завантаження кольорів
                if (availableColors.length === 0) {
                    if (CATEGORIES_WITH_DEFAULT_COLORS.includes(currentProductChild.category_id)) {
                        setAvailableColors(DEFAULT_DOOR_COLORS);
                    } else {
                        const colors = await getItem("api/v1/product/related/product_color/list/");
                        if (colors) setAvailableColors(colors);
                    }
                }

                // Завантаження кольорів скла
                if (availableGlassColors.length === 0) {
                    if (CATEGORIES_WITH_DEFAULT_GLASS_COLORS.includes(currentProductChild.category_id)) {
                        setAvailableGlassColors(DEFAULT_GLASS_COLORS);
                    } else {
                        const glassColors = await getItem("api/v1/product/related/product_glass_color/list/");
                        if (glassColors) setAvailableGlassColors(glassColors);
                    }
                }
            }
        };

        const setUpPhotos = () => {
            if (currentProductChild && currentProductChild.photos) {
                setProductPhotos(currentProductChild.photos);
                setCurrentPhoto(
                    currentProductChild.photos.find(
                        (photo: ProductPhotoType) => photo.is_main
                    )?.photo || ""
                );
            }
        };

        loadProductData();
        setUpPhotos();
    }, [currentProductChild]);

    const onChosen = async (fieldName: string, value: any, field: string) => {
    const newPhoto = productPhotos.find(
        (photo: any) => photo[field] === value
    );

    if (newPhoto) {
        setCurrentPhoto(newPhoto.photo);
    }

    if (product && product[fieldName] !== value) {
        if (setValue) {
            setValue(product.id, fieldName, value);
        }

        // Якщо відключили скло, скидаємо withGlass стейт
        if (fieldName === "with_glass" && !value) {
            setWithGlass(false);
            // Відправляємо тільки зміну with_glass
            await changeCartItem(product.id, { [fieldName]: value }).then(() =>
                dispatch(ChangeCartProduct({ ...product, [fieldName]: value }))
            );
            return;
        }

        await changeCartItem(product.id, { [fieldName]: value }).then(() =>
            dispatch(ChangeCartProduct({ ...product, [fieldName]: value }))
        );
    }
};

    const debouncedOnChosen = useRef(debounce(onChosen, 300)).current;

    return (
        currentProductChild && (
            <div className="checkout-product">
                <div className="checkout-product-inner-container">
                    <div className="checkout-product-image-container">
                        <img
                            className="checkout-product-cell"
                            src={currentPhoto || noImage}
                            alt={`door-${currentProductChild.price}-${currentProductChild.id}`}
                        />
                    </div>

                    <div className="checkout-product-cell main">
                        <div className="checkout-product-info">
                            <p className="small black bold">
                                {currentProductChild.name}
                            </p>
                            <p className="small black">
                                Арт. {currentProductChild.sku}
                            </p>
                        </div>

                        <div className="checkout-product-active">
                            <div className="checkout-product-count">
                                <div
                                    className="buy-products-pagination-button"
                                    onClick={() =>
                                        setProductQuantity((prev) =>
                                            prev > 1 ? prev - 1 : prev
                                        )
                                    }
                                >
                                    -
                                </div>

                                <p className="upper black pre-small">
                                    {productQuantity || 1} шт
                                </p>

                                <div
                                    className="buy-products-pagination-button"
                                    onClick={() =>
                                        setProductQuantity((prev) => prev + 1)
                                    }
                                >
                                    +
                                </div>
                            </div>

                            <div className="checkout-product-cell">
                                <p className="upper black bold mid">
                                    {totalValue} ₴{" "}
                                </p>

                                {deleteItem && (
                                    <button
                                        className="checkout-product-cell-delete"
                                        onClick={async () => {
                                            await deleteItem(product.id);
                                        }}
                                    >
                                        <svg
                                            viewBox="0 0 24 24"
                                            fill="none"
                                            xmlns="http://www.w3.org/2000/svg"
                                        >
                                            <path
                                                d="M3 3L6 6M6 6L10 10M6 6V18C6 19.6569 7.34315 21 9 21H15C16.6569 21 18 19.6569 18 18M6 6H4M10 10L14 14M10 10V17M14 14L18 18M14 14V17M18 18L21 21M18 6V12.3906M18 6H16M18 6H20M16 6L15.4558 4.36754C15.1836 3.55086 14.4193 3 13.5585 3H10.4415C9.94239 3 9.47572 3.18519 9.11861 3.5M16 6H11.6133"
                                                stroke="currentColor"
                                                strokeWidth="2"
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                            />
                                        </svg>
                                    </button>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="checkout-product-options checkout-product-cell">
                    {/* КОЛІР (з defaultColors) */}
                    {availableColors.length > 0 && (
                        <DropDown
                            borderless={false}
                            label={selectedColor ? selectedColor.name : "колір"}
                            field="color_id"
                            options={{
                                value: availableColors,
                                labelKey: "name",
                            }}
                            onChosen={(fieldName: string, value: any) =>
                                debouncedOnChosen(fieldName, value, "color_id")
                            }
                            defaultValue={{
                                defaultFieldName: "value",
                                defaultValue: product.color_id,
                            }}
                        />
                    )}

                    {/* РОЗМІР (з defaultSizes) */}
                    {allowedSizes && allowedSizes.length > 0 && (
                        <DropDown
                            borderless={false}
                            label={selectedSize ? selectedSize.dimensions : "розмір"}
                            field="size_id"
                            options={{
                                value: allowedSizes,
                                labelKey: "dimensions",
                            }}
                            onChosen={(fieldName: string, value: any) =>
                                debouncedOnChosen(fieldName, value, "size_id")
                            }
                            defaultValue={{
                                defaultFieldName: "value",
                                defaultValue: product.size_id,
                            }}
                        />
                    )}

                    {/* НАЯВНІСТЬ СКЛА (true/false) */}
                    {productHasGlass && (
                        <>
                            <DropDown
                                borderless={false}
                                label="наявність скла"
                                field="with_glass"
                                options={GLASS_PRESENCE_OPTIONS}
                                onChosen={(fieldName: string, value: any) => {
                                    debouncedOnChosen(fieldName, value, "with_glass");
                                    setWithGlass(value);
                                }}
                                defaultValue={{
                                    defaultFieldName: "value",
                                    defaultValue: product?.with_glass !== undefined ? product.with_glass : false,
                                }}
                            />

                            {/* КОЛІР СКЛА (якщо with_glass === true, показуємо defaultGlassColors) */}
                            {withGlass && availableGlassColors.length > 0 && (
                                <DropDown
                                    borderless={false}
                                    label={selectedGlassColor ? selectedGlassColor.name : "колір скла"}
                                    field="glass_color_id"
                                    options={{
                                        value: availableGlassColors,
                                        labelKey: "name",
                                    }}
                                    onChosen={(fieldName: string, value: any) =>
                                        debouncedOnChosen(fieldName, value, "glass_color_id")
                                    }
                                    defaultValue={{
                                        defaultFieldName: "value",
                                        defaultValue: product?.glass_color_id,
                                    }}
                                />
                            )}
                        </>
                    )}

                    {/* ОРІЄНТАЦІЯ (за замовчуванням "ліва") */}
                    {currentProductChild?.orientation_choice && (
                        <DropDown
                            borderless={false}
                            label="сторона петель"
                            field="orientation"
                            options={ORIENTATION_OPTIONS}
                            onChosen={(fieldName: string, value: any) =>
                                debouncedOnChosen(fieldName, value, "orientation")
                            }
                            defaultValue={{
                                defaultFieldName: "value",
                                defaultValue: product?.orientation || DEFAULT_ORIENTATION,
                            }}
                        />
                    )}

                    {/* МАТЕРІАЛ (опціонально) */}
                    {currentProductChild?.material_choice && (
                        <DropDown
                            borderless={false}
                            label="матеріал"
                            field="material"
                            options={[
                                {
                                    name: "Деревина",
                                    value: "wood",
                                },
                                {
                                    name: "МДФ",
                                    value: "mdf",
                                },
                            ]}
                            onChosen={(fieldName: string, value: any) =>
                                debouncedOnChosen(fieldName, value, "material")
                            }
                            defaultValue={{
                                defaultFieldName: "value",
                                defaultValue: product?.material,
                            }}
                        />
                    )}

                    {/* ТИП ЛИШТВИ (опціонально) */}
                    {currentProduct?.type_of_platband_choice && (
                        <DropDown
                            borderless={false}
                            label="тип лиштви"
                            field="type_of_platband"
                            options={[
                                {
                                    name: "Звичайний",
                                    value: "default",
                                },
                                {
                                    name: "Г-подібний",
                                    value: "L-shaped",
                                },
                            ]}
                            onChosen={(fieldName: string, value: any) =>
                                debouncedOnChosen(fieldName, value, "type_of_platband")
                            }
                            defaultValue={{
                                defaultFieldName: "value",
                                defaultValue: product?.type_of_platband,
                            }}
                        />
                    )}
                </div>
            </div>
        )
    );
};

export default CheckoutProduct;