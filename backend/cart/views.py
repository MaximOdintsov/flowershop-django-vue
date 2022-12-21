from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST
from django.views.generic import View

from products.models import Product
from .cart import Cart
from .forms import CartAddProductForm


def cart_add_all(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(request.POST)

    if form.is_valid():
        cd = form.cleaned_data
        cart.add(product=product,
                 quantity=cd['quantity'],
                 update_quantity=cd['update'])
    return redirect('cart:cart_detail')


def cart_remove_all(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('cart:cart_detail')


def cart_add_one(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)

    cart.add_one(product=product,
                 quantity=1,
                 update_quantity=True)
    return redirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))


def cart_remove_one(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)

    if cart.counter(str(product_id)) >= 0:
        cart.add_one(product=product,
                     quantity=-1,
                     update_quantity=True)
    else:
        raise ValidationError('Это значение не должно быть отрицательным')
    return redirect(request.META.get('HTTP_REFERER', 'redirect_if_referer_not_found'))


def cart_detail(request):
    cart = Cart(request)

    context = {
        'cart': cart
    }
    return render(request, 'cart/cart_detail.html', context=context)

