import os
from ninja import NinjaAPI, Schema
from typing import List, Optional
from django.shortcuts import get_object_or_404
from django.conf import settings
from .models import Category, Product, Cart, CartItem, Wishlist
from .gemini_service import generate_gemini_response
import stripe

api = NinjaAPI(
    title="PlantPot E-Commerce & AI API",
    version="2.0.0",
    description="REST API for the Plantpot luxury Next.js e-commerce storefront and Gemini AI assistant"
)

# -------------------------------------------------------------
# Schemas
# -------------------------------------------------------------

class CategoryOut(Schema):
    id: int
    name: str
    image_url: Optional[str] = None
    product_count: int

class ProductOut(Schema):
    id: int
    name: str
    category_id: int
    category_name: str
    description: str
    price: float
    formatted_price: str
    image_url: Optional[str] = None

class ChatIn(Schema):
    message: str

class ChatOut(Schema):
    reply: str

class CartItemIn(Schema):
    product_id: int
    quantity: int = 1

class CartItemOut(Schema):
    product_id: int
    name: str
    price: float
    formatted_price: str
    quantity: int
    subtotal: float
    formatted_subtotal: str
    image_url: Optional[str] = None

class CartOut(Schema):
    items: List[CartItemOut]
    total: float
    formatted_total: str
    item_count: int

class WishlistIn(Schema):
    product_id: int

class WishlistOut(Schema):
    product_id: int
    is_in_wishlist: bool
    wishlist_ids: List[int]

class CheckoutIn(Schema):
    product_ids: Optional[List[int]] = None

class CheckoutOut(Schema):
    checkout_url: Optional[str] = None
    message: str

# -------------------------------------------------------------
# Helpers
# -------------------------------------------------------------

def build_image_url(request, field):
    if not field:
        return None
    try:
        return request.build_absolute_uri(field.url)
    except Exception:
        return str(field)

# -------------------------------------------------------------
# Endpoints
# -------------------------------------------------------------

@api.get("/categories", response=List[CategoryOut], tags=["Catalog"])
def list_categories(request):
    """Retrieve all categories with their product counts and image URLs."""
    categories = Category.objects.all()
    results = []
    for cat in categories:
        img_url = build_image_url(request, cat.image)
        results.append(CategoryOut(
            id=cat.id,
            name=cat.name,
            image_url=img_url,
            product_count=cat.products.count()
        ))
    return results

@api.get("/products", response=List[ProductOut], tags=["Catalog"])
def list_products(request, category_id: Optional[int] = None):
    """Retrieve products, optionally filtered by category."""
    qs = Product.objects.select_related('category').all()
    if category_id:
        qs = qs.filter(category_id=category_id)
    
    results = []
    for p in qs:
        img_url = build_image_url(request, p.image)
        results.append(ProductOut(
            id=p.id,
            name=p.name,
            category_id=p.category.id if p.category else 0,
            category_name=p.category.name if p.category else "General",
            description=p.description or "",
            price=float(p.price),
            formatted_price=f"AED {float(p.price):,.2f}",
            image_url=img_url
        ))
    return results

@api.get("/products/{product_id}", response=ProductOut, tags=["Catalog"])
def get_product(request, product_id: int):
    """Retrieve details for a single product."""
    p = get_object_or_404(Product, id=product_id)
    img_url = build_image_url(request, p.image)
    return ProductOut(
        id=p.id,
        name=p.name,
        category_id=p.category.id if p.category else 0,
        category_name=p.category.name if p.category else "General",
        description=p.description or "",
        price=float(p.price),
        formatted_price=f"AED {float(p.price):,.2f}",
        image_url=img_url
    )

@api.post("/chat", response=ChatOut, tags=["AI Stylist"])
def chat_ai(request, payload: ChatIn):
    """Chat with the PlantPot AI Assistant, dynamically grounded on real inventory."""
    user_msg = payload.message.strip()
    if not user_msg:
        return ChatOut(reply="Please ask a question about our botanical planters, furniture, or styling.")
    
    reply_text = generate_gemini_response(user_msg)
    return ChatOut(reply=reply_text)

# -------------------------------------------------------------
# Session-Based Cart Operations (Supports Anonymous & Logged-in)
# -------------------------------------------------------------

def get_session_cart(request):
    """Retrieve or initialize cart dictionary from session."""
    return request.session.setdefault("cart_items", {})

