// static/js/calendar.js - Простой и надежный календарь

class SimpleCalendar {
    constructor(element, options = {}) {
        this.element = element;
        this.options = {
            minDate: options.minDate || null,
            maxDate: options.maxDate || null,
            defaultDate: options.defaultDate || new Date(),
            dateFormat: options.dateFormat || 'dd.mm.yyyy',
            onSelect: options.onSelect || null,
            ...options
        };

        this.selectedDate = null;
        this.currentMonth = new Date().getMonth();
        this.currentYear = new Date().getFullYear();

        this.init();
    }

    init() {
        this.createCalendarHTML();
        this.bindEvents();
        this.render();
    }

    createCalendarHTML() {
        this.calendar = document.createElement('div');
        this.calendar.className = 'simple-calendar';

        // Создаем структуру календаря
        this.calendar.innerHTML = `
            <div class="calendar-header">
                <button type="button" class="calendar-prev">
                    <i class="bi bi-chevron-left"></i>
                </button>
                <div class="calendar-title"></div>
                <button type="button" class="calendar-next">
                    <i class="bi bi-chevron-right"></i>
                </button>
            </div>
            <div class="calendar-weekdays">
                <div>Пн</div>
                <div>Вт</div>
                <div>Ср</div>
                <div>Чт</div>
                <div>Пт</div>
                <div>Сб</div>
                <div>Вс</div>
            </div>
            <div class="calendar-days"></div>
        `;

        // Скрываем календарь изначально
        this.calendar.style.display = 'none';
        this.calendar.style.position = 'absolute';
        this.calendar.style.zIndex = '1000';
        this.calendar.style.background = 'white';
        this.calendar.style.border = '1px solid #ddd';
        this.calendar.style.borderRadius = '8px';
        this.calendar.style.padding = '10px';
        this.calendar.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)';

