import json
import random
import requests
import shlex
import subprocess
import stripe
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_GET, require_POST
from django.http import HttpResponseRedirect, JsonResponse
from .forms import EditProfileForm
from django.views.decorators.csrf import csrf_exempt
from .models import UserProfile

from .models import Category, Product, Wishlist, Cart, CartItem
from .forms import RegisterForm
from .gemini_service import generate_gemini_response

# -----------------------------
# 🔐 OTP LOGIN SYSTEM
# -----------------------------

otp_store = {}

def generate_otp():
    return str(random.randint(100000, 999999))

def alt_login_view(request):
    if request.method == 'POST':
        contact = request.POST.get('contact', '').strip()

        if 'otp' in request.POST:
            entered_otp = request.POST['otp']
            actual_otp = otp_store.get(contact)

            if entered_otp == actual_otp:
                user, _ = User.objects.get_or_create(username=contact)
                login(request, user)
                request.session['show_party_popper'] = True  # 🎉 set flag for confetti
                messages.success(request, "Logged in successfully!")
                otp_store.pop(contact, None)
                return redirect('/')
            else:
                messages.error(request, "Invalid OTP.")
                return render(request, 'plantapp/alt_login.html', {'step': 'otp', 'contact': contact})

        if not contact:
            messages.error(request, "Please enter a valid phone or email.")
            return redirect('alt_login')

        otp = generate_otp()
        otp_store[contact] = otp
        print(f"🔐 OTP for {contact}: {otp}")
        messages.success(request, f"OTP sent to {contact} (Check Console)")
        return render(request, 'plantapp/alt_login.html', {'step': 'otp', 'contact': contact})

    return render(request, 'plantapp/alt_login.html')


# -----------------------------
# 🔐 AUTH VIEWS
# -----------------------------

def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        confirm = request.POST.get('confirm_password')

        if password != confirm:
            messages.error(request, "Passwords do not match")
            return redirect('register')

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect('register')

        User.objects.create_user(username=username, password=password)
        messages.success(request, "Account created. Please log in.")
        return redirect('login')

    return render(request, 'plantapp/register.html')

def login_view(request):
    if request.method == 'POST':
        user = authenticate(request,
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )
        if user:
            login(request, user)
            messages.success(request, f"Welcome back, {user.username}!")
            return redirect('/')
        else:
            messages.error(request, "Invalid credentials")
            return redirect('login')

    return render(request, 'plantapp/login.html')

def logout_view(request):
    logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('login')


# -----------------------------
# 🏠 HOME & PRODUCT VIEWS
# -----------------------------

def home(request):
    categories = Category.objects.all()
    show_party_popper = request.session.pop('show_party_popper', False) 
    return render(request, 'plantapp/home.html', {
        'categories': categories,
          'is_home': True,
          'show_party_popper': show_party_popper
          })

def category_products_view(request, category_id=None):
    categories = Category.objects.all().prefetch_related('products')
    search_query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'default')

    selected_category = None
    if category_id:
        selected_category = get_object_or_404(Category, id=category_id)
        products = Product.objects.filter(category=selected_category)
    else:
        products = Product.objects.all()

    if search_query:
        products = products.filter(name__icontains=search_query) | products.filter(description__icontains=search_query)

    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name_asc':
        products = products.order_by('name')

    wishlist_products = []
    if request.user.is_authenticated:
        wishlist_products = list(Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True))

    category_list = []
    for cat in categories:
        category_list.append({
            'id': cat.id,
            'name': cat.name,
            'image': cat.image,
            'count': cat.products.count(),
            'is_active': bool(selected_category and cat.id == selected_category.id)
        })

    all_count = Product.objects.count()

    return render(request, 'plantapp/category_products.html', {
        'category': selected_category,
        'categories': category_list,
        'products': products,
        'wishlist_products': wishlist_products,
        'search_query': search_query,
        'sort_by': sort_by,
        'total_count': products.count(),
        'all_count': all_count,
    })

def view_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_products = []
    if request.user.is_authenticated:
        wishlist_products = Wishlist.objects.filter(user=request.user).values_list('product_id', flat=True)

    return render(request, 'plantapp/view_product.html', {
        'product': product,
        'wishlist_products': wishlist_products
    })


