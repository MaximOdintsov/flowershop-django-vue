from decimal import Decimal

from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver


class ProductCategory(models.Model):
    title = models.CharField('Имя категории', max_length=100)
    slug = models.SlugField('Название на английском', max_length=150, unique=True, null=False)

    class Meta:
        verbose_name = 'Категория продукта'
        verbose_name_plural = 'Категории продуктов'

    def __str__(self):
        return self.title


class ProductComponent(models.Model):
    title = models.CharField('Название', max_length=150)
    slug = models.SlugField('Название на английском', max_length=150, unique=True)

    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)

    new_arrival = models.PositiveSmallIntegerField('Новое поступление', default=0)
    quantity_in_stock = models.PositiveSmallIntegerField('Запас', default=0)
    quantity_of_sold = models.PositiveSmallIntegerField('Количество проданных', default=0)

    available = models.BooleanField(verbose_name='Доступен', default=False)
    show_in_filter = models.BooleanField(verbose_name='Показывать в фильтре', default=False)

    class Meta:
        verbose_name = 'Компонент'
        verbose_name_plural = 'Компоненты'
        unique_together = ('slug', )
        ordering = ['quantity_of_sold']

    def __str__(self):
        return self.title

    def save_related_productcompositions(self):
        """Saves all related ProductComposition when ProductComponent.price changes"""
        compositions = self.productcomposition_set.all()
        for composition in compositions:
            composition.save()

    def add_new_arrival(self):
        self.quantity_in_stock += self.new_arrival
        self.new_arrival = 0


@receiver(pre_save, sender=ProductComponent)
def recalculate_quantity_in_stock_before_save(sender, instance, **kwargs):
    component = instance
    component.add_new_arrival()


@receiver(post_save, sender=ProductComponent)
def save_productcomposition(sender, instance, **kwargs):
    component = instance
    component.save_related_productcompositions()


class Product(models.Model):
    STATUS_REVIEW = 1
    STATUS_AVAILABLE = 2
    STATUS_ONLY_ORDER = 3
    STATUS_UNAVAILABLE = 4
    STATUS_CHOICES = [
        (STATUS_REVIEW, 'На проверке'),
        (STATUS_AVAILABLE, 'Доступно'),
        (STATUS_ONLY_ORDER, 'Только под заказ'),
        (STATUS_AVAILABLE, 'Недоступно')
    ]

    category = models.ForeignKey(ProductCategory, verbose_name='Категория', on_delete=models.PROTECT)

    title = models.CharField('Название', max_length=150)
    slug = models.SlugField('Название на английском', max_length=150, unique=True)
    preview = models.ImageField('Превью', upload_to='products/previews')

    price = models.DecimalField('Цена без скидки', max_digits=10, decimal_places=2, default=0)
    discount = models.PositiveSmallIntegerField('Скидка в %', default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])
    new_price = models.DecimalField('Цена со скидкой', max_digits=10, decimal_places=2, default=0)

    status = models.PositiveSmallIntegerField('Статус', choices=STATUS_CHOICES, default=STATUS_REVIEW)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        unique_together = ('slug', 'id')
        ordering = ['status']

    def __str__(self):
        return self.title

    @property
    def get_price(self):
        price = Decimal(0)
        for composition in self.productcomposition_set.all():
            price += composition.get_composition_price
        return price

    @property
    def get_new_price(self):
        return (self.price/100) * (100-self.discount)

    @property
    def get_available_quantity_of_products(self):
        compositions = self.productcomposition_set.all()
        number_of_composition_available = []

        for composition in compositions:
            if composition.quantity > 0:
                quantity = composition.component.quantity_in_stock // composition.quantity
                number_of_composition_available.append(quantity)

        if number_of_composition_available:
            return min(number_of_composition_available)
        return 0

    @property
    def get_status(self):
        if self.get_available_quantity_of_products > 0:
            return self.STATUS_AVAILABLE
        else:
            return self.STATUS_ONLY_ORDER

    @property
    def get_productcomponent_status(self):
        compositions = self.productcomposition_set.all()
        for composition in compositions:
            return composition.component.available

    def save_orderitem(self):
        items = self.orderitem_set.all()
        for item in items:
            item.save()


