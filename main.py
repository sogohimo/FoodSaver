import pandas as pd
from datetime import datetime, timedelta
import requests
from telegram import Bot
from telegram.error import BadRequest, Unauthorized
import json
import config
from llamaapi import LlamaAPI

def read_csv(file_path):
    return pd.read_csv(file_path, encoding='cp1251')

def generate_recipe(product_name, available_products):
    llama = LlamaAPI(config.LLAMA_API_KEY)
    api_request_json = {
        "messages": [
            {"role": "system", "content": "Ты - русскоязычный помощник по кулинарии. Всегда отвечай только на русском языке."},
            {"role": "user", "content": f"Создай рецепт, используя {product_name} и другие доступные ингредиенты: {', '.join(available_products)}. Рецепт должен быть на русском языке."},
        ]
    }
    try:
        response = llama.run(api_request_json)
        response.raise_for_status()
        response_data = response.json()
        return response_data['choices'][0]['message']['content']
    except requests.RequestException as e:
        return f"Ошибка при запросе к LLAMA API: {str(e)}"
    except (KeyError, IndexError) as e:
        return f"Ошибка при обработке ответа LLAMA API: {str(e)}"
    except Exception as e:
        return f"Непредвиденная ошибка: {str(e)}"

def generate_image(prompt):
    url = config.STABLE_DIFFUSION_API_URL
    payload = {
        "key": config.STABLE_DIFFUSION_API_KEY,
        "prompt": prompt,
        "negative_prompt": "",
        "width": "512",
        "height": "512",
        "safety_checker": False,
        "seed": None,
        "samples": 1,
        "base64": False,
        "webhook": None,
        "track_id": None
    }
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        response_data = response.json()
        return response_data['output'][0]
    except requests.RequestException as e:
        print(f"Error generating image: {str(e)}")
        return None

def send_telegram_message(bot_token, chat_id, message, image_url):
    try:
        bot = Bot(token=bot_token)
        
        # Разделяем сообщение на части по 4000 символов (лимит Telegram)
        message_parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
        
        for part in message_parts:
            bot.send_message(chat_id=chat_id, text=part)
        
        if image_url:
            bot.send_photo(chat_id=chat_id, photo=image_url)
    except BadRequest as e:
        print(f"Ошибка BadRequest: {e}")
    except Unauthorized as e:
        print(f"Ошибка авторизации: {e}")
    except Exception as e:
        print(f"Непредвиденная ошибка при отправке сообщения в Telegram: {e}")

def main():
    try:
        products_df = read_csv(config.CSV_FILE_PATH)
    except Exception as e:
        print(f"Ошибка при чтении CSV файла: {str(e)}")
        return

    today = datetime.today()
    warning_date = today + timedelta(days=config.EXPIRY_WARNING_THRESHOLD)
    
    expiring_products = products_df[pd.to_datetime(products_df['Срок годности'], format='%Y-%m-%d') <= warning_date]

    if not expiring_products.empty:
        for _, product in expiring_products.iterrows():
            product_name = product['Название продукта']
            expiry_date = product['Срок годности']
            available_products = products_df['Название продукта'].tolist()

            recipe = generate_recipe(product_name, available_products)
            image_url = generate_image(recipe)

            message = f"Продукт {product_name} скоро испортится.\n"
            message += f"Срок годности: {expiry_date}.\n\n"
            message += f"Предлагаю вам приготовить сегодня:\n\n{recipe}"
            
            send_telegram_message(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID, message, image_url)
    else:
        print("Продуктов с истекающим сроком годности не найдено.")

if __name__ == "__main__":
    main()