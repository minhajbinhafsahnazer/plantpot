from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    
    # Auth
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('alt-login/', views.alt_login_view, name='alt_login'),

    # Category & Products
    path('category/<int:category_id>/', views.category_products_view, name='category_products'),
    path('product/<int:product_id>/', views.view_product, name='view_product'),
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),

    # Wishlist
    path('wishlist/', views.wishlist, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:product_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('wishlist/toggle/<int:product_id>/', views.toggle_wishlist, name='toggle_wishlist'),

    # Cart
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.cart_view, name='cart'),  # ✅ Use correct view
    path('cart/update/', views.update_cart_items, name='update_cart_items'),
    path('cart/remove/<int:item_id>/', views.remove_cart_item, name='remove_cart_item'),
]
