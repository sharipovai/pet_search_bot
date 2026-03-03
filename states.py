from telebot.asyncio_handler_backends import State, StatesGroup


class BotStates(StatesGroup):
    add_pet = State()
    wait_user_menu =  State()
    main_menu = State()
    add_new_pet = State()
    waiting_for_photo = State()