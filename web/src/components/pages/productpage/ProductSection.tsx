import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate, useParams } from "react-router-dom";
import noImage from "../../../assets/no_image.png";
import { SetIsLoaded } from "../../../redux/actions/LoadActions";
import { paths } from "../../../router/paths";
import "../../../styles/components/pages/productpage/ProductSection.scss";
import {
  ProductPhotoType,
  ProductType,
} from "../../../types/productsRelatedTypes";
import { getItems } from "../../../utils/getItems";
import { generateUrl } from "../../../utils/generateUrl";
import { addCartItem } from "../../../utils/handleCart";
import Button from "../../UI/Button";
import DropDown from "../../UI/DropDown";
import Loader from "../../UI/Loader";
import Path from "../../UI/Path";
import { DEFAULT_DOOR_SIZES, CATEGORIES_WITH_DEFAULT_SIZES } from "../../../constants/defaultSizes";
import { DEFAULT_DOOR_COLORS, CATEGORIES_WITH_DEFAULT_COLORS } from "../../../constants/defaultColors";
import { DEFAULT_GLASS_COLORS, CATEGORIES_WITH_DEFAULT_GLASS_COLORS } from "../../../constants/defaultGlassColors";

// Helper функція для визначення типу характеристики
const getDetailLabel = (value: string, index: number): string | null => {
  const lower = value.toLowerCase();
  
  if (index === 0 || lower.includes('клас')) return "Модельний ряд";
  
  if (index === 1 || 
      lower.includes('пвх') || 
      lower.includes('шпон') || 
      lower.includes('ламінат') || 
      lower.includes('горіх') || 
      lower.includes('дуб') || 
      lower.includes('ясен') ||
      lower.includes('вільха') ||
      lower.includes('сосна') ||
      lower.includes('бук')) return "Матеріал і колір";
  
  if (index === 2 || 
      lower.includes('полотно') || 
      lower.includes('двер') || 
      lower.includes('виріб')) return "Виріб";
  
  if (index === 3 || /\d+x\d+/.test(value) || /\d+×\d+/.test(value)) return null;
  
  if (index === 4 || 
      lower.includes('праве') || 
      lower.includes('ліве') ||
      lower.includes('правий') ||
      lower.includes('лівий')) return "Стандартна сторона відкривання";
  
  if (index === 5 || 
      lower.includes('сатин') || 
      lower.includes('матов') || 
      lower.includes('глянець') ||
      lower.includes('bronze') ||
      lower.includes('бронз')) return null;
  
  return null;
};

const isSize = (value: string): boolean => {
  return /\d+x\d+/.test(value) || /\d+×\d+/.test(value);
};

const isGlassColor = (value: string, index: number): boolean => {
  const lower = value.toLowerCase();
  return index === 5 || 
         lower.includes('сатин') || 
         lower.includes('матов') || 
         lower.includes('глянець') ||
         lower.includes('bronze') ||
         lower.includes('бронз') ||
         lower.includes('прозор') ||
         lower.includes('тонован');
};

