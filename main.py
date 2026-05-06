# main.py
import kivy
kivy.require('2.2.0')

import os
import json
import datetime
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.clock import Clock
from kivy.properties import StringProperty, ListProperty, BooleanProperty
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from plyer import notification

Window.clearcolor = (0.94, 0.95, 0.97, 1)
CONFIG_FILE = 'med_reminder_config.json'

KV = '''
<RootLayout>:
    orientation: 'vertical'
    padding: 12
    spacing: 10
    canvas.before:
        Color:
            rgba: 0.94, 0.95, 0.97, 1
        Rectangle:
            pos: self.pos
            size: self.size

    Label:
        text: 'MedReminder'
        font_size: 24
        bold: True
        color: 0.15, 0.55, 0.95, 1
        size_hint_y: None
        height: 35

    BoxLayout:
        orientation: 'horizontal'
        size_hint_y: None
        height: 40
        spacing: 8
        Label:
            text: 'Окно уведомлений:'
            size_hint_x: 0.35
            color: 0.25, 0.25, 0.25, 1
            font_size: 14
            halign: 'left'
            valign: 'middle'
        TextInput:
            id: start_input
            text: root.notif_start
            hint_text: 'Начало'
            size_hint_x: 0.325
            multiline: False
            font_size: 14
            background_color: 1, 1, 1, 1
            padding: [8, 4]
            on_text: root.notif_start = self.text
        TextInput:
            id: end_input
            text: root.notif_end
            hint_text: 'Конец'
            size_hint_x: 0.325
            multiline: False
            font_size: 14
            background_color: 1, 1, 1, 1
            padding: [8, 4]
            on_text: root.notif_end = self.text

    BoxLayout:
        orientation: 'horizontal'
        size_hint_y: None
        height: 40
        spacing: 10
        Button:
            text: 'Выключить' if root.is_active else 'Включить'
            background_color: (0.15, 0.55, 0.95, 1) if root.is_active else (0.85, 0.85, 0.85, 1)
            color: (1, 1, 1, 1) if root.is_active else (0.4, 0.4, 0.4, 1)
            font_size: 15
            on_release: root.toggle_active()
        Label:
            text: root.status
            color: 0.2, 0.2, 0.2, 1
            font_size: 14
            size_hint_x: 0.6
            halign: 'left'
            valign: 'middle'

    Label:
        text: 'Препараты и расписание:'
        size_hint_y: None
        height: 25
        color: 0.25, 0.25, 0.25, 1
        font_size: 14
        halign: 'left'
        valign: 'middle'

    ScrollView:
        BoxLayout:
            id: meds_container
            orientation: 'vertical'
            size_hint_y: None
            height: self.minimum_height
            spacing: 8
            padding: 0

    BoxLayout:
        orientation: 'horizontal'
        size_hint_y: None
        height: 40
        spacing: 8
        TextInput:
            id: new_med_input
            hint_text: 'Название препарата'
            size_hint_x: 0.75
            font_size: 14
            multiline: False
            background_color: 1, 1, 1, 1
            padding: [8, 4]
        Button:
            text: 'Добавить'
            size_hint_x: 0.25
            background_color: 0.15, 0.55, 0.95, 1
            font_size: 14
            on_release: root.add_medication()
'''

Builder.load_string(KV)

