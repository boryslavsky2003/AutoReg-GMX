# 📊 Data Pool System - 100k+ Realistic Records

Система для генерації великих обсягів реалістичних даних для GMX реєстрації.

## 🚀 Quick Start

### 1. Ініціалізація пулу даних (100к+ записів)
```bash
# Стандартна ініціалізація (100k імен, 50k міст, 10k відповідей)
python init_data_pool.py

# Кастомні розміри
python init_data_pool.py --names 100000 --cities 50000 --security 10000

# Менші пули для тестування
python init_data_pool.py --names 10000 --cities 5000 --security 1000
```

### 2. Перевірка статистик
```bash
python init_data_pool.py --stats
```

### 3. Тестування генерації
```bash
python test_data_pool.py
```

## 📈 Переваги системи

### ✅ **Величезна різноманітність**
- **Імена**: 100,000+ комбінацій з 14 локалей (українська, німецька, французька, англійська і т.д.)
- **Міста**: 50,000+ реальних міст з різних країн
- **Безпечні відповіді**: 10,000+ реалістичних відповідей для кожного типу питань

### ✅ **Реалістичні дані замість рандомних символів**
```
❌ Старий підхід: "asdkfj_123", "qwerty789"  
✅ Новий підхід: "Олександр.Петренко2024", "Emma.Johnson47"
```

### ✅ **Максимальна продуктивність**
- SQLite індекси для швидкого пошуку
- Пакетна генерація (1000 записів за раз)  
- Мінімальне споживання пам'яті
- Уникнення дублікатів

### ✅ **Інтелектуальні відповіді на безпечні питання**
- **Дівоче прізвище матері**: справжні прізвища (Коваленко, Smith, Müller)
- **Ім'я першого домашнього улюбленця**: популярні клички (Buddy, Max, Luna)  
- **Місто народження**: реальні міста (Київ, London, Berlin)

## 🎯 Використання в коді

```python
from app.data_models import generate_registration_data

# Використання пулу даних (рекомендовано)
data = generate_registration_data(use_data_pool=True)

# Fallback на Faker (якщо пул порожній)  
data = generate_registration_data(use_data_pool=False)
```

## 📊 Структура бази даних

```
app/storage/data_pool.db
├── names_pool        (100k+ імен)
├── cities_pool       (50k+ міст)  
├── security_answers_pool (30k+ відповідей)
└── used_combinations (трекінг використання)
```

## 🛠 CLI Опції

### init_data_pool.py
```bash
python init_data_pool.py [options]

Options:
  --names N       Кількість імен (default: 100000)
  --cities N      Кількість міст (default: 50000)  
  --security N    Відповідей на питання (default: 10000)
  --stats         Показати статистики та вийти
  --db-path PATH  Кастомний шлях до бази
```

### Приклади використання
```bash
# Повна ініціалізація 100k+ записів
python init_data_pool.py --names 100000

# Швидке тестування  
python init_data_pool.py --names 5000 --cities 2000 --security 500

# Перевірка поточного стану
python init_data_pool.py --stats
```

## 🎲 Sample Output

```
Sample 1:
  Name: Владислав Мельник  
  Email: vladyslav.melnyk2024@gmx.com
  Recovery: smith.john@gmail.com
  Birth: 1995-03-15
  Security Q: birth_city  
  Security A: Львів

Sample 2:
  Name: Emma Thompson
  Email: emma_thompson47x@gmx.net
  Recovery: mueller.hans@yahoo.com  
  Birth: 1988-07-22
  Security Q: first_pet
  Security A: Buddy
```

## ⚡ Performance Tips

1. **Створюйте великі пули одразу** - SQLite оптимізований для пакетних операцій
2. **Використовуйте --stats** для моніторингу прогресу
3. **Почніть з малих пулів** для тестування, потім масштабуйте
4. **База даних займає ~50MB** для 100k записів

## 🔧 Troubleshooting

### База даних порожня?
```bash
python init_data_pool.py --stats
# Якщо 0 записів - запустіть ініціалізацію
```

### Повільна генерація?  
```bash
# Збільште batch_size в data_pool.py (default: 1000)
# Або створюйте менші пули: --names 50000
```

### Хочете ще більше різноманітності?
```bash
# Збільште цільові числа
python init_data_pool.py --names 500000 --cities 100000
```

---
**🚀 Готово! Тепер у вас є база з 100k+ реалістичних записів замість рандомних символів!**