const ProductSection = () => {
  const { product_id } = useParams();
  const [product, setProduct] = useState<ProductType | undefined>(undefined);
  const [productPhotos, setProductPhotos] = useState<ProductPhotoType[]>([]);
  const [currentPhoto, setCurrentPhoto] = useState<string>("");
  const isLoaded = useSelector((state: any) => state.LoadReducer.isLoaded);
  const navigate = useNavigate();
  const { getValues, setValue, handleSubmit, watch } = useForm();
  const [currentValues, setCurrentValues] = useState<any>({});
  const [allowedSizes, setAllowedSizes] = useState<any>([]);
  const [availableColors, setAvailableColors] = useState<any>([]);
  const [availableGlassColors, setAvailableGlassColors] = useState<any>([]); // ✅ ДОДАНО
  const dispatch = useDispatch();

  const setIsLoaded = (value: boolean) => {
    dispatch(SetIsLoaded(value));
  };

  // Відслідковування вибраних значень
  const selectedSizeId = watch('size_id');
  const selectedColorId = watch('color_id');
  const selectedGlassColorId = watch('glass_color_id'); // ✅ ДОДАНО
  const withGlass = watch('with_glass'); // ✅ ДОДАНО
  
  const selectedSize = allowedSizes.find((size: any) => size.id === selectedSizeId);
  const selectedColor = availableColors.find((color: any) => color.id === selectedColorId);
  const selectedGlassColor = availableGlassColors.find((color: any) => color.id === selectedGlassColorId); // ✅ ДОДАНО

  const productDetails = (product?.description as any)?.details as Array<{
    value: string;
  }> | undefined;

  const filteredDetails = productDetails?.filter((detail, index) => {
    const label = getDetailLabel(detail.value, index);
    return label !== null && !isSize(detail.value) && !isGlassColor(detail.value, index);
  });

  // Визначення наявності скла
  const hasGlassFromDetails = productDetails?.some((detail, index) => 
    isGlassColor(detail.value, index)
  );

  const productHasGlass = product?.have_glass || hasGlassFromDetails;

  // Діагностика
  useEffect(() => {
    if (product && productDetails) {
      console.log("🔍 DEBUG Glass:");
      console.log("  - product.have_glass:", product.have_glass);
      console.log("  - hasGlassFromDetails:", hasGlassFromDetails);
      console.log("  - productHasGlass:", productHasGlass);
      console.log("  - availableGlassColors:", availableGlassColors);
    }
  }, [product, productDetails, hasGlassFromDetails, productHasGlass, availableGlassColors]);

  // Завантаження продукту
  useEffect(() => {
    const getCurrentProduct = async () => {
      if (!product_id) return;

      try {
        console.log("🔄 Loading product:", product_id);
        const newProduct = await getItems(`api/v1/product/${product_id}`);
        console.log("✅ Product loaded:", newProduct);
        
        setProduct(newProduct);
      } catch (error) {
        console.error("❌ Error loading product:", error);
        navigate(paths.buy);
      }
    };

    if (!product) {
      getCurrentProduct();
    }
  }, [product_id, navigate, product]);

  // Завантаження додаткових даних
  useEffect(() => {
    if (!product) return;

    setIsLoaded(false);

    const loadProductData = async () => {
      try {
        // ✅ Завантаження кольорів дверей
        if (product.category_id && availableColors.length === 0) {
          if (CATEGORIES_WITH_DEFAULT_COLORS.includes(product.category_id)) {
            console.log("🎨 Using default door colors");
            setAvailableColors(DEFAULT_DOOR_COLORS);
          } else {
            console.log("🔄 Loading colors from API...");
            const colors = await getItems("api/v1/product/related/product_color/list");
            if (colors && colors.length > 0) {
              setAvailableColors(colors);
              console.log("✅ Colors loaded:", colors);
            }
          }
        }

        // ✅ ДОДАНО: Завантаження кольорів скла
        if (product.category_id && availableGlassColors.length === 0) {
          if (CATEGORIES_WITH_DEFAULT_GLASS_COLORS.includes(product.category_id)) {
            console.log("🔷 Using default glass colors");
            setAvailableGlassColors(DEFAULT_GLASS_COLORS);
          } else {
            console.log("🔄 Loading glass colors from API...");
            const glassColors = await getItems("api/v1/product/related/product_glass_color/list");
            if (glassColors && glassColors.length > 0) {
              setAvailableGlassColors(glassColors);
              console.log("✅ Glass colors loaded:", glassColors);
            }
          }
        }

        // Завантаження розмірів
        if (product.category_id && allowedSizes.length === 0) {
          if (CATEGORIES_WITH_DEFAULT_SIZES.includes(product.category_id)) {
            console.log("📏 Using default door sizes");
            setAllowedSizes(DEFAULT_DOOR_SIZES);
          } else {
            console.log("🔄 Loading category sizes from API...");
            const currentCategory = await getItems(
              `api/v1/product/category/${product.category_id}`
            );

            if (currentCategory?.allowed_sizes?.length > 0) {
              const sizePromises = currentCategory.allowed_sizes.map((sizeId: number) =>
                getItems(`api/v1/product/size/${sizeId}`)
              );
              const sizes = await Promise.all(sizePromises);
              const validSizes = sizes.filter(Boolean);
              setAllowedSizes(validSizes);
              console.log("✅ Sizes loaded:", validSizes);
            } else {
              console.warn("⚠️ No allowed sizes for category");
            }
          }
        }

        // Налаштування фото
        if (product.photos && product.photos.length > 0) {
          setProductPhotos(product.photos);
          const mainPhoto =
            product.photos.find((p: ProductPhotoType) => p.is_main) ||
            product.photos[0];

          const photoPath = mainPhoto?.photo || "";
          setCurrentPhoto(photoPath);
        }
      } catch (error) {
        console.error("❌ Error loading product data:", error);
      } finally {
        setIsLoaded(true);
      }
    };

    loadProductData();
  }, [product]);

  // Скидання початкових значень
  useEffect(() => {
    if (allowedSizes.length > 0 || availableColors.length > 0 || availableGlassColors.length > 0) {
      setValue('size_id', null);
      setValue('color_id', null);
      setValue('glass_color_id', null);
    }
  }, [allowedSizes, availableColors, availableGlassColors, setValue]);

  const onChosen = (fieldName: string, value: any, field: string) => {
    const newPhoto = productPhotos.find((photo: any) => photo[field] === value);
    if (newPhoto) {
      console.log("🔄 Changing photo to:", newPhoto.photo);
      setCurrentPhoto(newPhoto.photo);
    }
    setValue(fieldName, value);
    setCurrentValues(getValues());
  };

  const handlePhotoClick = (photoPath: string) => {
    setCurrentPhoto(photoPath);
  };

  const handleData = async (data: any) => {
    if (!product) return;

    data.product_id = product.id;
    if (data?.with_glass === false) {
      delete data.glass_color_id;
    }
    
    try {
      await addCartItem(data);
      console.log("✅ Item added to cart");
    } catch (error) {
      console.error("❌ Error adding to cart:", error);
    }
  };

  return (
    <div className="product-section">
      <Path
        segments={[
          { name: "головна", location: paths.main },
          { name: "продукція", location: paths.buy },
          { name: product?.sku || "", location: `${paths.buy}/${product_id}` },
        ]}
      />

      {!isLoaded || !product ? (
        <Loader />
      ) : (
        <div className="product-info">
          <div className="product-info-main">
            <div className="product-info-main-image">
              <img
                src={currentPhoto ? generateUrl(currentPhoto) : noImage}
                alt={product.name}
                className="main-photo"
                onError={(e) => {
                  (e.target as HTMLImageElement).src = noImage;
                }}
              />
              
              {productPhotos.length > 1 && (
                <div className="photo-gallery">
                  {productPhotos.map((photo, index) => (
                    <img
                      key={photo.id || index}
                      src={generateUrl(photo.photo)}
                      alt={`${product.name} - фото ${index + 1}`}
                      className={`thumbnail ${currentPhoto === photo.photo ? 'active' : ''}`}
                      onClick={() => handlePhotoClick(photo.photo)}
                      onError={(e) => {
                        (e.target as HTMLImageElement).src = noImage;
                      }}
                    />
                  ))}
                </div>
              )}

              <p className="small black sku">Артикул: {product.sku}</p>
            </div>

            <div className="product-info-main-description">
              <div className="product-info-main-description-principal">
                <p className="upper black mid">{product.name}</p>
                <p className="black small">{product?.description?.text}</p>

                {filteredDetails && filteredDetails.length > 0 && (
                  <div className="product-details">
                    <h3 className="details-title">Характеристики</h3>
                    <div className="details-list">
                      {filteredDetails.map((detail, index) => {
                        const label = getDetailLabel(detail.value, index);
                        if (!label) return null;
                        
                        return (
                          <div key={index} className="detail-item">
                            <span className="detail-label">{label}:</span>
                            <span className="detail-value">{detail.value}</span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>

              <div className="product-info-main-description-button">
                <p className="upper black bold big">{product.price} ₴</p>
                <Button
                  inversed={true}
                  additionalClasses={["upper"]}
                  onClickCallback={handleSubmit(handleData)}
                >
                  додати до кошику
                </Button>
              </div>

              <div className="product-info-main-description-options">
                {/* Колір дверей */}
                {availableColors.length > 0 && (
                  <DropDown
                    label={selectedColor ? selectedColor.name : "колір"}
                    field="color_id"
                    options={{ value: availableColors, labelKey: "name" }}
                    onChosen={(name: string, val: any) =>
                      onChosen(name, val, "color_id")
                    }
                  />
                )}

                {/* Розмір */}
                {allowedSizes?.length > 0 && (
                  <DropDown
                    label={selectedSize ? selectedSize.dimensions : "розмір"}
                    field="size_id"
                    options={{ value: allowedSizes, labelKey: "dimensions" }}
                    onChosen={(name: string, val: any) =>
                      onChosen(name, val, "size_id")
                    }
                  />
                )}

                {/* Наявність скла */}
                {productHasGlass && (
                  <>
                    <DropDown
                      label="наявність скла"
                      field="with_glass"
                      options={[
                        { name: "Присутнє", value: true },
                        { name: "Відсутнє", value: false },
                      ]}
                      onChosen={(name: string, val: any) =>
                        onChosen(name, val, "with_glass")
                      }
                    />
                    
                    {/* ✅ ОНОВЛЕНО: Колір скла з динамічним лейблом */}
                    {withGlass && availableGlassColors.length > 0 && (
                      <DropDown
                        label={selectedGlassColor ? selectedGlassColor.name : "колір скла"}
                        field="glass_color_id"
                        options={{ value: availableGlassColors, labelKey: "name" }}
                        onChosen={(name: string, val: any) =>
                          onChosen(name, val, "glass_color_id")
                        }
                      />
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProductSection;
