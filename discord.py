def generate_reply(prompt, use_google_ai=True, use_file_reply=False, language="en"):
    """Membuat balasan, menghindari duplikasi jika menggunakan Google Gemini AI"""

    global last_ai_response  # Gunakan variabel global agar dapat diakses di seluruh sesi

    if use_file_reply:
        log_message("💬 Using a message from the file as a reply.")
        return {"candidates": [{"content": {"parts": [{"text": get_random_message()}]}}]}

    if use_google_ai:
        # Use English for all responses
        ai_prompt = f"{prompt}\n\nRespond with only one sentence in casual urban English, like a natural conversation, and do not use symbols."

        url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={google_api_key}'
        headers = {'Content-Type': 'application/json'}
        data = {'contents': [{'parts': [{'text': ai_prompt}]}]}

        for attempt in range(3):  # Try up to 3 times if the AI repeats the same message
            try:
                response = requests.post(url, headers=headers, json=data)
                response.raise_for_status()
                ai_response = response.json()

                # Extract text from the AI response
                response_text = ai_response['candidates'][0]['content']['parts'][0]['text']

                # Check if the AI response is the same as the last one
                if response_text == last_ai_response:
                    log_message("⚠️ AI gave the same response, retrying...")
                    continue  # Retry with a new request
                
                last_ai_response = response_text  # Save the latest response
                return ai_response

            except requests.exceptions.RequestException as e:
                log_message(f"⚠️ Request failed: {e}")
                return None

        log_message("⚠️ AI kept giving the same response, using the last available response.")
        return {"candidates": [{"content": {"parts": [{"text": last_ai_response or 'Sorry, I cannot respond.'}]}}]}

    else:
        return {"candidates": [{"content": {"parts": [{"text": get_random_message()}]}}]}

def auto_reply(channel_id, read_delay, reply_delay, use_google_ai, use_file_reply, language, reply_mode):
    """Function for auto-reply on Discord, avoiding AI response duplication"""
    global last_message_id, bot_user_id

    headers = {'Authorization': f'{discord_token}'}

    try:
        bot_info_response = requests.get('https://discord.com/api/v9/users/@me', headers=headers)
        bot_info_response.raise_for_status()
        bot_user_id = bot_info_response.json().get('id')
    except requests.exceptions.RequestException as e:
        log_message(f"⚠️ Failed to retrieve bot information: {e}")
        return

    while True:
        try:
            response = requests.get(f'https://discord.com/api/v9/channels/{channel_id}/messages', headers=headers)
            response.raise_for_status()

            if response.status_code == 200:
                messages = response.json()
                if len(messages) > 0:
                    most_recent_message = messages[0]
                    message_id = most_recent_message.get('id')
                    author_id = most_recent_message.get('author', {}).get('id')
                    message_type = most_recent_message.get('type', '')

                    if (last_message_id is None or int(message_id) > int(last_message_id)) and author_id != bot_user_id and message_type != 8:
                        user_message = most_recent_message.get('content', '')
                        log_message(f"💬 Received message: {user_message}")

                        result = generate_reply(user_message, use_google_ai, use_file_reply, language)
                        response_text = result['candidates'][0]['content']['parts'][0]['text'] if result else "Sorry, I cannot respond."

                        log_message(f"⏳ Waiting {reply_delay} seconds before replying...")
                        time.sleep(reply_delay)
                        send_message(channel_id, response_text, reply_to=message_id if reply_mode else None, reply_mode=reply_mode)
                        last_message_id = message_id

            log_message(f"⏳ Waiting {read_delay} seconds before checking for new messages...")
            time.sleep(read_delay)
        except requests.exceptions.RequestException as e:
            log_message(f"⚠️ Request error: {e}")
            time.sleep(read_delay)

if __name__ == "__main__":
    use_reply = input("Do you want to use auto-reply feature? (y/n): ").lower() == 'y'
    channel_id = input("Enter the channel ID: ")

    if use_reply:
        use_google_ai = input("Use Google Gemini AI for replies? (y/n): ").lower() == 'y'
        use_file_reply = input("Use message from file 'pesan.txt' for replies? (y/n): ").lower() == 'y'
        reply_mode = input("Do you want to reply to the message or just send a message? (reply/send): ").lower() == 'reply'
        
        # Set language to English (no option for other languages)
        language_choice = "en"

        read_delay = int(input("Set delay to read new messages (in seconds): "))
        reply_delay = int(input("Set delay before replying (in seconds): "))

        log_message(f"✅ Reply mode {'active' if reply_mode else 'inactive'} with English responses...")
        auto_reply(channel_id, read_delay, reply_delay, use_google_ai, use_file_reply, language_choice, reply_mode)

    else:
        send_interval = int(input("Set message sending interval (in seconds): "))
        log_message("✅ Sending random message mode active...")

        while True:
            message_text = get_random_message()
            send_message(channel_id, message_text, reply_mode=False)
            log_message(f"⏳ Waiting {send_interval} seconds before sending the next message...")
            time.sleep(send_interval)