

""" 
class GameState(StatesGroup):
    playing = State()
    creators_editing = State()
    creating_content = State()


def generate_keyboard(question: Question) -> ReplyKeyboardMarkup:

    buttons_count = question.answers_count + 1
    numbers = random.sample(range(1, 101), buttons_count)
    buttons = [[KeyboardButton(text=str(num))] for num in numbers]

    return ReplyKeyboardMarkup(
        keyboard=buttons,
        resize_keyboard=True,
        one_time_keyboard=True
    )


async def next_round(message: Message):
    number = random.randint(1, 10)
    keyboard = generate_keyboard()
    await message.answer(
        f"🎲 Случайное число: <b>{number}</b>\nВыберите одно из чисел ниже:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
    )


@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer("Привет! Напиши /start_game чтобы начать игру.")


@dp.message(Command("start_game"))
async def cmd_start_game(message: Message, state: FSMContext):
    await state.set_state(GameState.playing)
    await next_round(message)


@dp.message(GameState.playing, F.text)
async def handle_game_message(message: Message, state: FSMContext):
    await message.answer(f"Вы нажали на кнопку с числом {message.text}")
    await next_round(message)


@dp.message(Command("end_game"))
async def cmd_end_game(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Игра завершена!", reply_markup=ReplyKeyboardRemove()) """

""" @inject
async def send_question(
    message: types.Message,
    state: FSMContext,
    session: AsyncSession = Provide[C.db_session],
    minio_client: Minio = Provide[C.minio_client]
):

    Функция для отправки одного вопроса с четырьмя вариантами ответа.
    qr = QuestionRepository(session)

    # Получаем новый вопрос, исключая уже заданные
    questions = await qr.get_random_questions(5)
    question = questions[0]

    # Берем 4 неверных варианта
    wrong_opts = questions[1:]

    # Собираем и перемешиваем варианты (1 правильный + 4 неверных)
    random.shuffle(questions)

    # Формируем Inline-клавиатуру
    keyboard = InlineKeyboardMarkup(row_width=2)
    for opt in questions:
        btn = InlineKeyboardButton(
            text=opt.file.answer,
            callback_data=f"answer:{opt.id}"
        )
        keyboard.insert(btn)

    # Генерируем presigned URL для медиа-вопроса
    media_url = minio_client.presigned_get_object(
        bucket_name=settings.minio_bucket,
        object_name=str(question.file.id),
        expires=timedelta(minutes=5)  # ссылка валидна 5 минут
    )

    # Отправляем картинку и клавиатуру
    await message.answer_photo(
        photo=media_url,
        caption="ABOBA?",
        reply_markup=keyboard
    )

    # Сохраняем в состоянии текущий вопрос и обновляем список заданных
    await state.update_data(question_id=question.id)


    Обработчик ответа пользователя: проверяет правильность и отправляет следующий вопрос.

    # Подтверждаем обработку callback, чтобы убрать «часики» у пользователя
    await callback.answer()

    data = await state.get_data()
    current_qid: int = data.get("question_id")
    selected_id = int(callback.data.split("\":\", 1)[1])

    qr = QuestionRepository(session)
    question = await qr.get_by_id(current_qid)

    # Проверяем правильность
    if selected_id == question.id:
        result_text = "✅ Правильно!"
    else:
        result_text = f"❌ Неверно! Правильный ответ: {question.answer_text}"

    # Отправляем результат и следующий вопрос
    await callback.message.answer(result_text)
    await send_question(callback.message, state) """


