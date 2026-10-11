import os

from django.contrib import messages
from django.shortcuts import render, redirect

from .forms import RecipeForm
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
    if fmt not in ('json', 'xml'):
        fmt = 'json'

    if not form.is_valid():
        files = list_data_files()
        return render(request, 'recipes/index.html', {'form': form, 'files': files})

    recipe = form.save()
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