@receiver(pre_save, sender=Product)
def recalculate_new_price(sender, instance, **kwargs):
    product = instance
    if product.get_productcomponent_status is False:
        product.status = Product.STATUS_UNAVAILABLE

    product.new_price = product.get_new_price


@receiver(post_save, sender=Product)
def save_orderitem_after_save(sender, instance, **kwargs):
    product = instance
    product.save_orderitem()


class ProductGallery(models.Model):
    product = models.ForeignKey(Product, verbose_name='Товар', on_delete=models.CASCADE)
    image = models.ImageField('Изображение', upload_to='products/images')

    class Meta:
        verbose_name = 'Изображение'
        verbose_name_plural = 'Изображения'


class ProductComposition(models.Model):
    product = models.ForeignKey(Product, verbose_name='Товар', on_delete=models.CASCADE)
    component = models.ForeignKey(ProductComponent, verbose_name='Выбрать цветок', on_delete=models.PROTECT)
    quantity = models.PositiveSmallIntegerField('Количество компонентов', default=0)

    class Meta:
        verbose_name = 'Состав'

    def __str__(self):
        return f'{self.component} composition for {self.product}'

    @property
    def get_composition_price(self):
        return self.quantity * self.component.price


@receiver(post_save, sender=ProductComposition)
def save_product_after_save(sender, instance, **kwargs):
    product = instance.product
    product.price = product.get_price
    product.status = product.get_status
    product.save()


@receiver(post_delete, sender=ProductComposition)
def save_product_after_delete(sender, instance, **kwargs):
    product = instance.product
    product.price = product.get_price
    product.status = product.get_status
    product.save()

