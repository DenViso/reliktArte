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

// Swiper imports
import { Swiper, SwiperSlide } from 'swiper/react';
import { Pagination } from 'swiper/modules';
import 'swiper/css';
import 'swiper/css/pagination';

const getDetailLabel = (value: string, index: number, allDetails: Array<{ value: string }>): string | null => {
  const lower = value.toLowerCase().trim();
  if (/\d+\s*[xх×]\s*\d+/i.test(value)) return null;
  const glassKeywords = ['сатин', 'матов', 'глянець', 'bronze', 'бронз', 'прозор', 'тонован', 'графіт', 'димч'];
  const isLikelyGlassColor = glassKeywords.some(kw => lower.includes(kw));
  if (isLikelyGlassColor && index >= allDetails.length - 2) return null;
  if (lower.includes('клас') || lower.includes('арт') || lower.includes('модель') || index === 0) return "Модельний ряд";
  if (lower.includes('пвх') || lower.includes('шпон') || lower.includes('ламінат') || lower.includes('екошпон') || lower.includes('мдф') ||
    lower.includes('горіх') || lower.includes('дуб') || lower.includes('ясен') || lower.includes('вільха') || lower.includes('сосна') || lower.includes('бук') || lower.includes('венге') || lower.includes('махагон') ||
    lower.includes('білий') || lower.includes('чорний') || lower.includes('сірий') || lower.includes('коричнев')) return "Матеріал і колір";
  if (lower.includes('полотно') || lower.includes('двер') || lower.includes('виріб') || lower.includes('рама') || lower.includes('короб')) return "Тип виробу";
  if (lower.includes('праве') || lower.includes('ліве') || lower.includes('правий') || lower.includes('лівий') || lower.includes('правост') || lower.includes('лівост')) return "Стандартна сторона відкривання";
  if (!isLikelyGlassColor && (lower.includes('глянц') || lower.includes('текстур') || lower.includes('рельєф') || lower.includes('шагрен'))) return "Оздоблення";
  if (lower.includes('суцільн') || lower.includes('філенч') || lower.includes('каркас') || lower.includes('щитов')) return "Конструкція";
  return null;
};

const isSize = (value: string): boolean => /\d+\s*[xх×]\s*\d+/i.test(value);

const isGlassColor = (value: string, index: number, allDetails: Array<{ value: string }>): boolean => {
  const lower = value.toLowerCase();
  const keywords = ['сатин', 'матов', 'глянець', 'bronze', 'бронз', 'прозор', 'тонован', 'графіт', 'димч'];
  return keywords.some(kw => lower.includes(kw)) && index >= allDetails.length - 2;
};

