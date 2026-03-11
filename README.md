# FastAPI-Store
Учебный проект магазина на FastAPI
Для запуска проекта:

в .env добавить:
1) SECRET_KEY - генерируем командой "openssl rand -hex 32"
2) DATABASE_URL - postgresql+asyncpg://*user*:*password*@*address*:*port*/*DATABASE_name*
Пример есть в .env.example
