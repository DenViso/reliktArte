import { useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { ChangeCartProduct, SetCart } from "../../redux/actions/CartActions";
import { paths } from "../../router/paths";
import "../../styles/components/UI/CartModal.scss";
import { deleteCartItem, getCart } from "../../utils/handleCart";
import Button from "./Button";
import CheckoutProduct from "./CheckoutProduct";
import Loader from "./Loader";

type CartModalProps = {
    closeModal: () => void;
};

const CartModal = ({ closeModal }: CartModalProps) => {
    const stopPropagation = (e: any) => e.stopPropagation();
    const navigate = useNavigate();
    const [itemsInfo, setItemsInfo] = useState<any>({});
    const [totalValue, setTotalValue] = useState(0);
    const [isLoaded, setIsLoaded] = useState(false);
    const dispatch = useDispatch();

    const products = useSelector(
        (state: any) => state.CartReducer.cartProducts
    );

    const setProducts = (cartProducts: any) => {
        dispatch(SetCart(cartProducts));
    };

    useEffect(() => {
        const setUpCart = async () => {
            setIsLoaded(false);

            const cart = await getCart().finally(() => {
                setIsLoaded(true);
            });

            if (cart) {
                setTotalValue(cart.total_value);
                setItemsInfo(cart.items);
                setProducts(cart.items.results);
            }
        };

        setUpCart();
    }, []);

    const deleteItem = async (id: number) => {
        setIsLoaded(false);

        const cart = await deleteCartItem(id).finally(() => [
            setIsLoaded(true),
        ]);

        if (cart) {
            setItemsInfo(cart.items);
            setProducts(cart.items.results);
        }
    };

    const onQuantityChange = (options: any) => {
        if (options?.currentObject) {
            dispatch(ChangeCartProduct(options.currentObject));
        }

        if (options?.data?.total_value !== undefined) {
            setTotalValue(options.data.total_value);
        }
    };

    return (
        <div className="cart-modal" onClick={closeModal}>
            <div className="cart-modal-inner-wrapper" onClick={stopPropagation}>
                <div className="cart-modal-inner" onClick={stopPropagation}>
                    {/* HEADER */}
                    <div className="cart-modal-inner-header">
                        <p className="upper black mid">корзина</p>
                        <svg
                            onClick={closeModal}
                            width="14"
                            height="14"
                            viewBox="0 0 14 14"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                        >
                            <path
                                d="M12.6575 1.34318L1.34375 12.6569M12.6575 12.6568L1.34375 1.34311"
                                stroke="currentColor"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                            />
                        </svg>
                    </div>

                    {/* PRODUCTS CONTAINER */}
                    <div className="cart-modal-inner-products-container">
                        {!isLoaded ? (
                            <Loader />
                        ) : (
                            <>
                                {/* ОПИС / ЗАГОЛОВОК */}
                                <div className="cart-modal-inner-description">
                                    <p className="black small">
                                        {products.length > 0
                                            ? "Ваше замовлення:"
                                            : "Тут поки що нічого немає ;("}
                                    </p>
                                </div>

                                {/* СПИСОК ПРОДУКТІВ */}
                                {products.length > 0 && (
                                    <div className="cart-modal-inner-products">
                                        {products.map((product: any) => (
                                            <CheckoutProduct
                                                key={product.id}
                                                product={product}
                                                setValue={() => false}
                                                deleteItem={deleteItem}
                                                onQuantityChange={onQuantityChange}
                                            />
                                        ))}
                                    </div>
                                )}
                            </>
                        )}
                    </div>

                    {/* BUTTONS */}
                    <div className="cart-modal-inner-buttons">
                        {/* ЦІНА І КНОПКА ОПЛАТИ */}
                        {products.length > 0 && isLoaded && (
                            <div className="cart-modal-inner-payment">
                                <p className="upper black bold big">{totalValue} ₴</p>
                                
                                <Button
                                    inversed={true}
                                    borderless={false}
                                    additionalClasses={["upper"]}
                                    onClickCallback={() => {
                                        closeModal();
                                        navigate(paths.checkout);
                                    }}
                                >
                                    перейти до сплати
                                </Button>
                            </div>
                        )}

                        {/* КНОПКА ПРОДОВЖИТИ ПОКУПКИ */}
                        <Button
                            colorScheme={"grey"}
                            onClickCallback={closeModal}
                            additionalClasses={["upper"]}
                        >
                            продовжити покупки
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default CartModal;