const ProductSection = () => {
  const { product_id } = useParams();
  const [product, setProduct] = useState<ProductType | undefined>(undefined);
  const [productPhotos, setProductPhotos] = useState<ProductPhotoType[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0); // Керуємо індексом замість стрінги
  const isLoaded = useSelector((state: any) => state.LoadReducer.isLoaded);
  const navigate = useNavigate();
  const { setValue, handleSubmit, watch } = useForm();
  const [allowedSizes, setAllowedSizes] = useState<any>([]);
  const [availableColors, setAvailableColors] = useState<any>([]);
  const [availableGlassColors, setAvailableGlassColors] = useState<any>([]);
  const dispatch = useDispatch();

  const [isZoomOpen, setIsZoomOpen] = useState(false);
  const [zoomIndex, setZoomIndex] = useState(0);

  const setIsLoaded = (value: boolean) => { dispatch(SetIsLoaded(value)); };

  const selectedSizeId = watch('size_id');
  const selectedColorId = watch('color_id');
  const selectedGlassColorId = watch('glass_color_id');
  const withGlass = watch('with_glass');

  const selectedSize = allowedSizes.find((size: any) => size.id === selectedSizeId);
  const selectedColor = availableColors.find((color: any) => color.id === selectedColorId);
  const selectedGlassColor = availableGlassColors.find((color: any) => color.id === selectedGlassColorId);

  const productDetails = (product?.description as any)?.details as Array<{ value: string }> | undefined;

  const filteredDetails = productDetails?.map((detail, originalIndex) => ({
    detail, originalIndex
  })).filter(({ detail, originalIndex }) => {
    if (!productDetails) return false;
    const label = getDetailLabel(detail.value, originalIndex, productDetails);
    return label !== null && !isSize(detail.value) && !isGlassColor(detail.value, originalIndex, productDetails);
  });

  const hasGlassFromDetails = productDetails?.some((detail, index) => isGlassColor(detail.value, index, productDetails));
  const productHasGlass = product?.have_glass || hasGlassFromDetails;

  useEffect(() => {
    const getCurrentProduct = async () => {
      if (!product_id) return;
      try {
        const newProduct = await getItems(`api/v1/product/${product_id}`);
        setProduct(newProduct);
      } catch (error) { navigate(paths.buy); }
    };
    if (!product) getCurrentProduct();
  }, [product_id, navigate, product]);

  useEffect(() => {
    if (!product) return;
    setIsLoaded(false);
    const loadProductData = async () => {
      try {
        if (product.category_id && availableColors.length === 0) {
          if (CATEGORIES_WITH_DEFAULT_COLORS.includes(product.category_id)) setAvailableColors(DEFAULT_DOOR_COLORS);
          else {
            const colors = await getItems("api/v1/product/related/product_color/list");
            if (colors) setAvailableColors(colors);
          }
        }
        if (product.category_id && availableGlassColors.length === 0) {
          if (CATEGORIES_WITH_DEFAULT_GLASS_COLORS.includes(product.category_id)) setAvailableGlassColors(DEFAULT_GLASS_COLORS);
          else {
            const glassColors = await getItems("api/v1/product/related/product_glass_color/list");
            if (glassColors) setAvailableGlassColors(glassColors);
          }
        }
        if (product.category_id && allowedSizes.length === 0) {
          if (CATEGORIES_WITH_DEFAULT_SIZES.includes(product.category_id)) setAllowedSizes(DEFAULT_DOOR_SIZES);
          else {
            const currentCategory = await getItems(`api/v1/product/category/${product.category_id}`);
            if (currentCategory?.allowed_sizes?.length > 0) {
              const sizes = await Promise.all(currentCategory.allowed_sizes.map((id: number) => getItems(`api/v1/product/size/${id}`)));
              setAllowedSizes(sizes.filter(Boolean));
            }
          }
        }
        if (product.photos && product.photos.length > 0) {
          setProductPhotos(product.photos);
          const mainIdx = product.photos.findIndex((p: ProductPhotoType) => p.is_main);
          setCurrentIndex(mainIdx >= 0 ? mainIdx : 0);
        }
      } finally { setIsLoaded(true); }
    };
    loadProductData();
  }, [product]);

  useEffect(() => {
    if (allowedSizes.length > 0 || availableColors.length > 0 || availableGlassColors.length > 0) {
      setValue('size_id', null);
      setValue('color_id', null);
      setValue('glass_color_id', null);
    }
  }, [allowedSizes, availableColors, availableGlassColors, setValue]);

  const onChosen = (fieldName: string, value: any) => {
    // Тільки встановлюємо значення форми, не намагаємось змінити фото по ID кольору/розміру
    setValue(fieldName, value);
  };

  const handleData = async (data: any) => {
    if (!product) return;
    data.product_id = product.id;
    if (data?.with_glass === false) delete data.glass_color_id;
    await addCartItem(data);
  };

  const openZoom = (index: number) => {
    setZoomIndex(index);
    setIsZoomOpen(true);
    document.body.style.overflow = "hidden";
  };

  const closeZoom = () => {
    setIsZoomOpen(false);
    document.body.style.overflow = "auto";
  };

  const nextZoom = () => setZoomIndex((prev) => (prev + 1) % productPhotos.length);
  const prevZoom = () => setZoomIndex((prev) => (prev - 1 + productPhotos.length) % productPhotos.length);

  return (
    <div className="product-section">
      <Path segments={[{ name: "головна", location: paths.main }, { name: "продукція", location: paths.buy }, { name: product?.sku || "", location: `${paths.buy}/${product_id}` }]} />

      {!isLoaded || !product ? <Loader /> : (
        <div className="product-info">
          <div className="product-info-main">
            <div className="product-info-main-image">
              
              {/* Desktop Gallery */}
              <div className="desktop-gallery">
                <img
                  src={productPhotos[currentIndex] ? generateUrl(productPhotos[currentIndex].photo) : noImage}
                  alt={product.name}
                  className="main-photo"
                  onClick={() => openZoom(currentIndex)}
                />
                {productPhotos.length > 1 && (
                  <div className="photo-gallery">
                    {productPhotos.map((photo, index) => (
                      <img
                        key={photo.id || index}
                        src={generateUrl(photo.photo)}
                        className={`thumbnail ${index === currentIndex ? 'active' : ''}`}
                        onClick={() => setCurrentIndex(index)}
                        alt="thumbnail"
                      />
                    ))}
                  </div>
                )}
              </div>

              {/* Mobile Gallery (Swiper) */}
              <div className="mobile-gallery">
                <Swiper
                  modules={[Pagination]}
                  pagination={{ clickable: true }}
                  spaceBetween={10}
                  slidesPerView={1}
                  className="product-swiper"
                  onSlideChange={(swiper:any) => setCurrentIndex(swiper.activeIndex)}
                >
                  {productPhotos.map((photo, index) => (
                    <SwiperSlide key={photo.id || index}>
                      <img 
                        src={generateUrl(photo.photo)} 
                        alt="product" 
                        className="swiper-image"
                        onError={(e) => { (e.target as HTMLImageElement).src = noImage; }}
                      />
                    </SwiperSlide>
                  ))}
                </Swiper>
              </div>

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
                      {filteredDetails.map(({ detail, originalIndex }, idx) => (
                        <div key={idx} className="detail-item">
                          <span className="detail-label">{getDetailLabel(detail.value, originalIndex, productDetails!)}:</span>
                          <span className="detail-value">{detail.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              <div className="product-info-main-description-button">
                <p className="upper black bold big">{product.price} ₴</p>
                <Button inversed={true} additionalClasses={["upper"]} onClickCallback={handleSubmit(handleData)}>додати до кошику</Button>
              </div>

              <div className="product-info-main-description-options">
                {availableColors.length > 0 && (
                  <DropDown label={selectedColor ? selectedColor.name : "колір"} field="color_id" options={{ value: availableColors, labelKey: "name" }} onChosen={(n, v) => onChosen(n, v)} />
                )}
                {allowedSizes?.length > 0 && (
                  <DropDown label={selectedSize ? selectedSize.dimensions : "розмір"} field="size_id" options={{ value: allowedSizes, labelKey: "dimensions" }} onChosen={(n, v) => onChosen(n, v)} />
                )}
                {productHasGlass && (
                  <>
                    <DropDown label="наявність скла" field="with_glass" options={[{ name: "Присутнє", value: true }, { name: "Відсутнє", value: false }]} onChosen={(n, v) => onChosen(n, v)} />
                    {withGlass && availableGlassColors.length > 0 && (
                      <DropDown label={selectedGlassColor ? selectedGlassColor.name : "колір скла"} field="glass_color_id" options={{ value: availableGlassColors, labelKey: "name" }} onChosen={(n, v) => onChosen(n, v)} />
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {isZoomOpen && (
        <div className="zoom-modal" onClick={closeZoom}>
          <div className="zoom-content" onClick={(e) => e.stopPropagation()}>
            <button className="zoom-close" onClick={closeZoom}>&times;</button>
            <button className="zoom-prev" onClick={prevZoom}>&#10094;</button>
            <img src={generateUrl(productPhotos[zoomIndex]?.photo || "")} alt="Zoom" className="zoom-image" />
            <button className="zoom-next" onClick={nextZoom}>&#10095;</button>
          </div>
        </div>
      )}
    </div>
  );
};

export default ProductSection;