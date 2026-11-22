import os

from django.contrib import messages
from django.shortcuts import render, redirect
from .models import Recipe
from .forms import RecipeForm
from django.http import JsonResponse
from django.db.models import Q
from django.shortcuts import get_object_or_404
from .services import (
    DATA_DIR,
    save_recipe_to_file,
    generate_safe_name,
    validate_json_content,
    validate_xml_content,
    read_data_file,
    list_data_files,
)

def index(request):
    form = RecipeForm()
    files = list_data_files()
    return render(request, 'recipes/index.html', {'form': form, 'files': files})


def add_recipe(request):
    if request.method != 'POST':
        return redirect('index')

    form = RecipeForm(request.POST)
    fmt = request.POST.get('fmt', 'json')
    if fmt not in ('json', 'xml', 'db'):
        fmt = 'json'

    if not form.is_valid():
        files = list_data_files()
        return render(request, 'recipes/index.html', {'form': form, 'files': files})

    if fmt == 'db':
        name = form.cleaned_data['name']
        # Проверка на дубликат (по названию рецепта, без учета регистра)
        if Recipe.objects.filter(name__iexact=name).exists():
            messages.error(request, f'Рецепт с названием «{name}» уже существует в базе данных.')
            files = list_data_files()
            return render(request, 'recipes/index.html', {'form': form, 'files': files})
        
        # Если дубликата нет — сохраняем в БД
        recipe = form.save()
        messages.success(request, f'Рецепт «{recipe.name}» успешно сохранён в базу данных!')
        return redirect('index')

    # Если выбрано сохранение в файл (JSON/XML)
    else:
        # commit=False создает объект в памяти, но НЕ сохраняет его в БД
        recipe = form.save(commit=False) 
        filename = save_recipe_to_file(recipe, fmt)
        messages.success(request, f'Рецепт «{recipe.name}» сохранён в файл {filename}')
        return redirect('index')


def upload_file(request):
    if request.method != 'POST':
        return redirect('index')

    uploaded = request.FILES.get('datafile')
    if not uploaded:
        messages.error(request, 'Файл не выбран.')
        return redirect('index')

    if uploaded.size > 2 * 1024 * 1024:
        messages.error(request, 'Файл слишком большой (максимум 2 МБ).')
        return redirect('index')

    _, ext = os.path.splitext(uploaded.name)
    ext = ext.lower()
    if ext not in ('.json', '.xml'):
        messages.error(request, 'Разрешены только файлы .json и .xml.')
        return redirect('index')

    try:
        content = uploaded.read().decode('utf-8')
    except UnicodeDecodeError:
        messages.error(request, 'Файл должен быть в кодировке UTF-8.')
        return redirect('index')

    try:
        if ext == '.json':
            recipes = validate_json_content(content)
        else:
            recipes = validate_xml_content(content)
    except Exception as e:
        messages.error(request, f'Файл невалиден и был отклонён: {e}')
        return redirect('index')

    safe_name = generate_safe_name(uploaded.name, prefix='upload')
    path = os.path.join(DATA_DIR, safe_name)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

    messages.success(
        request,
        f'Файл загружен как {safe_name}. Найдено рецептов: {len(recipes)}.'
    )
    return redirect('index')


def files_view(request):
    filenames = [f['name'] for f in list_data_files()]

    if not filenames:
        return render(request, 'recipes/files.html', {'files': [], 'empty': True})

    files = []
    for name in filenames:
        try:
            info = read_data_file(name)
            info['error'] = None
        except Exception as e:
            info = {'filename': name, 'raw': '', 'recipes': [], 'ext': '', 'error': str(e)}
        files.append(info)

    return render(request, 'recipes/files.html', {'files': files, 'empty': False})


def view_file(request, filename):
    try:
        info = read_data_file(filename)
        error = None
    except FileNotFoundError:
        messages.error(request, 'Файл не найден.')
        return redirect('files')
    except Exception as e:
        info = {'filename': filename, 'ext': '', 'raw': '', 'recipes': []}
        error = str(e)

    return render(request, 'recipes/view_file.html', {'info': info, 'error': error})


def delete_file(request, filename):
    safe = os.path.basename(filename)
    path = os.path.join(DATA_DIR, safe)
    if os.path.isfile(path):
        os.remove(path)
        messages.success(request, f'Файл {safe} удалён.')
    else:
        messages.error(request, 'Файл не найден.')
    return redirect('files')

def db_view(request):
    recipes = Recipe.objects.all().order_by('-created_at')
    return render(request, 'recipes/db.html', {'recipes': recipes})

def search_recipes_ajax(request):
    query = request.GET.get('q', '')
    if query:
        # Ищем совпадения по названию, ингредиентам или описанию
        recipes = Recipe.objects.filter(
            Q(name__icontains=query) |
            Q(ingredients__icontains=query) |
            Q(description__icontains=query)
        ).order_by('-created_at')
    else:
        recipes = Recipe.objects.all().order_by('-created_at')

    # Формируем список словарей для передачи в JSON
    data = []
    for r in recipes:
        data.append({
            'name': r.name,
            'ingredients': r.ingredients,
            'cooking_time': r.cooking_time,
            'difficulty': r.get_difficulty_display(),
            'description': r.description,
        })
    return JsonResponse({'recipes': data})

def edit_recipe_ajax(request, pk):
    recipe = get_object_or_404(Recipe, pk=pk)
    
    if request.method == 'GET':
        # Отдаем данные рецепта для заполнения формы в модальном окне
        data = {
            'id': recipe.id,
            'name': recipe.name,
            'ingredients': recipe.ingredients,
            'cooking_time': recipe.cooking_time,
            'difficulty': recipe.difficulty,
            'description': recipe.description,
        }
        return JsonResponse(data)
        
    elif request.method == 'POST':
        # Сохраняем отредактированные данные
        form = RecipeForm(request.POST, instance=recipe)
        if form.is_valid():
            form.save()
            return JsonResponse({'success': True})
        else:
            # Если есть ошибки валидации (например, пустое имя), возвращаем их
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)


def delete_recipe_ajax(request, pk):
    if request.method == 'POST':
        recipe = get_object_or_404(Recipe, pk=pk)
        recipe.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)