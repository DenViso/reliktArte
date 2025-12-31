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
// import { getItem } from "../../../utils/getItem";
import { generateUrl } from "../../../utils/generateUrl";
import { addCartItem } from "../../../utils/handleCart";
import Button from "../../UI/Button";
import DropDown from "../../UI/DropDown";
import Loader from "../../UI/Loader";
import Path from "../../UI/Path";
import { log } from "console";

const ProductSection = () => {
  const { product_id } = useParams();
  const [product, setProduct] = useState<ProductType | undefined>(undefined);
  const [productPhotos, setProductPhotos] = useState<ProductPhotoType[]>([]);
  const [currentPhoto, setCurrentPhoto] = useState<string>("");
  const isLoaded = useSelector((state: any) => state.LoadReducer.isLoaded);
  const navigate = useNavigate();
  const { getValues, setValue, handleSubmit } = useForm();
  const [currentValues, setCurrentValues] = useState<any>({});
  const [allowedSizes, setAllowedSizes] = useState<any>([]);
  const dispatch = useDispatch();

  const setIsLoaded = (value: boolean) => {
    dispatch(SetIsLoaded(value));
  };

  useEffect(() => {
    const getCurrentProduct = async () => {
      try {
        if (!product) {
          const newProduct = await getItems("api/v1/product/$id", {
            id: product_id,
          });
          setProduct(newProduct);
        }
      } catch {
        navigate(paths.buy);
      }
    };
    getCurrentProduct();
  }, [product_id, navigate, product]);

  useEffect(() => {
    if (!product) return;
    setIsLoaded(false);

    const getAllowedSizes = async () => {
      if (product.category_id !== null) {
        if (allowedSizes.length < 1) {
          let currentSizes: any = [];
          const currentCategory = await getItems(
            `api/v1/product/category/${product.category_id}/`
          );
          const currentAllowedSizes = currentCategory.allowed_sizes;

          if (currentAllowedSizes?.length > 0) {
            for (const sizeId of currentAllowedSizes) {
              const sizeObject = await getItems("api/v1/product/size/$id", {
                id: sizeId,
              });
              if (sizeObject) currentSizes.push(sizeObject);
            }
          }
          setAllowedSizes(currentSizes);
        }
        setIsLoaded(true);
      }
    };

    const setUpPhotos = () => {
      if (product.photos && product.photos.length > 0) {
        setProductPhotos(product.photos);
        const mainPhoto =
          product.photos.find((p: ProductPhotoType) => p.is_main) ||
          product.photos[0];
        setCurrentPhoto(mainPhoto?.photo || "");
      }
    };

    getAllowedSizes();
    setUpPhotos();
  }, [product, allowedSizes.length, setIsLoaded]);

  const onChosen = (fieldName: string, value: any, field: string) => {
    const newPhoto = productPhotos.find((photo: any) => photo[field] === value);
    if (newPhoto) setCurrentPhoto(newPhoto.photo);
    setValue(fieldName, value);
    setCurrentValues(getValues());
  };

  const handleData = async (data: any) => {
    if (product) {
      data.product_id = product.id;
      if (data?.with_glass === false) delete data.glass_color_id;
      await addCartItem(data);
    }
    log(product_id, product);
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
              {/* ВИПРАВЛЕННЯ: Тепер src завжди отримує повний URL через generateUrl */}
              {/* <img
                key={currentPhoto}
                src={currentPhoto ? generateUrl(currentPhoto) : noImage}
                alt={product.name}
                onError={(e) => {
                  (e.target as HTMLImageElement).src = noImage;
                }}
              /> */}
              <img 
  src={currentPhoto ? `${generateUrl}${currentPhoto}` : noImage} 
  alt={product?.name} 
  className="product-info-main-image"
  onError={(e) => { (e.target as HTMLImageElement).src = noImage; }}
/>
              <p className="small black sku">Артикул: {product.sku}</p>
            </div>

            <div className="product-info-main-description">
              <div className="product-info-main-description-principal">
                <p className="upper black mid">{product.name}</p>
                <p className="black small">{product?.description?.text}</p>
              </div>

              <div className="product-info-main-description-button">
                <p className="upper black bold big">{product?.price} ₴</p>
                <Button
                  inversed={true}
                  additionalClasses={["upper"]}
                  onClickCallback={handleSubmit(handleData)}
                >
                  додати до кошику
                </Button>
              </div>

              <div className="product-info-main-description-options">
                <DropDown
                  label="колір"
                  field="color_id"
                  options={{
                    url: "api/v1/product/related/product_color/list/",
                    labelKey: "name",
                  }}
                  onChosen={(name, val) => onChosen(name, val, "color_id")}
                />

                {allowedSizes?.length > 0 && (
                  <DropDown
                    label="розмір"
                    field="size_id"
                    options={{ value: allowedSizes, labelKey: "dimensions" }}
                    onChosen={(name, val) => onChosen(name, val, "size_id")}
                  />
                )}

                {product?.have_glass && (
                  <>
                    <DropDown
                      label="наявність скла"
                      field="with_glass"
                      options={[
                        { name: "Присутнє", value: true },
                        { name: "Відсутнє", value: false },
                      ]}
                      onChosen={(name, val) =>
                        onChosen(name, val, "have_glass")
                      }
                    />
                    {currentValues.with_glass && (
                      <DropDown
                        label="колір скла"
                        field="glass_color_id"
                        options={{
                          url: "api/v1/product/related/product_glass_color/list/",
                          labelKey: "name",
                        }}
                        onChosen={(name, val) =>
                          onChosen(name, val, "color_id")
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
