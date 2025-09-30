# AutoReg-GMX

Автоматизація створення тестових поштових скриньок GMX за допомогою Python 3.13.7 та Selenium.

## Огляд

Проєкт реалізує типову для веб-автоматизації архітектуру Page Object Model (POM):

- **`app/config.py`** – завантаження параметрів запуску браузера та налаштування середовища.
- **`app/data_models.py`** – датакласи для реєстраційних даних та результуючих статусів + генератор тестових даних через Faker.
- **`app/driver_factory.py`** – фабрика WebDriver з підтримкою керування життєвим циклом через контекстний менеджер.
- **`app/automation/`** – рівень Page Objects (сторінка реєстрації) та сервіс бізнес-логіки.
- **`app/main.py`** – CLI-утиліта, що готує дані, керує сервісом та збирає результат.
- **`app/logging_config.py`** – централізоване налаштування логування.

Код пройшов структурування таким чином, щоб можна було легко розширювати флоу (наприклад, нові провайдери або сценарії).

## Вимоги

- Python 3.13.7
- Google Chrome / Chromium з відповідним ChromeDriver (встановлюється автоматично через `webdriver-manager`)

Встановлення залежностей:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

### Підготовка `.env`

Скопіюйте `.env.example` у `.env` і оновіть значення під себе:

```
# 1 — використовувати проксі, 0 — запуск без проксі
GMX_PROXY_ENABLED=1
GMX_PROXY_SCHEME=socks5
GMX_PROXY_URL=proxy-host:port:user:password
GMX_SQLITE_PATH=./data/registrations.sqlite3
```

Коли `GMX_PROXY_ENABLED=1`, значення `GMX_PROXY_URL` обов'язкове. Якщо виставити `0`, трафік піде напряму.

## Запуск

```bash
python -m app.main --locale uk_UA --dump-json
```

- проксі й перемикач беруться з `.env`. Прапорець `--proxy http://host:port` тимчасово перекриває обидва значення; навіть якщо в `.env` проксі вимкнено, CLI-прапорець увімкне його на поточний запуск;
- `--data-file path.json` – використати власні дані замість згенерованих (формат див. нижче).
- `--skip-submit` – заповнити форму та зупинитися перед фінальним кліком.
- `--headed` / `--headless` – примусово керують режимом браузера, перекриваючи змінні середовища.
- `--success-url-fragment` – уривок URL, що сигналізує про успішну реєстрацію.
- `--dump-json` – вивести згенеровані дані у форматі JSON.

## Конфігурація через середовище

| Змінна | Значення за замовчуванням | Опис |
| --- | --- | --- |
| `GMX_BASE_URL` | `https://signup.gmx.com/#.1559516-header-signup1-1` | URL форми реєстрації |
| `GMX_HEADLESS` | `true` | Запускати браузер без інтерфейсу |
| `GMX_WINDOW_WIDTH` | `1920` | Ширина вікна |
| `GMX_WINDOW_HEIGHT` | `1080` | Висота вікна |
| `GMX_IMPLICIT_WAIT` | `5` | Неявне очікування для WebDriver (с) |
| `GMX_PAGE_LOAD_TIMEOUT` | `30` | Тайм-аут завантаження сторінки (с) |
| `GMX_DOWNLOAD_DIR` | `<repo>/downloads` | Тека для завантажень |
| `GMX_LOG_LEVEL` | `INFO` | Рівень логування |
| `GMX_PROXY_ENABLED` | `1` | 1 — використовувати проксі, 0 — вимкнути |
| `GMX_PROXY_SCHEME` | `http` | Схема проксі за замовчуванням. Підтримуються `http`, `https`, `socks5`, `socks5h`, `socks4` |
| `GMX_PROXY_URL` | – | Проксі у форматі `host:port` або `host:port:user:pass`. Схема додається автоматично згідно `GMX_PROXY_SCHEME`, але можна вказати повну URL вручну |
| `GMX_SQLITE_PATH` | `<repo>/data/registrations.sqlite3` | Шлях до SQLite-бази, де зберігаються креденшіали успішно створених акаунтів |

## Формат JSON-файлу для ручних даних

```json
{
	"first_name": "Bohdan",
	"last_name": "Petryk",
	"email_local_part": "bohdan.petryk2024",
	"email_domain": "gmx.com",
	"password": "SecurePassw0rd!",
	"recovery_email": "example.backup@mail.com",
	"birthdate": "1995-06-18",
	"security_question": "mother_maiden_name",
	"security_answer": "Ivanyuk"
}
```

## Примітки

### Збереження креденшіалів

- Після успішної реєстрації логін та пароль зберігаються у SQLite-файлі (`GMX_SQLITE_PATH`, за замовчуванням `data/registrations.sqlite3`).
- У БД є таблиця `gmx_accounts`; повторні запуски оновлюють запис за email.
- Переглянути вміст можна напряму через `sqlite3 data/registrations.sqlite3 "SELECT * FROM gmx_accounts;"`.

- На сторінці GMX використовується CAPTCHA, тому фінальний крок може потребувати ручного підтвердження. Скрипт повідомляє про необхідність втручання.
- Локатори елементів можуть змінюватися GMX; за потреби оновіть їх у `app/automation/gmx_registration_page.py`.
- Для CI/CD можна додати мок або емулятор сторінки, щоб тестувати без реальної реєстрації.