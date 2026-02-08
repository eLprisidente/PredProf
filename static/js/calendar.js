class SimpleCalendar {
    constructor(inputElement, options = {}) {
        this.input = inputElement;
        this.options = {
            minDate: options.minDate || null,
            maxDate: options.maxDate || null,
            defaultDate: options.defaultDate || null,
            hiddenFieldId: options.hiddenFieldId || null,
            onSelect: options.onSelect || null,
            ...options
        };

        console.log('Calendar initialized for:', inputElement.id);

        this.today = new Date();
        this.currentMonth = this.today.getMonth();
        this.currentYear = this.today.getFullYear();
        this.selectedDate = null;

        this.calendar = null;
        this.isVisible = false;

        this.handleOutsideClick = this.handleOutsideClick.bind(this);

        this.init();
    }

    init() {
        this.createCalendarElement();
        this.bindEvents();
        this.setInitialDate();
    }

    createCalendarElement() {
        this.calendar = document.createElement('div');
        this.calendar.className = 'simple-calendar';
        this.calendar.style.cssText = `
            display: none;
            position: absolute;
            z-index: 10000;
            background: white;
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 15px;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.2);
            width: 300px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        `;

        this.calendar.innerHTML = `
            <div class="calendar-header" style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px solid #eee;">
                <button type="button" class="calendar-prev" style="background: #f8f9fa; border: none; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #2c3e50; transition: all 0.2s;">
                    <i class="bi bi-chevron-left"></i>
                </button>
                <div class="calendar-title" style="font-weight: 600; color: #2c3e50; font-size: 1rem; text-align: center; flex: 1;"></div>
                <button type="button" class="calendar-next" style="background: #f8f9fa; border: none; width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #2c3e50; transition: all 0.2s;">
                    <i class="bi bi-chevron-right"></i>
                </button>
            </div>
            <div class="calendar-weekdays" style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; margin-bottom: 8px; text-align: center;">
                <div style="font-weight: 600; color: #7f8c8d; font-size: 0.85rem; padding: 5px 0;">Пн</div>
                <div style="font-weight: 600; color: #7f8c8d; font-size: 0.85rem; padding: 5px 0;">Вт</div>
                <div style="font-weight: 600; color: #7f8c8d; font-size: 0.85rem; padding: 5px 0;">Ср</div>
                <div style="font-weight: 600; color: #7f8c8d; font-size: 0.85rem; padding: 5px 0;">Чт</div>
                <div style="font-weight: 600; color: #7f8c8d; font-size: 0.85rem; padding: 5px 0;">Пт</div>
                <div style="font-weight: 600; color: #7f8c8d; font-size: 0.85rem; padding: 5px 0;">Сб</div>
                <div style="font-weight: 600; color: #7f8c8d; font-size: 0.85rem; padding: 5px 0;">Вс</div>
            </div>
            <div class="calendar-days" style="display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px; text-align: center;"></div>
        `;

        document.body.appendChild(this.calendar);
    }

    bindEvents() {
        this.input.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            this.toggle();
        });

        const icon = this.input.parentElement.querySelector('.datepicker-icon');
        if (icon) {
            icon.style.pointerEvents = 'auto';
            icon.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.toggle();
            });
        }

        this.calendar.addEventListener('click', (e) => {
            e.stopPropagation();

            if (e.target.closest('.calendar-prev')) {
                this.prevMonth();
            } else if (e.target.closest('.calendar-next')) {
                this.nextMonth();
            }
        });
    }

    handleOutsideClick(e) {
        if (this.isVisible &&
            !this.calendar.contains(e.target) &&
            e.target !== this.input) {
            this.hide();
        }
    }

    parseDate(dateStr) {
        if (!dateStr) return null;

        if (dateStr.includes('-')) {
            const parts = dateStr.split('-');
            if (parts.length === 3) {
                const year = parseInt(parts[0], 10);
                const month = parseInt(parts[1], 10) - 1;
                const day = parseInt(parts[2], 10);

                return new Date(year, month, day);
            }
        }
        return null;
    }

    setInitialDate() {
        if (this.options.defaultDate) {
            const date = this.parseDate(this.options.defaultDate);
            if (date) {
                this.selectedDate = date;
                this.currentMonth = date.getMonth();
                this.currentYear = date.getFullYear();
                this.updateInput();
            }
        }

        this.render();
    }

    updateInput() {
        if (this.selectedDate) {
            const day = String(this.selectedDate.getDate()).padStart(2, '0');
            const month = String(this.selectedDate.getMonth() + 1).padStart(2, '0');
            const year = this.selectedDate.getFullYear();

            this.input.value = `${day}.${month}.${year}`;
            console.log('Input updated:', this.input.value);

            if (this.options.hiddenFieldId) {
                const hiddenField = document.getElementById(this.options.hiddenFieldId);
                if (hiddenField) {
                    hiddenField.value = `${year}-${month}-${day}`;
                    console.log('Hidden field updated:', hiddenField.value);
                }
            }
        }
    }

    toggle() {
        if (this.isVisible) {
            this.hide();
        } else {
            this.show();
        }
    }

    show() {
        if (this.isVisible) return;

        console.log('Showing calendar');

        const rect = this.input.getBoundingClientRect();
        const scrollTop = window.pageYOffset || document.documentElement.scrollTop;
        const scrollLeft = window.pageXOffset || document.documentElement.scrollLeft;

        const spaceBelow = window.innerHeight - rect.bottom;
        const spaceAbove = rect.top;

        if (spaceBelow < 300 && spaceAbove > 300) {
            this.calendar.style.top = (rect.top + scrollTop - 320) + 'px';
        } else {
            this.calendar.style.top = (rect.bottom + scrollTop + 5) + 'px';
        }

        this.calendar.style.left = (rect.left + scrollLeft) + 'px';
        this.calendar.style.display = 'block';
        this.isVisible = true;

        document.addEventListener('click', this.handleOutsideClick);

        this.render();
    }

    hide() {
        if (!this.isVisible) return;

        console.log('Hiding calendar');
        this.calendar.style.display = 'none';
        this.isVisible = false;

        document.removeEventListener('click', this.handleOutsideClick);
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

        const monthNames = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ];
        title.textContent = `${monthNames[this.currentMonth]} ${this.currentYear}`;

        daysContainer.innerHTML = '';

        const firstDay = new Date(this.currentYear, this.currentMonth, 1);
        const lastDay = new Date(this.currentYear, this.currentMonth + 1, 0);
        const daysInMonth = lastDay.getDate();

        let startingDay = firstDay.getDay();
        if (startingDay === 0) startingDay = 6; // Воскресенье -> 6
        else startingDay--; // Понедельник -> 0

        for (let i = 0; i < startingDay; i++) {
            const emptyDay = document.createElement('div');
            emptyDay.style.height = '34px';
            daysContainer.appendChild(emptyDay);
        }

        const today = new Date();
        today.setHours(0, 0, 0, 0);

        const minDate = this.options.minDate ? this.parseDate(this.options.minDate) : today;
        const maxDate = this.options.maxDate ? this.parseDate(this.options.maxDate) : null;

        for (let day = 1; day <= daysInMonth; day++) {
            const date = new Date(this.currentYear, this.currentMonth, day);
            const dayElement = document.createElement('div');

            dayElement.style.cssText = `
                height: 34px;
                display: flex;
                align-items: center;
                justify-content: center;
                border-radius: 6px;
                cursor: pointer;
                font-size: 0.9rem;
                transition: all 0.2s;
                color: #2c3e50;
                user-select: none;
            `;

            dayElement.textContent = day;

            const isSelectable = this.isDateSelectable(date, minDate, maxDate);

            if (isSelectable) {
                if (date.getFullYear() === today.getFullYear() &&
                    date.getMonth() === today.getMonth() &&
                    date.getDate() === today.getDate()) {
                    dayElement.style.border = '2px solid #3498db';
                    dayElement.style.color = '#3498db';
                    dayElement.style.fontWeight = '600';
                }

                if (this.selectedDate &&
                    this.selectedDate.getFullYear() === date.getFullYear() &&
                    this.selectedDate.getMonth() === date.getMonth() &&
                    this.selectedDate.getDate() === date.getDate()) {
                    dayElement.style.background = '#27ae60';
                    dayElement.style.color = 'white';
                    dayElement.style.fontWeight = '600';
                }

                dayElement.addEventListener('click', (e) => {
                    e.stopPropagation();
                    console.log('Day selected:', day);
                    this.selectDate(date);
                });

                dayElement.addEventListener('mouseenter', () => {
                    if (dayElement.style.background !== 'rgb(39, 174, 96)') {
                        dayElement.style.background = '#3498db';
                        dayElement.style.color = 'white';
                    }
                });

                dayElement.addEventListener('mouseleave', () => {
                    if (dayElement.style.background === 'rgb(52, 152, 219)') {
                        dayElement.style.background = '';

                        if (date.getFullYear() === today.getFullYear() &&
                            date.getMonth() === today.getMonth() &&
                            date.getDate() === today.getDate()) {
                            dayElement.style.color = '#3498db';
                        } else if (this.selectedDate &&
                            this.selectedDate.getFullYear() === date.getFullYear() &&
                            this.selectedDate.getMonth() === date.getMonth() &&
                            this.selectedDate.getDate() === date.getDate()) {
                            dayElement.style.color = 'white';
                        } else {
                            dayElement.style.color = '#2c3e50';
                        }
                    }
                });
            } else {
                dayElement.style.color = '#bdc3c7';
                dayElement.style.cursor = 'not-allowed';
                dayElement.style.textDecoration = 'line-through';
            }

            daysContainer.appendChild(dayElement);
        }
    }

    isDateSelectable(date, minDate, maxDate) {
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        if (date < today) return false;

        if (minDate && date < minDate) return false;

        if (maxDate && date > maxDate) return false;

        return true;
    }

    selectDate(date) {
        console.log('Date selected:', date);

        this.selectedDate = date;
        this.updateInput();

        if (this.options.onSelect) {
            const day = String(date.getDate()).padStart(2, '0');
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const year = date.getFullYear();
            const formattedDate = `${day}.${month}.${year}`;
            this.options.onSelect(date, formattedDate);
        }

        this.hide();
    }
}

document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing calendars...');

    document.querySelectorAll('.datepicker-input').forEach(input => {
        const dateData = document.getElementById('date-data');

        if (dateData) {
            const calendar = new SimpleCalendar(input, {
                minDate: dateData.dataset.minDate,
                maxDate: dateData.dataset.maxDate,
                defaultDate: dateData.dataset.defaultDate,
                hiddenFieldId: 'order_date',
                onSelect: function(date, formattedDate) {
                    console.log('Date selected callback:', formattedDate);
                }
            });

            input.calendar = calendar;
        }
    });
});

window.SimpleCalendar = SimpleCalendar;