@login_required
def profile_view(request):
    user = request.user
    profile, created = UserProfile.objects.get_or_create(user=user)

    if request.method == "POST":
        # Get form fields
        first_name = request.POST.get("first_name", "").strip()
        email = request.POST.get("email", "").strip()
        address = request.POST.get("address", "").strip()

        # Update and save user fields
        if first_name:
            user.first_name = first_name
        if email:
            user.email = email
        user.save()

        # Update profile address
        if address:
            profile.address = address
            profile.save()

        messages.success(request, "Profile updated successfully.")

    wishlist_count = Wishlist.objects.filter(user=user).count()
    cart = Cart.objects.filter(user=user).first()
    cart_count = cart.items.count() if cart else 0

    return render(request, 'plantapp/profile.html', {
        'profile': profile,
        'wishlist_count': wishlist_count,
        'cart_count': cart_count,
    })


@login_required
def edit_profile(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        form = EditProfileForm(request.POST, instance=profile)
        if form.is_valid():
            user.email = form.cleaned_data['email']
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('profile')
    else:
        form = EditProfileForm(instance=profile, initial={
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name
        })

    return render(request, 'plantapp/edit_profile.html', {'form': form})



@login_required
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'plantapp/wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    _, created = Wishlist.objects.get_or_create(user=request.user, product=product)

    if created:
        messages.success(request, f"{product.name} added to your wishlist.")
    else:
        messages.info(request, f"{product.name} is already in your wishlist.")
    
    return redirect(request.META.get('HTTP_REFERER', 'home'))

@login_required
def remove_from_wishlist(request, product_id):
    Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
    messages.success(request, "Item removed from wishlist.")
    return redirect('wishlist')

@login_required
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)

    if not created:
        wishlist_item.delete()
        messages.info(request, "Removed from wishlist.")
    else:
        messages.success(request, "Added to wishlist.")
    
    return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/'))


# -----------------------------
# 🛒 CART VIEWS
# -----------------------------

@login_required
@require_GET
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    quantity = int(request.GET.get('quantity', 1))

    cart, _ = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if not created:
        cart_item.quantity += quantity
    else:
        cart_item.quantity = quantity
    cart_item.save()

    total_items = sum(item.quantity for item in cart.items.all())

    return JsonResponse({'status': 'success', 'cart_count': total_items})

@login_required
def cart_view(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = CartItem.objects.filter(cart=cart).select_related('product')
    return render(request, 'plantapp/cart.html', {'cart': cart, 'items': items})

@login_required
@require_POST
def update_cart_items(request):
    for key, val in request.POST.items():
        if key.startswith('quantity_'):
            try:
                item_id = int(key.split('_')[1])
                quantity = int(val)

                item = CartItem.objects.get(id=item_id, cart__user=request.user)
                if quantity > 0:
                    item.quantity = quantity
                    item.save()
                else:
                    item.delete()
            except (CartItem.DoesNotExist, ValueError):
                continue
    return redirect('cart')

@login_required
def remove_cart_item(request, item_id):
    item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    item.delete()
    messages.success(request, "Item removed from cart.")
    return redirect('cart')

# -----------------------------
# 🤖 CHATBOT VIEW (POWERED BY GOOGLE GEMINI)
# -----------------------------
@csrf_exempt
@require_POST
def chat_with_ai(request):
    try:
        data = json.loads(request.body)
        user_message = data.get('message', '').strip()

        if not user_message:
            return JsonResponse({'response': "Please enter a question or message."})

        response_text = generate_gemini_response(user_message)
        return JsonResponse({'response': response_text})

    except Exception as e:
        return JsonResponse({'response': f"⚠️ Error processing request: {str(e)}"})



# strip payment keys from settings.py
#
#
#
# -----------------------------
# 🏦 STRIPE PAYMENT VIEWS

stripe.api_key = settings.STRIPE_SECRET_KEY

@login_required
def checkout_page(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product')

    # ✅ FIX: Don't call .subtotal(), it's a property
    total_amount = sum(item.subtotal for item in items)

    return render(request, 'plantapp/checkout.html', {
        'cart': cart,
        'total_amount': total_amount,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    })


@login_required
def create_checkout_session(request):
    cart, _ = Cart.objects.get_or_create(user=request.user)
    items = cart.items.select_related('product')

    if not items:
        return JsonResponse({'error': 'Your cart is empty.'}, status=400)

    line_items = []
    for item in items:
        line_items.append({
            'price_data': {
                'currency': 'inr',
                'product_data': {
                    'name': item.product.name,
                },
                'unit_amount': int(item.product.price * 100),
            },
            'quantity': item.quantity,
        })

    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=line_items,
        mode='payment',
        success_url=request.build_absolute_uri('/payment-success/'),
        cancel_url=request.build_absolute_uri('/payment-cancel/'),
    )

    return JsonResponse({'id': session.id})
    

def payment_success(request):
    return render(request, 'plantapp/payment_success.html')


def payment_cancel(request):
    return render(request, 'plantapp/payment_cancel.html')