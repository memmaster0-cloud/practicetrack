from behave import given, when, then

from app.domain import Status
from app.progress import calculate_progress, format_days_left


@given('у студента всего работ: {total:d}')
def step_total(context, total):
    context.total = total


@given('из них принято: {accepted:d}')
def step_accepted(context, accepted):
    context.statuses = ([Status.ACCEPTED] * accepted
                        + [Status.IN_PROGRESS] * (context.total - accepted))


@when('я рассчитываю прогресс')
def step_calc(context):
    context.result = calculate_progress(context.statuses)


@then('прогресс равен {expected:d}%')
def step_check_progress(context, expected):
    assert context.result == expected, f"ожидалось {expected}, получено {context.result}"


@given('до срока осталось дней: {days:d}')
def step_days(context, days):
    context.days = days


@when('я формирую подпись срока')
def step_label(context):
    context.label = format_days_left(context.days)


@then('подпись такая: "{text}"')
def step_check_label(context, text):
    assert context.label == text, f"ожидалось «{text}», получено «{context.label}»"