        document.body.appendChild(this.calendar);
    }

    bindEvents() {
        // Открытие/закрытие календаря
        this.element.addEventListener('click', (e) => {
            e.preventDefault();
            this.toggle();
        });

        // Навигация
        this.calendar.querySelector('.calendar-prev').addEventListener('click', () => {
            this.prevMonth();
        });

        this.calendar.querySelector('.calendar-next').addEventListener('click', () => {
            this.nextMonth();
        });

        // Закрытие при клике вне календаря
        document.addEventListener('click', (e) => {
            if (!this.calendar.contains(e.target) && e.target !== this.element) {
                this.hide();
            }
        });
    }

    toggle() {
        if (this.calendar.style.display === 'none') {
            this.show();
        } else {
            this.hide();
        }
    }

    show() {
        const rect = this.element.getBoundingClientRect();
        this.calendar.style.top = (rect.bottom + window.scrollY + 5) + 'px';
        this.calendar.style.left = (rect.left + window.scrollX) + 'px';
        this.calendar.style.display = 'block';
    }

    hide() {
        this.calendar.style.display = 'none';
    }

    prevMonth() {
        this.currentMonth--;
        if (this.currentMonth < 0) {
            this.currentMonth = 11;
            this.currentYear--;
        }
        this.render();
    }

    nextMonth() {
        this.currentMonth++;
        if (this.currentMonth > 11) {
            this.currentMonth = 0;
            this.currentYear++;
        }
        this.render();
    }

    render() {
        const title = this.calendar.querySelector('.calendar-title');
        const daysContainer = this.calendar.querySelector('.calendar-days');

        // Название месяца и года
        const monthNames = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ];
        title.textContent = `${monthNames[this.currentMonth]} ${this.currentYear}`;

        // Очищаем дни
        daysContainer.innerHTML = '';

        // Получаем первый день месяца и сколько дней в месяце
        const firstDay = new Date(this.currentYear, this.currentMonth, 1);
        const lastDay = new Date(this.currentYear, this.currentMonth + 1, 0);
        const daysInMonth = lastDay.getDate();
        const startingDay = firstDay.getDay() === 0 ? 6 : firstDay.getDay() - 1; // Начинаем с понедельника

        // Добавляем пустые ячейки для дней предыдущего месяца
        for (let i = 0; i < startingDay; i++) {
            const emptyDay = document.createElement('div');
            emptyDay.className = 'calendar-day empty';
            daysContainer.appendChild(emptyDay);
        }

        // Добавляем дни текущего месяца
        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(this.currentYear, this.currentMonth, day);
            const dayElement = document.createElement('div');
            dayElement.className = 'calendar-day';
            dayElement.textContent = day;
            dayElement.dataset.date = this.formatDate(date);

            // Проверяем, можно ли выбрать эту дату
            if (this.isDateSelectable(date)) {
                dayElement.classList.add('selectable');

                // Отмечаем сегодняшний день
                const today = new Date();
                if (date.getDate() === today.getDate() &&
                    date.getMonth() === today.getMonth() &&
                    date.getFullYear() === today.getFullYear()) {
                    dayElement.classList.add('today');
                }

                // Отмечаем выбранный день
                if (this.selectedDate && this.formatDate(this.selectedDate) === this.formatDate(date)) {
                    dayElement.classList.add('selected');
                }

                dayElement.addEventListener('click', () => {
                    this.selectDate(date);
                });
            } else {
                dayElement.classList.add('disabled');
            }

            daysContainer.appendChild(dayElement);
        }
    }

    isDateSelectable(date) {
        // Проверяем минимальную дату
        if (this.options.minDate) {
            const minDate = new Date(this.options.minDate);
            minDate.setHours(0, 0, 0, 0);
            if (date < minDate) return false;
        }

        // Проверяем максимальную дату
        if (this.options.maxDate) {
            const maxDate = new Date(this.options.maxDate);
            maxDate.setHours(23, 59, 59, 999);
            if (date > maxDate) return false;
        }

        // Нельзя выбирать даты из прошлого
        const today = new Date();
        today.setHours(0, 0, 0, 0);
        if (date < today) return false;

        return true;
    }

    selectDate(date) {
        this.selectedDate = date;

        // Форматируем дату для отображения
        const formattedDate = this.formatForDisplay(date);
        this.element.value = formattedDate;

        // Вызываем callback
        if (this.options.onSelect) {
            this.options.onSelect(date, formattedDate);
        }

        this.hide();
        this.render();
    }

    formatDate(date) {
        // Формат YYYY-MM-DD
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        return `${year}-${month}-${day}`;
    }

    formatForDisplay(date) {
        // Формат DD.MM.YYYY
        const day = String(date.getDate()).padStart(2, '0');
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const year = date.getFullYear();
        return `${day}.${month}.${year}`;
    }

    setDate(dateString) {
        if (!dateString) return;

        const parts = dateString.split('.');
        if (parts.length === 3) {
            const day = parseInt(parts[0]);
            const month = parseInt(parts[1]) - 1;
            const year = parseInt(parts[2]);
            const date = new Date(year, month, day);

            if (!isNaN(date.getTime())) {
                this.selectDate(date);
                this.currentMonth = month;
                this.currentYear = year;
                this.render();
            }
        }
    }
}

// Инициализация календаря на странице
document.addEventListener('DOMContentLoaded', function() {
    // Находим все поля с классом .simple-datepicker
    document.querySelectorAll('.simple-datepicker').forEach(input => {
        const minDate = input.dataset.minDate;
        const maxDate = input.dataset.maxDate;
        const defaultDate = input.dataset.defaultDate;

        const calendar = new SimpleCalendar(input, {
            minDate: minDate,
            maxDate: maxDate,
            defaultDate: defaultDate,
            onSelect: function(date, formattedDate) {
                // Обновляем связанное скрытое поле, если оно есть
                const hiddenField = document.getElementById(input.dataset.hiddenField);
                if (hiddenField) {
                    const year = date.getFullYear();
                    const month = String(date.getMonth() + 1).padStart(2, '0');
                    const day = String(date.getDate()).padStart(2, '0');
                    hiddenField.value = `${year}-${month}-${day}`;
                }

                console.log('Дата выбрана:', formattedDate);
            }
        });

        // Устанавливаем начальную дату
        if (defaultDate) {
            calendar.setDate(defaultDate);
        }
    });
});