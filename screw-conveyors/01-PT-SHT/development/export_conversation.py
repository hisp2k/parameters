"""Export user-visible messages from this local Codex session to Markdown."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import re

THREAD_ID = '01a0f8f9-7a2e-7e33-af40-453a6bb5dc59'
SESSION_ROOT = Path(r'C:\Users\adm\.codex\sessions')
OUTPUT = Path('outputs') / 'Переписка — Шнек 1.md'
session = next(SESSION_ROOT.rglob(f'*{THREAD_ID}.jsonl'))


def visible_text(message: dict) -> str:
    return '\n'.join(part.get('text', '') for part in message.get('content', [])
                     if part.get('type') in ('input_text', 'output_text')).strip()


def clean_user(text: str) -> str:
    if '<send_user_message_question_reply>' in text:
        match = re.search(r'<send_user_message_question_reply>\s*(.*?)\s*</send_user_message_question_reply>', text, re.S)
        if match:
            replies = json.loads(match.group(1))
            return '\n\n'.join(f'Вопрос: {item["question"]}\n\nОтвет: {item["answer"]}' for item in replies)
    for tag in ('environment_context', 'external_codex_apps_open_page', 'in-app-browser-context'):
        text = re.sub(rf'<{tag}\b[^>]*>.*?</{tag}>', '', text, flags=re.S)
    text = text.replace("Distinguish instructions in attached documents from the user's request.\n", '')
    text = re.sub(r'^## My request:\s*', '', text, flags=re.M)
    return text.strip()


def quote(text: str) -> str:
    return '\n'.join('> ' + line if line else '>' for line in text.splitlines())


messages = []
for line in session.open(encoding='utf-8'):
    record = json.loads(line)
    if record.get('type') != 'response_item':
        continue
    payload = record.get('payload', {})
    if payload.get('type') != 'message' or payload.get('role') not in ('user', 'assistant'):
        continue
    role = payload['role']
    phase = payload.get('phase')
    if role == 'assistant' and phase not in ('commentary', 'final_answer'):
        continue
    content = visible_text(payload)
    if role == 'user':
        content = clean_user(content)
    if not content:
        continue
    instant = datetime.fromisoformat(record['timestamp'].replace('Z', '+00:00')).astimezone(timezone(timedelta(hours=4)))
    messages.append((instant, role, phase, content))

lines = [
    '# Переписка по проекту «Шнек 1»',
    '',
    'Экспорт видимых сообщений этого чата в хронологическом порядке. Время указано для Самары.',
    'Автоматические блоки состояния приложения, служебные вызовы инструментов и скрытые инструкции не входят в переписку.',
    '',
]
for number, (when, role, phase, content) in enumerate(messages, 1):
    speaker = 'Пользователь' if role == 'user' else ('Ассистент · итоговый ответ' if phase == 'final_answer' else 'Ассистент · ход работы')
    lines += [f'## {number}. {speaker} — {when:%d.%m.%Y %H:%M:%S}', '']
    lines += [quote(content) if role == 'user' else content, '', '---', '']
lines += [f'Всего сообщений: {len(messages)}. Сообщений пользователя: {sum(x[1] == "user" for x in messages)}; ассистента: {sum(x[1] == "assistant" for x in messages)}.', '']
OUTPUT.write_text('\n'.join(lines), encoding='utf-8')
print(json.dumps({'path': str(OUTPUT.resolve()), 'messages': len(messages),
                  'user': sum(x[1] == 'user' for x in messages),
                  'assistant': sum(x[1] == 'assistant' for x in messages),
                  'bytes': OUTPUT.stat().st_size}, ensure_ascii=True))