# def save_slug(pk, slug, title):
#     """
#     Переводит поле title с ru на en и сохраняет в slug
#     """
#
#     if (slug == str(pk)) or (len(slug) == 0):
#         try:
#             import translators as ts
#             translated_title = ts.google(title)
#             slug = slugify(translated_title)
#             return slug
#         except Exception:
#             slug = pk
#             return slug
#     else:
#         return slug
#
#
# class ProductCategory(models.Model):
#     """
#     Категория продукта
#     """
#     title = models.CharField('Имя категории', max_length=100)
#     slug = models.SlugField('Название на английском', max_length=150, unique=True, null=False)
#
#     class Meta:
#         verbose_name = 'Категория продукта'
#         verbose_name_plural = 'Категории продуктов'
#
#     def __str__(self):
#         return self.title
#
#     @transaction.atomic
#     def save(self, *args, **kwargs):
#         super(ProductCategory, self).save()
#         self.slug = save_slug(pk=self.id, slug=self.slug, title=self.title)
#
#         super(ProductCategory, self).save(*args, **kwargs)
#
#
# class ProductComponent(models.Model):
#     """
#     Класс компонента, из которого состоит продукт
#     """
#     SALE = 1
#     ORDER = 2
#
#     STATUS_CHOICES = [
#         (SALE, 'Доступно'),
#         (ORDER, 'Только под заказ'),
#     ]
#
#     title = models.CharField('Название', max_length=100)
#     slug = models.SlugField('Название на английском', max_length=150, unique=True, null=False)
#
#     price = models.DecimalField('Цена', max_digits=8, decimal_places=2, default=0)
#     old_price = models.DecimalField('Цена', max_digits=8, decimal_places=2, default=0)
#
#     new_arrival = models.PositiveSmallIntegerField('Новое поступление', default=0)
#
#     total_count = models.PositiveSmallIntegerField('Весь запас', default=0)
#     quantity_in_product = models.PositiveSmallIntegerField('Компоненты в продуктах', default=0)
#     quantity_for_sale = models.PositiveSmallIntegerField('Остаток для продажи', default=0)
#
#     status = models.PositiveSmallIntegerField(choices=STATUS_CHOICES,
#                                               verbose_name='Статус')
#     available = models.BooleanField(verbose_name='Доступен', default=False)
#
#     class Meta:
#         verbose_name = 'Компонент'
#         verbose_name_plural = 'Компоненты'
#         unique_together = ('slug', )
#
#     def __str__(self):
#         return self.title
#
#     def check_old_price(self):
#         """
#         Проверяет, не изменилась ли цена
#         """
#         if self.old_price != self.price:
#             return True
#         else:
#             return False
#
#     def update_new_arrival(self):
#         """
#         Обновляет количество компонентов при новом поступлении
#         """
#         if self.new_arrival != 0:
#             self.total_count += self.new_arrival
#             self.new_arrival = 0
#
#     def update_quantity_for_sale(self):
#         """
#         Обновляет количество остатка компонентов для продажи
#         """
#         self.quantity_for_sale = self.total_count - self.quantity_in_product
#
#     def update_price(self):
#         """
#         При изменении цены компонента нужно обновить все связанные продукты
#         """
#         compositions = ProductComposition.objects.filter(component_composition=self.id)
#         for composition in compositions:
#             composition.save_product()
#             composition.old_quantity = composition.quantity
#             composition.save()
#
#     @transaction.atomic
#     def save(self, *args, **kwargs):
#         super(ProductComponent, self).save()
#
#         if self.check_old_price() is True:
#             self.update_price()
#             self.old_price = self.price
#
#         self.slug = save_slug(pk=self.id, slug=self.slug, title=self.title)
#         self.update_new_arrival()
#         self.update_quantity_for_sale()
#
#         super(ProductComponent, self).save(*args, **kwargs)
#
#     @transaction.atomic
#     def save_quantity(self):
#         """
#         Функция сохранения компонента для других классов
#         """
#         self.update_quantity_for_sale()
#
#         super(ProductComponent, self).save()
#
#
# class Product(models.Model):
#     """
#     Класс продукта
#     """
#     UNCHECKED = 1
#     SALE = 2
#     ORDER = 3
#
#     STATUS_CHOICES = [
#         (UNCHECKED, 'Находится на проверке'),
#         (SALE, 'Доступно для продажи'),
#         (ORDER, 'Только под заказ'),
#     ]
#
#     category = models.ForeignKey(ProductCategory,
#                                  verbose_name='Категория',
#                                  on_delete=models.PROTECT)
#
#     title = models.CharField('Название', max_length=150)
#     slug = models.SlugField('Название на английском', max_length=150, unique=True, null=False)
#
#     preview = models.ImageField('Превью', upload_to='products/previews')
#
#     price = models.DecimalField('Цена без скидки', max_digits=8, decimal_places=2, default=0)
#     discount = models.PositiveSmallIntegerField('Скидка в %',
#                                                 default=0,
#                                                 validators=[MinValueValidator(0), MaxValueValidator(80)])
#     discount_price = models.DecimalField('Цена со скидкой', max_digits=8, decimal_places=2, default=0)
#
#     quantity = models.PositiveSmallIntegerField('Количество продуктов', default=1)
#     old_quantity = models.PositiveSmallIntegerField('Старое количества', default=0)
#
#     status = models.PositiveSmallIntegerField('Статус',
#                                               choices=STATUS_CHOICES,
#                                               default=UNCHECKED)
#
#     available = models.BooleanField('Доступен', default=False)
#
#     class Meta:
#         verbose_name = 'Товар'
#         verbose_name_plural = 'Товары'
#         unique_together = ('slug',)
#
#     def __str__(self):
#         return self.title
#
#     def save_orderitem(self):
#         items = self.orderitem_set.all()
#         for item in items:
#             item.save()
#
#     def get_url(self):
#         return reverse('product_detail', args=[self.slug])
#
#     def get_composition(self):
#         """
#         Получает композицию продукта
#         """
#         composition = Product.objects.get(id=self.id).product_composition.all()
#         return composition
#
#     def check_quantity_update(self):
#         """
#         Проверяет, было ли обновлено self.quantity
#         """
#         if self.old_quantity != self.quantity:
#             return True
#         else:
#             return False
#
#     def update_product_price(self):
#         """
#         Обнуляем цену продукта и
#         рассчитываем цену из всех его компонентов
#         """
#         compositions = self.get_composition()
#         self.price = 0
#         for composition in compositions:
#             self.price += composition.price_counter()
#
#     def update_discount_price(self):
#         """
#         Рассчитывает цену со скидкой
#         """
#         sale = (self.price / 100) * self.discount
#         self.discount_price = self.price - sale
#         return self.discount_price
#
#     def save_composition(self):
#         """
#         Сохраняет все связанные объекты ProductComposition
#         Нужно для того, чтобы делать расчеты для
#         Component и Composition при изменении self.quantity
#         """
#         compositions = self.get_composition()
#         for composition in compositions:
#             composition.save()
#
#     def delete_composition(self):
#         """
#         Удаляет все связанные объекты ProductComposition
#         """
#         compositions = self.get_composition()
#         for composition in compositions:
#             composition.delete()
#
#     @transaction.atomic
#     def save(self, *args, **kwargs):
#         super(Product, self).save()
#         self.slug = save_slug(pk=self.id, slug=self.slug, title=self.title)
#
#         if self.check_quantity_update() is True:
#             self.save_composition()
#             self.old_quantity = self.quantity
#
#         self.update_product_price()
#         self.update_discount_price()
#
#         super(Product, self).save(*args, **kwargs)
#
#     @transaction.atomic
#     def delete(self, *args, **kwargs):
#         self.delete_composition()
#         super(Product, self).delete(*args, **kwargs)
#
#
# @receiver(post_save, sender=Product)
# def resave_related_order_items_after_save(sender, instance, **kwargs):
#     product = instance
#     product.save_orderitem()
#
#
# class ProductGallery(models.Model):
#     """
#     Добавляет картинки в продукт
#     """
#     product_gallery = models.ForeignKey(Product,
#                                         on_delete=models.CASCADE,
#                                         related_name='product_gallery')
#
#     image = models.ImageField(upload_to='products/images')
#
#     class Meta:
#         verbose_name = 'Изображение'
#         verbose_name_plural = 'Изображения'
#
#
# class ProductComposition(models.Model):
#     """
#     Определяет состав продукта
#     """
#     product_composition = models.ForeignKey(Product,
#                                             verbose_name='Товар',
#                                             on_delete=models.CASCADE,
#                                             related_name='product_composition')
#
#     component_composition = models.ForeignKey(ProductComponent,
#                                               verbose_name='Выбрать цветок',
#                                               on_delete=models.PROTECT,
#                                               db_column='component',
#                                               related_name='component_composition')
#
#     quantity = models.PositiveSmallIntegerField('Количество компонентов', default=1)
#     old_quantity = models.PositiveSmallIntegerField('Обновление количества компонентов', default=0)
#
#     # общее количество в экземпляре продукта
#     # (количество продуктов * количество компонентов в 1 продукте)
#     total_quantity = models.PositiveSmallIntegerField('Общее количество', default=0)
#
#     class Meta:
#         verbose_name = 'Цветок'
#         verbose_name_plural = 'Цветы'
#
#     def __str__(self):
#         return f'Composition id {self.id}, component_composition - ' \
#                f'{self.component_composition.title}, ' \
#                f'доступное количество для продажи: {self.component_composition.quantity_for_sale}'
#
#     def check_quantity_update(self):
#         """
#         Проверяет, было ли обновлено self.quantity
#         """
#         if self.old_quantity != self.quantity:
#             return True
#         else:
#             return False
#
#     def save_product(self):
#         super(ProductComposition, self).save()
#         product = Product.objects.get(id=self.product_composition.id)
#         product.save()
#
#     def price_counter(self):
#         """
#         Рассчитывает цену продукта из всех компонентов
#         """
#         price = self.component_composition.price * self.quantity
#         return price
#
#     def update_total_quantity(self):
#         """
#         Удаляем старое значение self.total_quantity
#         из Component.quantity_in_product
#         и обновляем self.total_quantity
#
#         Сохраняем Component
#         """
#         self.component_composition.quantity_in_product -= self.total_quantity
#         self.total_quantity = self.product_composition.quantity * self.quantity
#         self.component_composition.quantity_in_product += self.total_quantity
#
#         self.component_composition.save_quantity()
#
#     def delete_component(self):
#         """
#         Удаляет quantity_in_product из ProductComponent
#         """
#         self.component_composition.quantity_in_product -= self.total_quantity
#         self.component_composition.save_quantity()
#
#     @transaction.atomic
#     def save(self, *args, **kwargs):
#
#         if self.check_quantity_update() is True:
#             self.save_product()
#             self.old_quantity = self.quantity
#
#         self.update_total_quantity()
#         super(ProductComposition, self).save(*args, **kwargs)
#
#     @transaction.atomic
#     def delete(self, *args, **kwargs):
#         self.delete_component()
#         super(ProductComposition, self).delete(*args, **kwargs)


