# plantapp/admin.py

from django.contrib import admin
from .models import Category, Product
from .models import Cart, CartItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'price']
    list_filter = ['category']

admin.site.register(Cart)
admin.site.register(CartItem)