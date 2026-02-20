from aiogram.fsm.state import State, StatesGroup


class ScheduleStates(StatesGroup):
    choosing_day = State()
    entering_time = State()


class MeetStates(StatesGroup):
    entering_title = State()
    entering_datetime = State()
    entering_location = State()
    entering_deadline = State()
    entering_reminder = State()
    entering_recurrence = State()
    confirm = State()


class ExpenseStates(StatesGroup):
    entering_title = State()
    entering_amount = State()
    choosing_participants = State()
