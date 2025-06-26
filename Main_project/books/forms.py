from django import forms
from .models import Book, Review, Cover, Order, User
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Submit, Row, Column, Div, HTML
from crispy_forms.bootstrap import TabHolder, Tab, FormActions
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from typing import Any, Dict
from django.contrib.auth.forms import UserCreationForm as DjangoUserCreationForm

class BookForm(forms.ModelForm):
    published_at = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M'
        ),
        input_formats=['%Y-%m-%dT%H:%M']
    )
    discount_start = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M'
        ),
        input_formats=['%Y-%m-%dT%H:%M']
    )
    discount_end = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={'type': 'datetime-local'},
            format='%Y-%m-%dT%H:%M'
        ),
        input_formats=['%Y-%m-%dT%H:%M']
    )

    class Meta:
        model = Book
        fields = [
            'title', 'author', 'description', 'price', 'status',
            'has_discount', 'discount_percent', 'discount_start', 'discount_end',
            'ebook_file', 'published_at', 'stock_quantity'
        ]

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Инициализация формы с настройкой Crispy Forms и начальных значений.

        Args:
            *args: Позиционные аргументы.
            **kwargs: Именованные аргументы.
        """
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = True
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        
        # Устанавливаем начальные значения для полей даты
        if self.instance and self.instance.pk:
            if self.instance.published_at:
                self.initial['published_at'] = self.instance.published_at.strftime('%Y-%m-%dT%H:%M')
            if self.instance.discount_start:
                self.initial['discount_start'] = self.instance.discount_start.strftime('%Y-%m-%dT%H:%M')
            if self.instance.discount_end:
                self.initial['discount_end'] = self.instance.discount_end.strftime('%Y-%m-%dT%H:%M')
        
        self.helper.layout = Layout(
            TabHolder(
                Tab('Основная информация',
                    'title',
                    'author',
                    'description',
                    'price',
                    'status',
                    'published_at',
                ),
                Tab('Скидки',
                    'has_discount',
                    'discount_percent',
                    'discount_start',
                    'discount_end',
                ),
                Tab('Файлы',
                    'ebook_file',
                ),
            ),
            FormActions(
                Submit('submit', 'Сохранить', css_class='btn btn-primary'),
                HTML('<a href="{% url "admin:books_book_changelist" %}" class="btn btn-secondary">Отмена</a>'),
            )
        )

    def clean(self):
        cleaned_data = super().clean()
        has_discount = cleaned_data.get('has_discount')
        discount_percent = cleaned_data.get('discount_percent')
        discount_start = cleaned_data.get('discount_start')
        discount_end = cleaned_data.get('discount_end')
        status = cleaned_data.get('status')
        stock_quantity = cleaned_data.get('stock_quantity')

        # Валидация скидок
        if has_discount:
            if not discount_percent:
                raise forms.ValidationError(_('Укажите процент скидки'))
            if discount_percent > 100:
                raise forms.ValidationError(_('Процент скидки не может быть больше 100'))
            if not discount_start or not discount_end:
                raise forms.ValidationError(_('Для активной скидки необходимо указать даты начала и окончания'))
            if discount_start >= discount_end:
                raise forms.ValidationError(_('Дата начала скидки должна быть раньше даты окончания'))

        # Валидация статуса и количества
        if status == 'available' and stock_quantity == 0:
            raise forms.ValidationError(_('Книга не может быть в наличии при нулевом количестве'))
        if status == 'out_of_stock' and stock_quantity > 0:
            raise forms.ValidationError(_('Книга не может быть отсутствовать при наличии на складе'))

        return cleaned_data

class CoverForm(forms.ModelForm):
    class Meta:
        model = Cover
        fields = ['image']
        widgets = {
            'image': forms.FileInput(attrs={'accept': 'image/*'})
        }

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={'rows': 4}),
        }

class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['shipping_address', 'payment_method']
        widgets = {
            'shipping_address': forms.Textarea(attrs={'rows': 3}),
            'payment_method': forms.Select(choices=Order.PAYMENT_CHOICES),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """
        Инициализация формы заказа с настройкой Crispy Forms.

        Args:
            *args: Позиционные аргументы.
            **kwargs: Именованные аргументы.
        """
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = True
        self.helper.form_method = 'post'
        
        self.helper.layout = Layout(
            'shipping_address',
            'payment_method',
            FormActions(
                Submit('submit', 'Оформить заказ', css_class='btn btn-primary'),
            )
        )

class UserRegistrationForm(DjangoUserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'password1', 'password2', 'email', 'first_name', 'last_name') 