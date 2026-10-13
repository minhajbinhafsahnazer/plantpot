from .models import CartItem, Cart

def cart_count(request):
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        try:
            cart = Cart.objects.get(user=user)
            count = CartItem.objects.filter(cart=cart).count()
        except Cart.DoesNotExist:
            count = 0
    else:
        count = 0
    return {'cart_count': count}
