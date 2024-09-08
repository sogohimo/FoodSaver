import datetime
import requests
import sqlite3
import pytz
from apscheduler.schedulers.background import BackgroundScheduler

TOKEN = '7260581002:AAGyq_ND-RNXH6J45MukuqDRIp5MzX9RbG4'

def get_expiring_products():
    notifications = []
    three_days_from_now = datetime.date.today() + datetime.timedelta(days=3)

    # Подключение к базе данных
    conn = sqlite3.connect('/app/instance/users.db')
    cursor = conn.cursor()

    # Получаем продукты, срок годности которых истек или истекает в течение трех дней
    cursor.execute("SELECT name, expiration_date FROM product WHERE expiration_date <= ?", (three_days_from_now.strftime('%Y-%m-%d'),))
    expiring_products = cursor.fetchall()

    for product in expiring_products:
        name, expiration_date = product
        expiration_date = datetime.datetime.strptime(expiration_date, '%Y-%m-%d').date()
        if expiration_date < datetime.date.today():
            notification = f"Продукт '{name}' уже просрочен! Срок годности истек {expiration_date}."
        else:
            notification = f"Продукт '{name}' истекает срок годности через {(expiration_date - datetime.date.today()).days} дней!"
        notifications.append(notification)

    # Закрываем соединение с базой данных
    conn.close()

    return notifications

def send_notifications(notifications):
    # Подключение к базе данных
    conn = sqlite3.connect('/app/instance/users.db')
    cursor = conn.cursor()

    # Получаем список подписчиков
    cursor.execute("SELECT chat_id FROM subscriber")
    subscribers = cursor.fetchall()

    # Формируем список продуктов в виде одного сообщения
    message = "\n\n".join(notifications)

    for subscriber in subscribers:
        chat_id = subscriber[0]
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage?chat_id={chat_id}&text={message}"
        requests.get(url)

    # Закрываем соединение с базой данных
    conn.close()

def check_expiring_products():
    notifications = get_expiring_products()
    send_notifications(notifications)

scheduler = BackgroundScheduler()

# Настройка задачи на выполнение через 10 секунд
scheduler.add_job(check_expiring_products, 'cron', hour=10, minute=0, timezone=pytz.timezone('Asia/Yekaterinburg'))
scheduler.add_job(check_expiring_products, 'cron', hour=18, minute=30, timezone=pytz.timezone('Asia/Yekaterinburg'))

if __name__ == '__main__':
    scheduler.start()

    # Бесконечный цикл для поддержания работы скрипта
    try:
        while True:
            pass
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()


