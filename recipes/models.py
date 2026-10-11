from django.db import models


class Recipe(models.Model):
    DIFFICULTY_CHOICES = [
        ('easy', 'Легко'),
        ('medium', 'Средне'),
        ('hard', 'Сложно'),
    ]

    name = models.CharField('Название', max_length=200)
    ingredients = models.TextField('Ингредиенты')
    cooking_time = models.PositiveIntegerField('Время готовки (мин)')
    difficulty = models.CharField('Сложность', max_length=10, choices=DIFFICULTY_CHOICES)
    description = models.TextField('Описание', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name