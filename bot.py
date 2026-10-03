import asyncio

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes
)

from questions import QUESTIONS


TOKEN = "8915539087:AAH4pDSUkn4JGYMiB58GVmzz3VzUw8LcLxM"

TIME_LIMIT = 60


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton(
                "🇺🇿 O‘zbekiston tarixi",
                callback_data="start_quiz"
            )
        ]
    ]

    await update.message.reply_text(
        "👋 Salom!\n\n"
        "🧠 MIRA Quiz Botga xush kelibsiz!\n\n"
        "📚 Fanni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    old_task = context.user_data.get("timer_task")

    if old_task:
        old_task.cancel()

    context.user_data["question"] = 0
    context.user_data["score"] = 0
    context.user_data["wrong"] = []
    context.user_data["quiz_active"] = True

    await send_question(query, context)


async def send_question(query, context):
    number = context.user_data.get("question")

    if number is None or number >= len(QUESTIONS):
        return

    question = QUESTIONS[number]

    buttons = []

    for i, option in enumerate(question["options"]):
        buttons.append([
            InlineKeyboardButton(
                option,
                callback_data=f"answer_{number}_{i}"
            )
        ])

    text = (
        f"🇺🇿 O‘zbekiston tarixi\n\n"
        f"📝 Savol {number + 1}/{len(QUESTIONS)}\n"
        f"⏱️ Vaqt: {TIME_LIMIT} soniya\n\n"
        f"{question['question']}"
    )

    # Eski savol natijasi o‘chmaydi
    # Yangi savol alohida xabar bo‘ladi
    message = await query.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons)
    )

    old_task = context.user_data.get("timer_task")

    if old_task:
        old_task.cancel()

    context.user_data["timer_task"] = asyncio.create_task(
        question_timer(message, context, number)
    )


async def question_timer(message, context, question_number):

    try:

        for remaining in range(TIME_LIMIT - 1, -1, -1):

            await asyncio.sleep(1)

            # Boshqa savolga o'tilgan bo'lsa timer to'xtaydi
            if context.user_data.get("question") != question_number:
                return

            # Quiz tugagan bo'lsa
            if not context.user_data.get("quiz_active", False):
                return

            # Vaqtni ko'rsatamiz
            if remaining in [50, 40, 30, 20, 10, 5, 4, 3, 2, 1]:

                question = QUESTIONS[question_number]

                buttons = []

                for i, option in enumerate(question["options"]):
                    buttons.append([
                        InlineKeyboardButton(
                            option,
                            callback_data=f"answer_{question_number}_{i}"
                        )
                    ])

                try:
                    await message.edit_text(
                        f"🇺🇿 O‘zbekiston tarixi\n\n"
                        f"📝 Savol {question_number + 1}/{len(QUESTIONS)}\n"
                        f"⏱️ Vaqt: {remaining} soniya\n\n"
                        f"{question['question']}",
                        reply_markup=InlineKeyboardMarkup(buttons)
                    )
                except Exception:
                    pass

        # Vaqt tugadi
        if context.user_data.get("question") == question_number:
            await time_finished(message, context, question_number)

    except asyncio.CancelledError:
        pass