class RootLayout(BoxLayout):
    notif_start = StringProperty('08:00')
    notif_end = StringProperty('22:00')
    is_active = BooleanProperty(False)
    status = StringProperty('Не активно')
    medications = ListProperty([])
    notified_today = ListProperty([])
    last_date = StringProperty('')

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.load_config()
        self.rebuild_meds_ui()
        Clock.schedule_interval(self.check_reminders, 15)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                self.notif_start = cfg.get('notif_start', '08:00')
                self.notif_end = cfg.get('notif_end', '22:00')
                self.medications = cfg.get('medications', [])
                self.is_active = cfg.get('is_active', False)
                self.update_status()
            except Exception as e:
                print(f"Ошибка загрузки: {e}")

    def save_config(self):
        cfg = {
            'notif_start': self.notif_start,
            'notif_end': self.notif_end,
            'medications': self.medications,
            'is_active': self.is_active
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(cfg, f)

    def rebuild_meds_ui(self):
        container = self.ids.meds_container
        container.clear_widgets()
        if not self.medications:
            container.add_widget(Label(text='Нет добавленных препаратов',
                                     color=(0.5, 0.5, 0.5, 1), size_hint_y=None, height=40))
            return

        for i, med in enumerate(self.medications):
            # Карточка препарата
            card = BoxLayout(orientation='vertical', size_hint_y=None, height=0, spacing=4, padding=10)
            
            # Фон карточки
            with card.canvas.before:
                Color(1, 1, 1, 1)
                card_bg = RoundedRectangle(pos=card.pos, size=card.size, radius=[10])

            def sync_bg(bg_rect, layout):
                bg_rect.pos = layout.pos
                bg_rect.size = layout.size

            card.bind(pos=lambda inst, val: sync_bg(card_bg, card),
                      size=lambda inst, val: sync_bg(card_bg, card))
            card.bind(minimum_height=card.setter('height'))

            # Заголовок карточки
            header = BoxLayout(orientation='horizontal', size_hint_y=None, height=38, spacing=8)
            name_lbl = Label(text=med['name'], bold=True, color=(0.15, 0.5, 0.9, 1),
                            font_size=15, halign='left', valign='middle')
            name_lbl.bind(size=name_lbl.setter('text_size'))
            header.add_widget(name_lbl)

            del_btn = Button(text='Удалить', size_hint_x=None, width=80,
                            background_color=(0.85, 0.25, 0.25, 1), font_size=13)
            del_btn.bind(on_release=lambda *args, idx=i: self.remove_medication(idx))
            header.add_widget(del_btn)
            card.add_widget(header)

            # Список времён
            for t in sorted(med['times']):
                row = BoxLayout(orientation='horizontal', size_hint_y=None, height=36, spacing=8)
                time_lbl = Label(text=f"{t}  |  {med['name']}", color=(0.25, 0.25, 0.25, 1),
                               font_size=14, halign='left', valign='middle')
                time_lbl.bind(size=time_lbl.setter('text_size'))
                row.add_widget(time_lbl)

                rm_btn = Button(text='Убрать', size_hint_x=None, width=65,
                               background_color=(0.92, 0.92, 0.92, 1), color=(0.4, 0.4, 0.4, 1), font_size=13)
                rm_btn.bind(on_release=lambda *args, med_idx=i, time=t: self.remove_time(med_idx, time))
                row.add_widget(rm_btn)
                card.add_widget(row)

            # Строка добавления времени
            add_row = BoxLayout(orientation='horizontal', size_hint_y=None, height=38, spacing=6)
            time_inp = TextInput(hint_text='ЧЧ:ММ', multiline=False, font_size=14,
                                background_color=(0.96, 0.96, 0.96, 1), foreground_color=(0.2, 0.2, 0.2, 1),
                                padding=[8, 4])
            add_btn = Button(text='+', size_hint_x=None, width=50, background_color=(0.2, 0.65, 0.3, 1))
            add_btn.bind(on_release=lambda *args, inp=time_inp, med_idx=i: self.add_time(med_idx, inp))
            add_row.add_widget(time_inp)
            add_row.add_widget(add_btn)
            card.add_widget(add_row)

            container.add_widget(card)

    def add_medication(self):
        inp = self.ids.new_med_input
        name = inp.text.strip()
        if not name:
            inp.hint_text = 'Введите название'
            Clock.schedule_once(lambda dt: setattr(inp, 'hint_text', 'Название препарата'), 1.5)
            return
        if any(m['name'].lower() == name.lower() for m in self.medications):
            inp.hint_text = 'Уже существует'
            Clock.schedule_once(lambda dt: setattr(inp, 'hint_text', 'Название препарата'), 1.5)
            return

        self.medications.append({'name': name, 'times': []})
        inp.text = ''
        self.save_config()
        self.rebuild_meds_ui()
        self.update_status()

    def remove_medication(self, idx):
        self.medications.pop(idx)
        self.save_config()
        self.rebuild_meds_ui()
        self.update_status()

    def add_time(self, med_idx, inp):
        raw = inp.text.strip()
        if not self._validate_time(raw):
            inp.foreground_color = (0.8, 0, 0, 1)
            Clock.schedule_once(lambda dt: setattr(inp, 'foreground_color', (0.2, 0.2, 0.2, 1)), 1.5)
            return
        if raw in self.medications[med_idx]['times']:
            inp.hint_text = 'Уже добавлено'
            Clock.schedule_once(lambda dt: setattr(inp, 'hint_text', 'ЧЧ:ММ'), 1.5)
            return
        
        self.medications[med_idx]['times'].append(raw)
        self.medications[med_idx]['times'].sort()
        inp.text = ''
        self.save_config()
        self.rebuild_meds_ui()
        self.update_status()

    def remove_time(self, med_idx, time_str):
        if time_str in self.medications[med_idx]['times']:
            self.medications[med_idx]['times'].remove(time_str)
            self.save_config()
            self.rebuild_meds_ui()
            self.update_status()

    def _validate_time(self, t):
        try:
            datetime.datetime.strptime(t, '%H:%M')
            return True
        except ValueError:
            return False

    def update_status(self):
        total = sum(len(m['times']) for m in self.medications)
        if self.is_active and total > 0:
            self.status = f"Активно | {total} напоминаний"
        else:
            self.status = "Не активно"

    def toggle_active(self):
        self.is_active = not self.is_active
        if self.is_active:
            self.notified_today = []
            self.last_date = ''
        self.save_config()
        self.update_status()

    def check_reminders(self, dt):
        if not self.is_active or not self.medications:
            return

        now = datetime.datetime.now()
        curr_time = now.time()
        curr_date = now.date().isoformat()

        start_t = self.parse_time(self.notif_start)
        end_t = self.parse_time(self.notif_end)
        if not (start_t and end_t):
            return

        in_window = False
        if start_t <= end_t:
            in_window = start_t <= curr_time <= end_t
        else:
            in_window = curr_time >= start_t or curr_time <= end_t

        if not in_window:
            return

        if self.last_date != curr_date:
            self.notified_today = []
            self.last_date = curr_date

        for med in self.medications:
            for t_str in med['times']:
                key = f"{med['name']}_{t_str}"
                if key in self.notified_today:
                    continue
                
                t = self.parse_time(t_str)
                if not t:
                    continue

                diff = abs((curr_time.hour * 60 + curr_time.minute) - (t.hour * 60 + t.minute))
                if diff <= 1:
                    self.send_notification(med['name'], t_str)
                    self.notified_today.append(key)

    def parse_time(self, t_str):
        try:
            return datetime.datetime.strptime(t_str.strip(), '%H:%M').time()
        except ValueError:
            return None

    def send_notification(self, med_name, time_str):
        try:
            notification.notify(
                title='Напоминание о приёме',
                message=f'Время: {time_str} | Препарат: {med_name}',
                app_name='MedReminder',
                timeout=12
            )
        except Exception as e:
            print(f"Ошибка уведомления: {e}")


class MedReminderApp(App):
    def build(self):
        return RootLayout()


if __name__ == '__main__':
    MedReminderApp().run()