@api.get("/cart", response=CartOut, tags=["Cart"])
def get_cart(request):
    """Retrieve current cart items, total amount, and count."""
    cart_dict = get_session_cart(request)
    items_out = []
    total = 0.0

    for pid_str, qty in cart_dict.items():
        try:
            product = Product.objects.get(id=int(pid_str))
            sub = float(product.price) * qty
            total += sub
            items_out.append(CartItemOut(
                product_id=product.id,
                name=product.name,
                price=float(product.price),
                formatted_price=f"AED {float(product.price):,.2f}",
                quantity=qty,
                subtotal=sub,
                formatted_subtotal=f"AED {sub:,.2f}",
                image_url=build_image_url(request, product.image)
            ))
        except Product.DoesNotExist:
            continue

    item_count = sum(cart_dict.values())
    return CartOut(
        items=items_out,
        total=total,
        formatted_total=f"AED {total:,.2f}",
        item_count=item_count
    )

@api.post("/cart/add", response=CartOut, tags=["Cart"])
def add_to_cart(request, payload: CartItemIn):
    """Add a product to the cart with specified quantity."""
    cart_dict = get_session_cart(request)
    pid_str = str(payload.product_id)
    cart_dict[pid_str] = cart_dict.get(pid_str, 0) + payload.quantity
    request.session["cart_items"] = cart_dict
    request.session.modified = True
    return get_cart(request)

@api.post("/cart/update", response=CartOut, tags=["Cart"])
def update_cart_quantity(request, payload: CartItemIn):
    """Update quantity of an item in the cart. If <= 0, item is removed."""
    cart_dict = get_session_cart(request)
    pid_str = str(payload.product_id)
    if payload.quantity <= 0:
        cart_dict.pop(pid_str, None)
    else:
        cart_dict[pid_str] = payload.quantity
    request.session["cart_items"] = cart_dict
    request.session.modified = True
    return get_cart(request)

@api.post("/cart/remove", response=CartOut, tags=["Cart"])
def remove_from_cart(request, payload: CartItemIn):
    """Remove a product entirely from the cart."""
    cart_dict = get_session_cart(request)
    cart_dict.pop(str(payload.product_id), None)
    request.session["cart_items"] = cart_dict
    request.session.modified = True
    return get_cart(request)

# -------------------------------------------------------------
# Wishlist
# -------------------------------------------------------------

@api.post("/wishlist/toggle", response=WishlistOut, tags=["Wishlist"])
def toggle_wishlist(request, payload: WishlistIn):
    """Toggle a product in the session wishlist."""
    wishlist = request.session.setdefault("wishlist_ids", [])
    pid = payload.product_id
    if pid in wishlist:
        wishlist.remove(pid)
        is_in = False
    else:
        wishlist.append(pid)
        is_in = True
    request.session["wishlist_ids"] = wishlist
    request.session.modified = True
    return WishlistOut(
        product_id=pid,
        is_in_wishlist=is_in,
        wishlist_ids=wishlist
    )

# -------------------------------------------------------------
# Stripe Checkout Session
# -------------------------------------------------------------

@api.post("/checkout", response=CheckoutOut, tags=["Checkout"])
def create_checkout(request, payload: CheckoutIn):
    """Create a Stripe checkout session for current cart items."""
    cart_dict = get_session_cart(request)
    if not cart_dict:
        return CheckoutOut(checkout_url=None, message="Cart is empty.")
    
    stripe_key = getattr(settings, 'STRIPE_SECRET_KEY', None) or os.getenv('STRIPE_SECRET_KEY')
    if not stripe_key:
        return CheckoutOut(
            checkout_url=None,
            message="Stripe is in demo mode. Please configure STRIPE_SECRET_KEY to complete live payment."
        )

    stripe.api_key = stripe_key
    line_items = []

    for pid_str, qty in cart_dict.items():
        try:
            prod = Product.objects.get(id=int(pid_str))
            line_items.append({
                'price_data': {
                    'currency': 'aed',
                    'unit_amount': int(prod.price * 100),
                    'product_data': {
                        'name': prod.name,
                        'description': prod.description[:100] if prod.description else "",
                    },
                },
                'quantity': qty,
            })
        except Product.DoesNotExist:
            continue

    if not line_items:
        return CheckoutOut(checkout_url=None, message="No valid items found in cart.")

    try:
        host = request.get_host()
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=f"http://localhost:3000/?checkout=success",
            cancel_url=f"http://localhost:3000/?checkout=cancel",
        )
        return CheckoutOut(checkout_url=session.url, message="Session created.")
    except Exception as e:
        return CheckoutOut(checkout_url=None, message=f"Stripe error: {str(e)}")