async def time_finished(message, context, question_number):

    if context.user_data.get("question") != question_number:
        return

    question = QUESTIONS[question_number]

    context.user_data["wrong"].append({
        "number": question_number + 1,
        "question": question["question"],
        "your_answer": "⏰ Javob berilmadi",
        "correct_answer": question["options"][question["correct"]]
    })

    context.user_data["question"] += 1

    # Bu xabar o‘chmaydi
    await message.edit_text(
        "⏰ VAQT TUGADI!\n\n"
        "❌ NOTO‘G‘RI\n\n"
        "🟢 To‘g‘ri javob:\n"
        f"{question['options'][question['correct']]}"
    )

    await asyncio.sleep(0.5)

    if context.user_data["question"] < len(QUESTIONS):

        # Yangi savol alohida xabar
        await send_question(message, context)

    else:
        context.user_data["quiz_active"] = False
        await show_result(message, context)


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    # callback_data:
    # answer_savol_raqami_javob_raqami

    try:
        parts = query.data.split("_")

        question_number = int(parts[1])
        selected = int(parts[2])

    except (ValueError, IndexError):
        return

    # Quiz boshlanmagan bo‘lsa
    if not context.user_data.get("quiz_active", False):
        await query.answer(
            "⚠️ Bu quiz tugagan. /start ni bosing.",
            show_alert=True
        )
        return

    # Eski savolning tugmasi bosilgan bo‘lsa
    current_question = context.user_data.get("question")

    if current_question != question_number:

        await query.answer(
            "⚠️ Bu savol allaqachon javoblangan.",
            show_alert=True
        )
        return

    # Timer'ni to‘xtatamiz
    timer_task = context.user_data.get("timer_task")

    if timer_task:
        timer_task.cancel()

    question = QUESTIONS[question_number]

    # To‘g‘ri javob
    if selected == question["correct"]:

        context.user_data["score"] += 1

        result = (
            "✅ TO‘G‘RI!\n\n"
            "🟢 Sizning javobingiz:\n"
            f"{question['options'][selected]}"
        )

    # Noto‘g‘ri javob
    else:

        context.user_data["wrong"].append({
            "number": question_number + 1,
            "question": question["question"],
            "your_answer": question["options"][selected],
            "correct_answer": question["options"][question["correct"]]
        })

        result = (
            "❌ NOTO‘G‘RI!\n\n"
            "🔴 Sizning javobingiz:\n"
            f"{question['options'][selected]}\n\n"
            "🟢 TO‘G‘RI JAVOB:\n"
            f"{question['options'][question['correct']]}"
        )

    # Natija o‘chmaydi
    await query.message.edit_text(result)

    context.user_data["question"] += 1

    await asyncio.sleep(0.5)

    if context.user_data["question"] < len(QUESTIONS):

        # Keyingi savol yangi xabar
        await send_question(query, context)

    else:

        context.user_data["quiz_active"] = False

        await show_result(query, context)


async def show_result(query, context):

    score = context.user_data["score"]
    wrong = context.user_data["wrong"]

    wrong_count = len(wrong)

    text = (
        "🎉 TEST YAKUNLANDI!\n\n"
        f"📊 Natijangiz: {score}/{len(QUESTIONS)}\n\n"
        f"✅ To‘g‘ri: {score} ta\n"
        f"❌ Xato: {wrong_count} ta\n"
    )

    keyboard = [
        [
            InlineKeyboardButton(
                "🔄 Qayta ishlash",
                callback_data="start_quiz"
            )
        ],
        [
            InlineKeyboardButton(
                "🏠 Bosh sahifa",
                callback_data="home"
            )
        ]
    ]

    # Natija alohida xabar bo‘ladi
    await query.message.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    # Xato savollarni alohida xabarlarda chiqaramiz
    if wrong_count > 0:

        await query.message.reply_text(
            "📕 XATO QILGAN SAVOLLARINGIZ:"
        )

        chunk = ""

        for item in wrong:

            item_text = (
                f"❌ {item['number']}. {item['question']}\n\n"
                f"🔴 Sizning javobingiz:\n"
                f"{item['your_answer']}\n\n"
                f"🟢 To‘g‘ri javob:\n"
                f"{item['correct_answer']}\n\n"
                "━━━━━━━━━━━━━━\n\n"
            )

            if len(chunk) + len(item_text) > 3800:

                await query.message.reply_text(chunk)

                chunk = ""

            chunk += item_text

        if chunk:
            await query.message.reply_text(chunk)


async def home(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    timer_task = context.user_data.get("timer_task")

    if timer_task:
        timer_task.cancel()

    context.user_data["quiz_active"] = False

    keyboard = [
        [
            InlineKeyboardButton(
                "🇺🇿 O‘zbekiston tarixi",
                callback_data="start_quiz"
            )
        ]
    ]

    await query.message.reply_text(
        "🏠 Bosh sahifa\n\n"
        "📚 Fanni tanlang:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


app = Application.builder().token(TOKEN).build()


app.add_handler(
    CommandHandler("start", start)
)


app.add_handler(
    CallbackQueryHandler(
        start_quiz,
        pattern="^start_quiz$"
    )
)


app.add_handler(
    CallbackQueryHandler(
        answer,
        pattern=r"^answer_\d+_[0-3]$"
    )
)


app.add_handler(
    CallbackQueryHandler(
        home,
        pattern="^home$"
    )
)


print("🧠 MIRA Quiz Bot ishga tushdi...")


app.run_polling()