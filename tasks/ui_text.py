"""Русские подписи для UI задач."""

PRIORITY_LABELS = {
    'High': 'Высокий',
    'Medium': 'Средний',
    'Low': 'Низкий',
}

STATUS_UI_LABELS = {
    'open': 'К выполнению',
    'in_progress': 'В работе',
    'pending_review': 'На проверке',
    'completed': 'Выполнена',
    'failed': 'Отменена',
}

STATUS_CHOICES_RU = [
    ('open', 'Открыта'),
    ('in_progress', 'В работе'),
    ('pending_review', 'На проверке'),
    ('completed', 'Выполнена'),
    ('failed', 'Провалена'),
]

PRIORITY_FILTER_CHOICES = [
    ('High', 'Высокий'),
    ('Medium', 'Средний'),
    ('Low', 'Низкий'),
]

RESULT_FILTER_CHOICES = [
    ('completed', 'Выполнена'),
    ('failed', 'Провалена'),
]

MEMBER_BADGES = {
    'owner': 'Владелец',
    'you': 'Вы',
    'member': 'Участник',
}

ROLE_TITLES = {
    'Front': 'Frontend-разработчик',
    'Back': 'Backend-разработчик',
    'Design': 'FullStack-разработчик',
    'DB': 'Инженер БД',
    'BD': 'Business-разработчик',
    'Backlog': 'Product-разработчик',
    'Canceled': 'Разработчик',
}

def greeting_for_hour(hour):
    """Приветствие по локальному часу (0–23)."""
    if 5 <= hour < 12:
        return 'Доброе утро'
    if 12 <= hour < 18:
        return 'Добрый день'
    if 18 <= hour < 23:
        return 'Добрый вечер'
    return 'Доброй ночи'


WEEKDAY_NAMES = [
    'понедельник', 'вторник', 'среда', 'четверг',
    'пятница', 'суббота', 'воскресенье',
]

MONTH_NAMES = [
    '', 'января', 'февраля', 'марта', 'апреля', 'мая', 'июня',
    'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря',
]

PROJECT_STATUS_LABELS = {
    'Design': 'Веб-дизайн',
    'DB': 'SQL-база',
    'Front': 'Мобильный шаблон',
    'Back': 'Backend API',
    'BD': 'Одностраничник',
}
