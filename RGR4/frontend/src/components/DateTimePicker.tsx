import { useEffect, useRef } from 'react'
import AirDatepicker from 'air-datepicker'
import 'air-datepicker/air-datepicker.css'

const locale = {
  days: ['Воскресенье', 'Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота'],
  daysShort: ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'],
  daysMin: ['Вс', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб'],
  months: ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'],
  monthsShort: ['Янв', 'Фев', 'Мар', 'Апр', 'Май', 'Июн', 'Июл', 'Авг', 'Сен', 'Окт', 'Ноя', 'Дек'],
  today: 'Сегодня',
  clear: 'Очистить',
  dateFormat: 'dd.MM.yyyy',
  timeFormat: 'HH:mm',
  firstDay: 1 as const,
}

export default function DateTimePicker({ value, onChange, required = false }: { value: string; onChange: (value: string) => void; required?: boolean }) {
  const inputRef = useRef<HTMLInputElement>(null)
  const pickerRef = useRef<AirDatepicker<HTMLInputElement> | null>(null)

  useEffect(() => {
    if (!inputRef.current) return
    pickerRef.current = new AirDatepicker(inputRef.current, {
      locale,
      timepicker: true,
      minutesStep: 5,
      autoClose: true,
      selectedDates: value ? [new Date(value)] : [],
      onSelect: ({ date }) => onChange(date instanceof Date ? date.toISOString() : ''),
    })
    return () => pickerRef.current?.destroy()
  }, [])

  return <input ref={inputRef} className="date-picker-input" type="text" placeholder="ДД.ММ.ГГГГ, чч:мм" required={required} />
}
